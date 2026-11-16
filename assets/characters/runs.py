"""Run cycles for the hero, made by script (Blender): in place, on the Tripo 20k model's skeleton (Unreal-style names:
pelvis, spine_01-03, neck_01, head, clavicle, upperarm, lowerarm, hand and fingers, thigh, calf, foot, ball), for the
game to carry the hero along at its speed (the user asked for running animations to choose from, 2 November).

A run is a handful of numbers, a style (STYLES): how many frames a cycle takes, how long a foot stays on the ground,
where it lands, how high the heels kick and the knees drive, how far the trunk leans and twists, how the arms swing
and the elbows bend, how tight the fists are. From them each frame is posed:

- the hips rise and fall as a runner's do, sinking into each landing and flying as gravity has them between steps;
- each foot on the ground stays put on it, moving back under the hero at its speed (SPEED), rolling from heel or
  forefoot to the ball, the heel rising as it pushes off, the toes bending on the ground; the legs reach it by IK;
- in the air the ankle follows a path through a few points (kicking back, passing under the hips, reaching out);
- the pelvis turns, tilts and sways with the legs, the shoulders turn against it and roll toward the foot on the
  ground, the head holds still;
- the arms swing against the legs, the elbows bent, the hands loosely closed, the thumb across the fingers.

Each bone's whole turn from its rest pose is worked out in the armature's space, where "forward" and "up" mean the
same for every bone, and only then put into each bone's own axes, so the Tripo rig's bone rolls don't matter.
"""
import json
import math
import os

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "run_settings.json")  # the user's tuning (the run editor's "Save settings"), over STYLES
FPS = 60  # keys a second
SPEED = 5.5  # m/s, the hero's speed in the demo (game/scripts/hero.gd): the feet on the ground move back at it
G = 9.81
UP = Vector((0.0, 0.0, 1.0))
FWD = Vector((0.0, -1.0, 0.0))  # the figures face -Y; their left is +X
FINGERS = ("index", "middle", "ring", "pinky")
THUMB = (0.6, 0.9, 0.9)  # the thumb's joints bend this much of the fingers' (it closes over them)
THUMB_ACROSS = 1.5  # the thumb bends toward the little finger this much for each part toward the palm
LANDING_PITCH = 0.75  # share of the swing by which the foot has the pitch it lands with (toes up, the heel leading)
# how much of the chest's turn from the pelvis each spine bone has, from the bottom up: the lower back takes much of
# the lean, so the whole trunk leans from the hips as a runner's does, rather than only the chest curling forward
SPINE = (0.55, 0.8, 1.0)
# helper bones some rigs have (rigs.py): each turns half as far as its joint, the child turning from the parent
HELPER_JOINTS = {"knee": ("thigh", "calf"), "elbow": ("upperarm", "lowerarm"), "hip": ("pelvis", "thigh"),
                 "shoulder": ("clavicle", "upperarm")}

# The athletic run; every style changes some of these.
DEFAULTS = dict(
    frames=40,          # keys in a cycle (two steps) at 60 a second: 40 is 180 steps a minute
    stance=0.20,        # share of the cycle each foot is on the ground
    land=0.27,          # m ahead of the hip the ankle lands
    track=0.17,         # m between the lines the two feet land on
    toe_out=6.0,        # degrees the feet turn out
    knee_out=4.0,       # degrees the knees point out
    strike=-16.0,       # foot pitch at landing, degrees: below 0 toes up (heel first), above 0 toes down (forefoot)
    flat_at=0.22,       # share of the stance by which the foot is flat: the forefoot comes down a beat after the heel
    heel_at=0.6,        # share of the stance at which the heel starts to rise: the foot planted flat till then
    dorsi=12.0,         # degrees the foot comes up (the toes toward the shin) late in the swing, so the heel leads
    push=38.0,          # foot pitch at toe-off, heel up
    hip=0.865,          # m, the hip joints' height at landing (standing, 0.918)
    sink=0.0,           # m the hips sink in the stance on top of what landing gives
    float=0.85,         # the flight's rise between steps, times what gravity gives
    back1=0.36, z1=0.36,   # the ankle a fifth into the swing: m behind the hip, m high
    back2=0.14, z2=0.46,   # half way, passing under the hips: the heel kick
    fwd3=0.12, z3=0.34,    # three quarters: the shank swinging forward under the driving knee
    reach=0.0, z4=0.17,    # just before landing: m out past the landing spot, m high
    bow=0.04,           # m the swinging foot bows out, round the other leg
    catch=0.75,         # share of the ground's speed the foot is already going back at as it lands
    land_drop=0.7,      # m/s the foot is coming down at as it lands
    lean=13.0,          # degrees forward, the trunk
    hunch=0.0,          # degrees more the upper back rounds forward, the head pushed out ahead (below 0, chest out)
    pelvis_tilt=4.0,    # degrees forward, the pelvis
    tilt_swing=2.0,     # degrees more as each foot pushes off, less as it lands
    pelvis_yaw=7.0,     # degrees each way, the pelvis turning with the legs
    pelvis_drop=4.0,    # degrees, the swinging leg's side dropping in stance
    sway=0.012,         # m the hips move toward the foot on the ground
    twist=9.0,          # degrees each way, the shoulders against the hips
    bounce_lean=1.5,    # degrees the trunk dips forward after each landing
    rock=1.2,           # degrees the shoulders roll toward the foot on the ground
    arm_swing=34.0,     # degrees each way at the shoulder
    arm_mean=-6.0,      # degrees, the middle of the swing (below 0, behind)
    arm_out=12.0,       # degrees out from the side
    back_out=9.0,       # degrees more as the arm swings back
    arm_loop=0.08,      # share of a cycle the arm's in and out lead its swing
    arm_across=7.0,     # degrees the forearms turn in across the body
    elbow=88.0,         # degrees the elbows bend, on average
    elbow_swing=14.0,   # more bent forward, less behind, by this each way
    arm_lag=0.03,       # share of a cycle the arms lag the legs
    shrug=3.0,          # degrees the shoulders rise as the arm swings forward
    protract=6.0,       # degrees the shoulders go forward with the arm
    shoulders=0.0,      # degrees the shoulders are held up all along (tense; below 0 dropped, loose)
    wrist=8.0,          # degrees the wrists bend in
    wrist_swing=6.0,    # degrees the hands flop after the forearms, each way
    head_pitch=6.0,     # degrees chin down, looking ahead
    head_steady=0.85,   # how much the head holds still against the trunk's turning
    head_nod=2.0,       # degrees the head dips after each landing, a beat after the trunk
    skirt_push=0.75,    # how far the thighs push the tunic's skirt (cloth bones), of how far they swing
    skirt_flutter=4.0,  # degrees the hem swings on after each landing
    fist=0.7,           # 0 an open hand, 1 a tight fist
    snap=0.0,           # 0 smooth swings; above 0 sharper, held longer at the ends
)

# The fifty runs of round 1, all at the hero's speed, landing heel first. label: a name; text: what it's like, for the
# portfolio.
STYLES = {
    "athletic": dict(
        label="Athletic", text="A strong, even run: a firm lean, the knees driving, the arms pumping at the elbow.",
        stance=0.22, land=0.3, lean=14.0, back2=0.12, z2=0.5, fwd3=0.16, z3=0.42, arm_swing=42.0, elbow=90.0,
        elbow_swing=18.0, twist=11.0, arm_out=16.0, arm_across=3.0, back_out=15.0),
    # as sprinters run: tall, landing under the hips and driving off a nearly straight leg (the knee some 20 degrees
    # bent as the foot leaves the ground), the knees no higher than the hips, the hands up beside the chin and not
    # across the body
    "sprint": dict(
        label="Sprinter", text="Quick and all-out: high knees, heels kicked up, quick light heel-to-toe steps, the "
        "body level, the arms pumping hard with open hands.",
        frames=32, stance=0.245, land=0.235, strike=-10.0, flat_at=0.2, heel_at=0.52, push=44.0, hip=0.89, float=0.6,
        lean=17.0, back1=0.3, z1=0.46, back2=0.06, z2=0.6, fwd3=0.2, z3=0.46, reach=0.0, z4=0.22, arm_swing=52.0,
        arm_mean=-6.0, elbow=86.0, elbow_swing=24.0, arm_out=14.0, back_out=15.0, arm_across=0.0, fist=0.1, snap=0.2,
        twist=8.0, head_pitch=8.0, head_steady=0.92),
    "easy": dict(
        label="Easy stride", text="Relaxed and upright: low knees, a low heel kick, the arms hanging loose and low, "
        "the head riding along.",
        frames=46, stance=0.22, land=0.335, hip=0.85, float=0.6, strike=-14.0, push=55.0, lean=4.0, pelvis_tilt=2.0,
        back1=0.34, z1=0.28, back2=0.24, z2=0.3, fwd3=0.04, z3=0.26, reach=0.02, z4=0.15, arm_swing=22.0,
        arm_mean=-12.0, elbow=62.0, elbow_swing=8.0, arm_out=14.0, arm_across=5.0, fist=0.35, wrist_swing=10.0,
        twist=6.0, pelvis_yaw=8.0, shrug=1.0, head_steady=0.6, head_pitch=2.0, bounce_lean=0.8, back_out=15.0),
    "heroic": dict(
        label="Heroic", text="Chest up and chin high, long floating strides, the arms long and swinging high, fists "
        "closed.",
        frames=44, stance=0.195, land=0.3, hip=0.865, float=0.9, lean=3.0, pelvis_tilt=1.0, head_pitch=-3.0, back2=0.12,
        z2=0.5, fwd3=0.18, z3=0.44, arm_swing=48.0, arm_mean=-6.0, elbow=46.0, elbow_swing=14.0, arm_out=14.0,
        back_out=6.0, arm_across=2.0, wrist=4.0, fist=0.8, twist=13.0, pelvis_yaw=9.0, shrug=4.0, protract=10.0,
        snap=0.1),
    "heavy": dict(
        label="Heavy", text="A big man in armour: wide feet, low heavy landings heel first, long on the ground, "
        "rocking side to side, the arms held out and swinging little.",
        frames=48, stance=0.24, land=0.395, track=0.28, toe_out=12.0, knee_out=10.0, strike=-12.0, flat_at=0.18,
        push=60.0, hip=0.8, sink=0.04, float=0.45, lean=10.0, pelvis_drop=7.0, sway=0.04, rock=5.0, back1=0.32, z1=0.26,
        back2=0.22, z2=0.32, fwd3=0.08, z3=0.3, z4=0.15, arm_swing=18.0, arm_mean=-2.0, elbow=72.0, elbow_swing=8.0,
        arm_out=26.0, back_out=8.0, arm_across=0.0, fist=0.8, twist=4.0, pelvis_yaw=4.0, head_pitch=12.0,
        head_steady=0.6, shrug=1.0, bounce_lean=3.0),
    "nimble": dict(
        label="Nimble", text="Low, quick and light: short fast steps rolling heel to toe, the body level, the arms "
        "tucked in tight, the head still.",
        frames=30, stance=0.31, land=0.36, strike=-10.0, flat_at=0.2, heel_at=0.52, push=34.0, hip=0.82, float=0.5,
        lean=18.0, back1=0.32, z1=0.34, back2=0.14, z2=0.42, fwd3=0.1, z3=0.32, z4=0.16, arm_swing=20.0, arm_mean=0.0,
        elbow=108.0, elbow_swing=8.0, arm_out=10.0, back_out=6.0, arm_across=10.0, fist=0.65, twist=6.0, pelvis_yaw=6.0,
        head_pitch=8.0, head_steady=0.97, bounce_lean=1.0),
    "guarded": dict(
        label="Guarded", text="Ready to fight: crouched, fists up by the chin, the elbows in, short steps, chin down.",
        frames=36, stance=0.285, land=0.35, track=0.22, toe_out=10.0, hip=0.825, float=0.5, lean=15.0, strike=-10.0,
        push=50.0, back2=0.18, z2=0.38, fwd3=0.08, z3=0.3, arm_swing=10.0, arm_mean=22.0, elbow=116.0, elbow_swing=5.0,
        arm_out=16.0, back_out=4.0, arm_across=18.0, fist=0.9, wrist=14.0, shrug=6.0, protract=6.0, twist=4.0,
        pelvis_yaw=5.0, head_pitch=14.0, head_steady=0.95),
    "bounding": dict(
        label="Bounding", text="Long, floating leaps: fewer steps, the legs spread wide in the air, the arms swinging "
        "long.",
        frames=52, stance=0.165, land=0.3, hip=0.87, float=1.15, lean=9.0, bounce_lean=2.5, back1=0.44, z1=0.3,
        back2=0.22, z2=0.44, fwd3=0.24, z3=0.46, reach=0.04, z4=0.22, arm_swing=46.0, elbow=66.0, elbow_swing=16.0,
        arm_out=16.0, fist=0.5, twist=12.0, pelvis_yaw=10.0, arm_across=3.0),
    "snappy": dict(
        label="Snappy", text="Cartoon energy: a big bounce, heels to the seat, knees high, arms flung wide, the poses "
        "held and snapped between, readable from far away.",
        frames=34, stance=0.235, land=0.29, float=1.35, sink=0.04, lean=18.0, bounce_lean=5.0, snap=0.65, back1=0.3,
        z1=0.46, back2=0.04, z2=0.62, fwd3=0.24, z3=0.5, reach=0.08, z4=0.26, arm_swing=50.0, arm_mean=0.0, elbow=86.0,
        elbow_swing=14.0, arm_out=22.0, back_out=18.0, arm_across=0.0, fist=0.8, twist=15.0, pelvis_yaw=11.0,
        pelvis_drop=6.0, head_steady=0.4, head_nod=5.0, shrug=7.0, protract=12.0),
    # its rhythm as measured in runners at 20 km/h (Hanley et al. 2022): 3.2 steps a second of 1.74 m, a foot on the
    # ground 166-178 ms and in the air 133-150, the hips 7-8 cm up and down. The hero's legs are shorter than theirs,
    # so a foot stays down only as long as it's in the air, pushing off high on the toes to reach that far.
    "natural": dict(
        label="Natural", text="As a real runner moves at this speed: a slight lean, quick light steps landing nearly "
        "in line, heel first, each foot on the ground about as long as it's in the air, relaxed hands crossing a "
        "little in front, the head still.",
        frames=38, stance=0.255, land=0.28, track=0.1, hip=0.87, float=0.9, lean=6.0, strike=-12.0, flat_at=0.22,
        push=65.0, back1=0.36, z1=0.32, back2=0.18, z2=0.4, fwd3=0.08, z3=0.3, z4=0.16, arm_swing=26.0, arm_mean=-10.0,
        elbow=80.0, elbow_swing=12.0, arm_out=14.0, arm_across=8.0, fist=0.45, twist=8.0, pelvis_drop=5.0, sway=0.015,
        head_steady=0.92, head_pitch=5.0, arm_lag=0.04, bounce_lean=1.0, back_out=24.0),

    # runners
    "marathon": dict(
        label="Marathoner", text="Economical over long miles: a slight lean, quick short steps with little bounce, low "
        "knees and a low heel kick, the hands low and loose, swinging close by the waist.",
        frames=36, stance=0.265, land=0.31, float=0.55, lean=7.0, back2=0.24, z2=0.32, fwd3=0.06, z3=0.28, z4=0.15,
        strike=-12.0, push=50.0, arm_swing=22.0, arm_mean=-8.0, elbow=82.0, elbow_swing=8.0, arm_out=12.0,
        back_out=20.0, arm_across=4.0, fist=0.35, wrist=4.0, wrist_swing=8.0, twist=6.0, pelvis_yaw=6.0, shrug=1.0,
        protract=3.0, shoulders=-2.0, head_steady=0.95, head_pitch=4.0, bounce_lean=0.6),
    "miler": dict(
        label="Miler", text="A middle-distance racer: tall and quick, the knees coming well up, the arms swinging "
        "fully at a right angle, loose shoulders and relaxed hands.",
        frames=34, stance=0.26, land=0.275, hip=0.875, float=0.8, lean=9.0, back2=0.12, z2=0.48, fwd3=0.16, z3=0.4,
        strike=-14.0, push=45.0, arm_swing=40.0, arm_mean=-4.0, elbow=90.0, elbow_swing=12.0, arm_out=13.0,
        arm_across=2.0, fist=0.4, twist=9.0, shoulders=-1.0, head_steady=0.93, back_out=24.0),
    "trail": dict(
        label="Trail runner", text="Sure-footed over roots and stones: a little crouched, the feet a touch apart, "
        "short quick steps, the arms held out a little for balance, the eyes on the ground ahead.",
        frames=34, stance=0.28, land=0.34, hip=0.845, float=0.6, track=0.22, toe_out=8.0, lean=12.0, back2=0.18, z2=0.4,
        fwd3=0.12, z3=0.36, strike=-12.0, arm_swing=26.0, arm_mean=-2.0, arm_out=20.0, back_out=12.0, elbow=78.0,
        elbow_swing=10.0, fist=0.3, wrist_swing=9.0, twist=7.0, sway=0.02, rock=2.5, head_pitch=14.0, head_steady=0.9),
    "strider": dict(
        label="Long strider", text="Long, reaching strides at an unhurried rhythm: each foot reaching far out and "
        "planting, the body passing smoothly over it, the arms swinging long and low.",
        frames=50, stance=0.17, land=0.29, hip=0.875, float=0.5, lean=4.0, reach=0.06, back1=0.42, z1=0.3, back2=0.22,
        z2=0.34, fwd3=0.24, z3=0.38, z4=0.18, strike=-18.0, arm_swing=36.0, arm_mean=-10.0, elbow=50.0,
        elbow_swing=14.0, arm_out=14.0, fist=0.4, twist=12.0, pelvis_yaw=11.0, head_steady=0.85, back_out=12.0),
    "quickstep": dict(
        label="Quick feet", text="Short, quick, light steps, the feet barely leaving the ground, little bounce, the "
        "arms making small quick swings, the body level and calm above them.",
        frames=31, stance=0.27, land=0.29, hip=0.87, float=0.4, lean=5.0, back1=0.3, z1=0.24, back2=0.2, z2=0.28,
        fwd3=0.06, z3=0.24, z4=0.13, strike=-10.0, arm_swing=18.0, arm_mean=-6.0, elbow=100.0, elbow_swing=6.0,
        arm_out=10.0, fist=0.5, twist=5.0, head_steady=0.95),
    "glide": dict(
        label="Glide", text="Smooth as if on rails: the head and hips hardly rising or falling, long flowing steps on "
        "soft knees, the arms swinging long and easy, the head quite still.",
        frames=44, stance=0.21, land=0.33, hip=0.85, float=0.3, lean=7.0, back1=0.36, z1=0.28, back2=0.2, z2=0.34,
        fwd3=0.14, z3=0.32, z4=0.15, catch=0.9, land_drop=0.4, strike=-12.0, bounce_lean=0.3, head_nod=0.5,
        head_steady=1.0, arm_swing=34.0, arm_mean=-8.0, elbow=70.0, elbow_swing=10.0, arm_lag=0.06, fist=0.3,
        wrist_swing=9.0, twist=8.0, back_out=18.0, arm_across=3.0),
    "springy": dict(
        label="Springy", text="Every step a spring: the hips sinking into each landing and bouncing high off it, the "
        "heels kicking up, the arms lifting with the bounce.",
        frames=44, stance=0.195, land=0.3, hip=0.86, float=1.4, sink=0.035, lean=5.0, bounce_lean=3.0, back2=0.1,
        z2=0.58, fwd3=0.16, z3=0.42, strike=-14.0, arm_swing=36.0, elbow=70.0, shrug=6.0, fist=0.5, head_nod=4.0,
        head_steady=0.8, arm_mean=-8.0, arm_out=14.0, back_out=15.0, arm_across=3.0),
    "courier": dict(
        label="Courier", text="A messenger with news to carry: quick and set on getting there, a steady forward lean, "
        "the arms swinging briskly but low, the head up.",
        frames=34, stance=0.26, land=0.3, lean=17.0, hip=0.865, float=0.75, back2=0.14, z2=0.44, fwd3=0.14, z3=0.38,
        strike=-14.0, arm_swing=32.0, arm_mean=-12.0, elbow=70.0, elbow_swing=12.0, arm_out=16.0, arm_across=2.0,
        fist=0.5, twist=8.0, head_pitch=-2.0, head_steady=0.9, back_out=15.0),

    # fighters
    "charge": dict(
        label="Charge", text="Head down and driving forward: a deep lean from the hips, the fists pumping hard, the "
        "knees punching forward, each foot dug in.",
        frames=38, stance=0.265, land=0.33, lean=30.0, hunch=6.0, pelvis_tilt=8.0, hip=0.85, float=0.75, back2=0.1,
        z2=0.5, fwd3=0.2, z3=0.44, strike=-14.0, push=50.0, arm_swing=48.0, arm_mean=0.0, elbow=92.0, elbow_swing=20.0,
        fist=0.95, twist=12.0, shoulders=4.0, protract=10.0, head_pitch=18.0, back_out=21.0),
    "barbarian": dict(
        label="Barbarian", text="A big, wild-strong man: chest out, the arms swinging wide and high with the fists "
        "closed, heavy driving steps, the shoulders rolling.",
        frames=44, stance=0.21, land=0.33, hip=0.85, sink=0.025, float=0.75, track=0.24, toe_out=10.0, lean=8.0,
        hunch=-6.0, back2=0.14, z2=0.44, fwd3=0.18, z3=0.42, strike=-16.0, bounce_lean=2.5, arm_swing=44.0,
        arm_mean=-2.0, arm_out=26.0, back_out=14.0, elbow=70.0, elbow_swing=16.0, fist=0.9, twist=15.0, pelvis_yaw=9.0,
        rock=4.0, shrug=6.0, protract=12.0, head_pitch=2.0),
    "brawler": dict(
        label="Brawler", text="A street fighter on the move: fists loose in front of the chest, the shoulders rolling "
        "side to side, a bouncing, swaggering step, the chin tucked.",
        frames=40, stance=0.23, land=0.33, hip=0.85, float=0.8, lean=11.0, strike=-14.0, sway=0.03, pelvis_drop=6.0,
        rock=6.0, arm_swing=18.0, arm_mean=18.0, elbow=112.0, elbow_swing=8.0, arm_out=22.0, arm_across=6.0, fist=0.85,
        twist=10.0, shrug=4.0, shoulders=5.0, protract=8.0, head_pitch=10.0),
    "berserker": dict(
        label="Berserker", text="Wild fury: a deep lean, the arms flung out and round with the fists clenched, the "
        "head down, the knees and heels high, every step a lunge.",
        frames=36, stance=0.265, land=0.35, lean=26.0, hip=0.85, float=1.0, back1=0.3, z1=0.46, back2=0.06, z2=0.58,
        fwd3=0.22, z3=0.48, reach=0.04, strike=-16.0, arm_swing=56.0, arm_mean=4.0, arm_out=24.0, back_out=18.0,
        arm_across=0.0, elbow=70.0, elbow_swing=22.0, fist=1.0, snap=0.35, twist=18.0, pelvis_yaw=12.0, shrug=8.0,
        protract=14.0, shoulders=6.0, head_pitch=14.0, head_steady=0.5),
    "soldier": dict(
        label="Double time", text="A soldier's double time: upright and square, a strict rhythm, the fists swinging "
        "straight forward and back on nearly straight arms, the eyes front.",
        frames=42, stance=0.205, land=0.29, lean=4.0, pelvis_tilt=2.0, hip=0.87, float=0.65, back2=0.18, z2=0.4,
        fwd3=0.1, z3=0.36, strike=-16.0, arm_swing=38.0, arm_mean=-4.0, elbow=40.0, elbow_swing=8.0, arm_out=8.0,
        back_out=10.0, arm_across=0.0, arm_loop=0.0, fist=0.9, snap=0.4, twist=4.0, pelvis_yaw=5.0, shoulders=-1.0,
        head_pitch=0.0, head_steady=1.0),
    "knight": dict(
        label="Knight", text="As if in mail: the trunk held stiff and upright and hardly turning, the arms a little "
        "out from the body and swinging short, heavy, deliberate steps.",
        frames=46, stance=0.19, land=0.29, hip=0.86, sink=0.02, float=0.55, track=0.22, toe_out=9.0, lean=6.0,
        back2=0.22, z2=0.34, fwd3=0.08, z3=0.32, strike=-16.0, twist=3.0, pelvis_yaw=4.0, rock=2.5, sway=0.025,
        arm_swing=20.0, arm_mean=-4.0, arm_out=22.0, back_out=6.0, elbow=60.0, elbow_swing=8.0, fist=0.85, shrug=1.0,
        protract=3.0, shoulders=3.0, head_pitch=4.0, head_steady=0.95),
    "bull": dict(
        label="Bull", text="Massive and unstoppable: the head and shoulders down and forward, the shoulders hunched "
        "up, wide heavy steps, the arms swinging low and wide.",
        frames=46, stance=0.21, land=0.355, lean=24.0, hunch=10.0, hip=0.83, sink=0.03, float=0.6, track=0.26,
        toe_out=10.0, knee_out=8.0, strike=-14.0, pelvis_drop=6.0, sway=0.03, rock=5.0, arm_swing=28.0, arm_mean=-4.0,
        arm_out=24.0, back_out=10.0, elbow=58.0, elbow_swing=10.0, fist=0.9, twist=7.0, shoulders=10.0, head_pitch=9.0),
    "stomper": dict(
        label="Stomper", text="Pounding the ground: each heel planted hard and far out in front, the body jolting down "
        "onto it, upright, the arms swinging stiffly.",
        frames=46, stance=0.195, land=0.32, strike=-20.0, dorsi=18.0, flat_at=0.16, catch=0.45, land_drop=1.6,
        sink=0.045, float=0.7, reach=0.04, z4=0.2, back2=0.22, z2=0.36, fwd3=0.12, z3=0.34, lean=4.0, bounce_lean=3.5,
        arm_swing=30.0, arm_mean=-6.0, elbow=64.0, elbow_swing=6.0, fist=0.75, twist=6.0, head_nod=5.0, head_steady=0.7,
        arm_out=14.0, back_out=12.0),
    "boxer": dict(
        label="Roadwork", text="A boxer out on a morning run: light and springy, the fists up near the chest swinging "
        "short, the shoulders loose, the chin tucked in.",
        frames=36, stance=0.235, land=0.28, hip=0.87, float=0.95, lean=7.0, back2=0.14, z2=0.46, fwd3=0.12, z3=0.36,
        strike=-12.0, arm_swing=14.0, arm_mean=16.0, elbow=114.0, elbow_swing=6.0, arm_out=10.0, arm_across=14.0,
        fist=0.8, twist=6.0, shrug=2.0, shoulders=3.0, head_pitch=12.0),
    "veteran": dict(
        label="Veteran", text="An old campaigner saving his strength: upright and stiff, short low strides, hardly "
        "turning, the arms bent and swinging only a little.",
        frames=40, stance=0.215, land=0.3, hip=0.86, float=0.5, lean=6.0, back1=0.3, z1=0.26, back2=0.24, z2=0.28,
        fwd3=0.04, z3=0.26, z4=0.14, strike=-16.0, bounce_lean=0.8, twist=3.0, pelvis_yaw=4.0, arm_swing=16.0,
        arm_mean=-4.0, elbow=84.0, elbow_swing=6.0, arm_out=10.0, fist=0.6, shrug=1.0, protract=2.0, shoulders=2.0,
        head_steady=0.9),
    "ducking": dict(
        label="Ducking", text="Running low under flying arrows: the knees deeply bent and the hips low but the back "
        "kept upright, the head drawn down between raised shoulders, the arms tight.",
        frames=38, stance=0.28, land=0.405, hip=0.8, float=0.45, lean=8.0, hunch=4.0, back2=0.18, z2=0.4, fwd3=0.12,
        z3=0.32, z4=0.14, strike=-12.0, arm_swing=22.0, arm_mean=4.0, elbow=104.0, elbow_swing=8.0, arm_out=12.0,
        arm_across=8.0, fist=0.7, twist=5.0, shoulders=9.0, head_pitch=6.0, head_steady=0.95),

    # the wilds
    "prowler": dict(
        label="Prowler", text="Stalking at speed: low and hunched, the head pushed forward but the eyes level, the "
        "arms low and a little out, soft, quiet landings.",
        frames=38, stance=0.26, land=0.365, hip=0.81, float=0.45, lean=32.0, hunch=10.0, back2=0.2, z2=0.36, fwd3=0.12,
        z3=0.3, z4=0.13, catch=0.9, land_drop=0.4, strike=-10.0, arm_swing=24.0, arm_mean=-14.0, arm_out=18.0,
        back_out=10.0, elbow=50.0, elbow_swing=10.0, fist=0.3, wrist=12.0, twist=6.0, head_pitch=8.0, head_steady=0.97,
        arm_across=3.0),
    "rogue": dict(
        label="Rogue", text="Quick and sly: bent forward, short fast steps, the arms swept low and back with the hands "
        "open, the head up and alert.",
        frames=32, stance=0.3, land=0.35, hip=0.83, float=0.55, lean=27.0, hunch=4.0, back2=0.16, z2=0.42, fwd3=0.1,
        z3=0.32, strike=-10.0, arm_swing=26.0, arm_mean=-22.0, arm_out=14.0, back_out=12.0, elbow=40.0,
        elbow_swing=12.0, fist=0.15, wrist=16.0, wrist_swing=10.0, twist=7.0, head_pitch=3.0, arm_across=3.0),
    "scout": dict(
        label="Scout", text="Light and watchful: short quick steps a little crouched, the arms close and swinging "
        "small, the head up and steady, looking far ahead.",
        frames=34, stance=0.28, land=0.35, hip=0.845, float=0.6, lean=9.0, back2=0.18, z2=0.4, fwd3=0.1, z3=0.32,
        strike=-12.0, arm_swing=20.0, arm_mean=-4.0, elbow=104.0, elbow_swing=8.0, arm_out=10.0, arm_across=8.0,
        fist=0.5, twist=5.0, head_pitch=-2.0, head_steady=0.98, back_out=12.0),
    "ranger": dict(
        label="Ranger", text="A woodsman covering ground: long easy strides with the knees coming forward, a forward "
        "lean, the arms low and loose with the hands half open, steady and tireless.",
        frames=46, stance=0.205, land=0.34, hip=0.85, float=0.65, lean=16.0, back2=0.18, z2=0.4, fwd3=0.16, z3=0.38,
        strike=-14.0, arm_swing=32.0, arm_mean=-12.0, elbow=80.0, elbow_swing=12.0, arm_out=18.0, arm_across=4.0,
        fist=0.4, wrist_swing=8.0, twist=9.0, pelvis_yaw=9.0, head_pitch=6.0, head_steady=0.9, back_out=15.0),
    "hunter": dict(
        label="Hunter", text="Closing on quarry: leaning in, the head dead still and level, compact arms pumping short "
        "and quick, long low strides.",
        frames=40, stance=0.23, land=0.33, hip=0.85, float=0.5, lean=20.0, back2=0.18, z2=0.4, fwd3=0.14, z3=0.36,
        strike=-14.0, bounce_lean=0.8, arm_swing=26.0, arm_mean=2.0, elbow=108.0, elbow_swing=10.0, arm_out=8.0,
        arm_across=10.0, fist=0.6, twist=6.0, head_pitch=2.0, head_steady=1.0, head_nod=0.5, back_out=24.0),
    "lope": dict(
        label="Lope", text="A long, easy lope that could go on all day: unhurried, little bounce, long strides on soft "
        "knees, the arms hanging loose and swinging low.",
        frames=52, stance=0.175, land=0.33, hip=0.85, float=0.45, lean=6.0, back1=0.4, z1=0.26, back2=0.26, z2=0.3,
        fwd3=0.14, z3=0.3, z4=0.15, strike=-14.0, arm_swing=26.0, arm_mean=-14.0, elbow=40.0, elbow_swing=12.0,
        arm_out=14.0, fist=0.25, wrist_swing=12.0, twist=9.0, pelvis_yaw=10.0, head_steady=0.8),

    # moods and people
    "swagger": dict(
        label="Swagger", text="Cocky and loose: chest out and chin up, the hips rolling, the open hands swinging "
        "across the body, taking his time about it.",
        frames=44, stance=0.195, land=0.3, hip=0.865, float=0.75, toe_out=10.0, lean=2.0, hunch=-8.0, strike=-16.0,
        pelvis_yaw=12.0, pelvis_drop=7.0, sway=0.03, twist=12.0, arm_swing=30.0, arm_mean=-6.0, arm_across=15.0,
        elbow=50.0, elbow_swing=14.0, arm_out=12.0, fist=0.15, wrist_swing=12.0, shoulders=-3.0, head_pitch=-6.0,
        back_out=15.0),
    "weary": dict(
        label="Weary", text="Running on his last legs: the head hanging forward, the shoulders slumped, the arms "
        "swinging low and heavy, the feet kept low and landing heavily.",
        frames=42, stance=0.215, land=0.32, hip=0.845, float=0.45, sink=0.03, lean=12.0, hunch=12.0, back1=0.3, z1=0.27,
        back2=0.26, z2=0.26, fwd3=0.04, z3=0.24, z4=0.15, catch=0.6, land_drop=1.0, strike=-10.0, arm_swing=18.0,
        arm_mean=-10.0, elbow=48.0, elbow_swing=6.0, arm_out=14.0, fist=0.3, wrist_swing=10.0, twist=6.0,
        shoulders=-4.0, head_pitch=10.0, head_steady=0.6, head_nod=4.0, arm_across=3.0, back_out=15.0),
    "fleeing": dict(
        label="Fleeing", text="Running for his life: upright, leaning back a little with the head up, the arms "
        "flailing wide with open hands, long panicked strides.",
        frames=38, stance=0.225, land=0.29, lean=-2.0, hunch=-4.0, hip=0.875, float=0.95, back2=0.1, z2=0.52, fwd3=0.18,
        z3=0.44, reach=0.06, strike=-18.0, arm_swing=48.0, arm_mean=-6.0, arm_out=22.0, back_out=16.0, elbow=48.0,
        elbow_swing=22.0, fist=0.05, wrist_swing=14.0, twist=14.0, pelvis_yaw=10.0, shrug=6.0, head_pitch=-8.0,
        head_steady=0.4),
    "eager": dict(
        label="Eager squire", text="Young and keen: bouncing along on quick steps, the arms pumping a little too high "
        "with open hands, the head bobbing.",
        frames=32, stance=0.28, land=0.31, float=1.35, sink=0.03, lean=4.0, back2=0.1, z2=0.5, fwd3=0.16, z3=0.42,
        strike=-14.0, arm_swing=40.0, arm_mean=-8.0, elbow=96.0, elbow_swing=22.0, arm_out=16.0, fist=0.2, twist=10.0,
        shrug=6.0, head_steady=0.6, head_nod=4.0, hip=0.865, hunch=-3.0, back_out=21.0),
    "farmhand": dict(
        label="Farmhand", text="Gangly and loose-limbed: the feet turned out, the elbows flapping out to the sides, "
        "floppy wrists, the head nodding along.",
        frames=42, stance=0.215, land=0.33, hip=0.855, float=0.75, track=0.22, toe_out=16.0, knee_out=10.0, bow=0.07,
        sway=0.025, lean=7.0, strike=-16.0, arm_swing=26.0, arm_mean=-4.0, arm_out=30.0, back_out=14.0, elbow=80.0,
        elbow_swing=16.0, arm_across=4.0, fist=0.2, wrist=14.0, wrist_swing=15.0, twist=8.0, head_steady=0.5,
        head_nod=5.0),
    "monk": dict(
        label="Monk", text="Calm and contained: very upright, the arms bent tight and close and barely swinging, quick "
        "light steps, the head quite still.",
        frames=36, stance=0.235, land=0.29, hip=0.87, float=0.6, lean=3.0, pelvis_tilt=1.0, back2=0.16, z2=0.42,
        fwd3=0.1, z3=0.34, strike=-12.0, arm_swing=8.0, arm_mean=6.0, elbow=100.0, elbow_swing=4.0, arm_out=10.0,
        back_out=5.0, arm_across=12.0, fist=0.5, twist=2.0, pelvis_yaw=5.0, head_steady=1.0, head_pitch=2.0,
        head_nod=0.5),
    "dancer": dict(
        label="Dancer", text="Light and graceful: the feet landing on one line, the hips swaying, the arms floating "
        "out with soft hands, the chin lifted.",
        frames=40, stance=0.18, land=0.215, track=0.02, toe_out=14.0, bow=0.06, hip=0.875, float=1.0, lean=3.0,
        hunch=-4.0, strike=-14.0, pelvis_drop=8.0, pelvis_yaw=10.0, sway=0.03, arm_swing=30.0, arm_mean=-2.0,
        arm_out=22.0, back_out=10.0, elbow=40.0, elbow_swing=16.0, fist=0.05, wrist=16.0, wrist_swing=12.0, twist=8.0,
        head_pitch=-4.0),

    # arms and rhythm
    "straight": dict(
        label="Straight arms", text="The arms swinging nearly straight from the shoulders, like a boy at play: long "
        "arcs forward and back with open hands, an upright, bouncy run.",
        frames=40, stance=0.215, land=0.3, hip=0.87, float=0.95, lean=5.0, back2=0.12, z2=0.48, fwd3=0.16, z3=0.4,
        strike=-16.0, arm_swing=44.0, arm_mean=-6.0, elbow=18.0, elbow_swing=8.0, arm_out=14.0, back_out=10.0,
        arm_across=4.0, fist=0.2, twist=12.0, head_steady=0.8),
    "wings": dict(
        label="Wide arms", text="The arms swinging long and wide, out to the sides and round, the hands passing far "
        "from the body: a broad, open run.",
        frames=40, stance=0.225, land=0.31, lean=9.0, arm_swing=30.0, arm_mean=-4.0, arm_out=32.0, back_out=18.0,
        elbow=40.0, elbow_swing=14.0, arm_across=0.0, fist=0.3, twist=8.0, shrug=8.0),
    "twister": dict(
        label="Cross-body", text="The shoulders turning far against the hips, the arms swinging round in front of the "
        "chest with them, the whole trunk winding and unwinding with each step.",
        frames=42, stance=0.21, land=0.31, lean=5.0, arm_swing=42.0, arm_mean=-8.0, arm_across=2.0, arm_out=14.0,
        back_out=22.0, elbow=100.0, elbow_swing=12.0, fist=0.6, twist=20.0, pelvis_yaw=14.0, head_steady=0.95),
    "piston": dict(
        label="Piston arms", text="The arms driving straight forward and back like pistons, close by the sides, the "
        "fists punching ahead and pulling hard behind, a strong upright run.",
        frames=38, stance=0.235, land=0.31, lean=8.0, arm_swing=46.0, arm_mean=-10.0, arm_out=6.0, back_out=17.0,
        arm_across=0.0, arm_loop=0.0, elbow=88.0, elbow_swing=28.0, fist=0.95, snap=0.25, twist=6.0, shrug=4.0,
        protract=12.0),
    "stepper": dict(
        label="High stepper", text="The knees lifted high in front with every stride and the feet stepping down onto "
        "the heel, the body tall, the arms pumping to match.",
        frames=42, stance=0.195, land=0.275, hip=0.875, float=0.9, lean=4.0, back1=0.3, z1=0.4, back2=0.1, z2=0.46,
        fwd3=0.26, z3=0.56, reach=0.02, z4=0.24, strike=-14.0, arm_swing=40.0, elbow=90.0, elbow_swing=16.0, fist=0.6,
        twist=8.0, arm_out=18.0, back_out=15.0, arm_across=3.0),
    "gazelle": dict(
        label="Gazelle", text="Light, leaping strides: a quick spring off each foot into a long float, the knees "
        "lifting, the arms swinging light and high, the body tall.",
        frames=48, stance=0.17, land=0.275, hip=0.875, float=1.3, lean=5.0, back2=0.1, z2=0.5, fwd3=0.22, z3=0.46,
        strike=-14.0, arm_swing=42.0, arm_mean=2.0, elbow=70.0, elbow_swing=14.0, arm_out=16.0, fist=0.2, twist=10.0,
        back_out=12.0),
    "drummer": dict(
        label="Drumbeat", text="A marked, even beat: each landing punctuated by a dip of the head and body, the arms "
        "snapping through their swing and holding at the ends.",
        frames=46, stance=0.19, land=0.3, lean=5.0, float=0.8, sink=0.025, bounce_lean=4.0, snap=0.5, arm_swing=36.0,
        elbow=70.0, elbow_swing=16.0, fist=0.7, twist=8.0, head_nod=6.0, head_steady=0.7, arm_out=14.0, z2=0.38,
        back_out=18.0),
    "silk": dict(
        label="Fluid", text="Soft and flowing: the arms trailing the legs and swinging in loose loops, the wrists "
        "relaxed, every step easing into the next.",
        frames=42, stance=0.205, land=0.29, lean=8.0, float=0.8, catch=0.9, land_drop=0.5, arm_lag=0.08, arm_loop=0.16,
        arm_swing=36.0, elbow=74.0, elbow_swing=20.0, wrist_swing=14.0, fist=0.15, twist=10.0, head_steady=0.85,
        arm_out=16.0, arm_across=3.0, back_out=12.0),
}

# Round 2 (16 November), from the user's ratings of the fifty (ratings/round1.json): Athletic was their favourite, 7 of
# 10, and their comments came back to the same few things. The feet flared out in nearly every run (all fifty turned
# them out 6° or more); the chest wanted a firm forward lean, neither upright nor bent over; the knees wanted to come
# up about as far as Athletic's; less bounce; the arms bent near a right angle and swinging freely, not tucked up or
# held high, nor flung wide; nothing aggressive or goofy. So every round-2 run points its feet and knees straight
# ahead, lands them a little nearer the line and holds the head steadier (STRAIGHT); five are Athletic with one more
# thing changed each, five the user's other favourites changed as their comments asked.
STRAIGHT = dict(toe_out=1.0, knee_out=1.0, track=0.13, head_steady=0.92, head_nod=1.0)


def _from(parent, label, text, **change):
    """A round-2 run: the parent run's numbers, with STRAIGHT's and then change over them."""
    return {**{n: v for n, v in STYLES[parent].items() if n not in ("label", "text")}, **STRAIGHT, "label": label,
            "text": text, **change}


STYLES.update({
    "athletic_straight": _from(
        "athletic", "Athletic, feet straight", "Athletic as it was, but with the feet and knees pointing straight "
        "ahead, landing a little nearer the line, and the head steadier. The other Athletics each change one more "
        "thing from this one."),
    "athletic_settled": _from(
        "athletic", "Athletic, settled", "Less bounce: a lower float between steps and less of a dip after each "
        "landing, so the head and body ride more level.", float=0.35, bounce_lean=0.8),
    "athletic_lean": _from(
        "athletic", "Athletic, leaning in", "The chest a little further forward, and the head with it.", lean=18.0,
        head_pitch=8.0),
    "athletic_knees": _from(
        "athletic", "Athletic, high knees", "The knees lifting higher and further forward, the heels kicking up a "
        "little more.", z3=0.47, fwd3=0.19, z2=0.54),
    "athletic_arms": _from(
        "athletic", "Athletic, loose arms", "The arms more relaxed: the shoulders dropped, the elbows opened a little, "
        "the hands half open, swinging a little lower and less far.", arm_swing=36.0, elbow=84.0, elbow_swing=14.0,
        shoulders=-2.0, fist=0.4, wrist_swing=8.0, arm_out=17.0, back_out=15.0),
    "trail_knees": _from(
        "trail", "Trail runner, higher knees", "Trail runner's chest and quick steps, the knees now lifting higher.",
        z3=0.41, fwd3=0.15, z2=0.45, track=0.15),
    "ducking_arms": _from(
        "ducking", "Ducking, arms relaxed", "Ducking's low, steady run, the shoulders now dropped and the arms "
        "swinging loose instead of held up tight.", shoulders=2.0, elbow=96.0, arm_mean=0.0, arm_swing=28.0,
        arm_out=16.0, back_out=14.0, arm_across=5.0, elbow_swing=12.0, fist=0.5),
    "ranger_calm": _from(
        "ranger", "Ranger, less bounce", "Ranger's long easy strides and loose arms, with much less bounce.",
        float=0.4),
    "glide_knees": _from(
        "glide", "Glide, higher knees", "Glide's smooth, level run and easy arms, the knees now lifting higher.",
        z3=0.39, fwd3=0.17, z2=0.42),
    "strider_arms": _from(
        "strider", "Long strider, arms bent", "Long strider's reaching steps, the arms now bent, swinging a shorter "
        "and higher arc, the chest leaning in a little.", elbow=80.0, arm_mean=-4.0, arm_swing=32.0, arm_out=15.0,
        back_out=15.0, lean=8.0, knee_out=2.0, track=0.15),
})

# the runs in families, for the portfolio's page and in STYLES's order: (title, what its runs have in common, runs)
FAMILIES = [
    ("The first ten", "The runs from before, now planting the heel first.",
     ["athletic", "sprint", "easy", "heroic", "heavy", "nimble", "guarded", "bounding", "snappy", "natural"]),
    ("Runners", "Real runners' forms, from the marathon to the trail.",
     ["marathon", "miler", "trail", "strider", "quickstep", "glide", "springy", "courier"]),
    ("Fighters", "Fighting men on the move, from the charge to the soldier's double time.",
     ["charge", "barbarian", "brawler", "berserker", "soldier", "knight", "bull", "stomper", "boxer", "veteran",
      "ducking"]),
    ("The wilds", "Stealth and the hunt: low, quiet and watchful.",
     ["prowler", "rogue", "scout", "ranger", "hunter", "lope"]),
    ("Moods and people", "How a mood, or a kind of man, runs.",
     ["swagger", "weary", "fleeing", "eager", "farmhand", "monk", "dancer"]),
    ("Arms and rhythm", "Ways with the arms, and with the beat.",
     ["straight", "wings", "twister", "piston", "stepper", "gazelle", "drummer", "silk"]),
    ("Athletic, refined", "Athletic, the best of round 1, its feet straight, and four more each changing one thing.",
     ["athletic_straight", "athletic_settled", "athletic_lean", "athletic_knees", "athletic_arms"]),
    ("Favourites, fixed", "Round 1's other best runs, changed as the user's comments asked, their feet straight too.",
     ["trail_knees", "ducking_arms", "ranger_calm", "glide_knees", "strider_arms"]),
]
assert [k for _t, _x, keys in FAMILIES for k in keys] == list(STYLES), "FAMILIES: every run once, in STYLES's order"
# the rounds the user rates the runs in, on the portfolio's page (make_runs.py's ROUND): each round's families
ROUNDS = {1: [t for t, _x, _k in FAMILIES[:6]], 2: ["Athletic, refined", "Favourites, fixed"]}


def round_runs(n):
    """Round n's runs, in its families' order."""
    return [k for t, _x, keys in FAMILIES if t in ROUNDS[n] for k in keys]


assert sorted(k for n in ROUNDS for k in round_runs(n)) == sorted(STYLES), "ROUNDS: every run in one round"


# each run's numbers as made here, every setting of DEFAULTS (the run editor's Reset goes back to them)
AS_MADE = {k: dict(DEFAULTS, **{n: v for n, v in spec.items() if n in DEFAULTS}) for k, spec in STYLES.items()}


def tuned(saved=None):
    """The runs' numbers with the saved tuning (run_settings.json, or saved: {run: {setting: value}}) over them, as
    the run editor leaves them: {run: {setting: value}}."""
    if saved is None:
        saved = {}
        if os.path.exists(SETTINGS):
            with open(SETTINGS, encoding="utf-8") as fh:
                saved = json.load(fh)
    return {k: dict(v, **{n: float(x) for n, x in saved.get(k, {}).items() if n in DEFAULTS})
            for k, v in AS_MADE.items()}


for _k, _v in tuned().items():  # the runs as tuned, for every tool that reads STYLES
    STYLES[_k].update(_v)


def rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 3, Vector(axis))


def turned(yaw, roll, pitch):
    """The turn of the pelvis or the chest, degrees: tipped forward (pitch), rolled to the side, then turned about the
    up axis (yaw)."""
    return rot(UP, yaw) @ rot((0, 1, 0), roll) @ rot((1, 0, 0), pitch)


def frame(d, n):
    """An orthonormal frame, its columns d, n made square to d, and d x n."""
    d = d.normalized()
    n = (n - d * n.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed()


def turn_to(d0, n0, d1, n1):
    """The turn taking the frame of d0 and n0 to that of d1 and n1."""
    return frame(d1, n1) @ frame(d0, n0).transposed()


def slerp(a, b, t):
    return a.to_quaternion().slerp(b.to_quaternion(), t).to_matrix()


def smooth(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def wave(x, snap=0.0):
    """cos(2 pi x), sharpened by snap: held longer at the ends, quicker through the middle (a soft clip, smooth
    everywhere)."""
    c = math.cos(2.0 * math.pi * x)
    if not snap:
        return c
    k = 3.0 * snap
    return math.tanh(k * c) / math.tanh(k)


def hermite(keys, t):
    """The point at t on a curve through keys, [(t, point, tangent)] in order."""
    for (t0, p0, m0), (t1, p1, m1) in zip(keys, keys[1:]):
        if t <= t1 or (t1 == keys[-1][0]):
            h = t1 - t0
            s = min(max((t - t0) / h, 0.0), 1.0)
            s2, s3 = s * s, s * s * s
            return (p0 * (2 * s3 - 3 * s2 + 1) + m0 * (h * (s3 - 2 * s2 + s)) + p1 * (3 * s2 - 2 * s3)
                    + m1 * (h * (s3 - s2)))
    return keys[-1][1].copy()


class Rest:
    """The skeleton at rest, in the armature's space, and the joints the run works with. heel and toe: {side: the
    point at the back of the heel and the tip of the toes, on the ground}, from the model's mesh."""

    def __init__(self, arm, heel, toe):
        bones = arm.data.bones
        self.mat = {b.name: b.matrix_local.copy() for b in bones}
        self.inv = {n: m.inverted() for n, m in self.mat.items()}
        self.rot = {n: m.to_3x3().normalized() for n, m in self.mat.items()}
        self.head = {b.name: b.head_local.copy() for b in bones}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in bones}
        self.order = []

        def visit(b):
            self.order.append(b.name)
            for c in b.children:
                visit(c)
        for b in bones:
            if b.parent is None:
                visit(b)
        h = self.head
        self.legs, self.arms, self.fingers = {}, {}, {}
        for s in "lr":
            hip, knee, ankle, ball = h[f"thigh_{s}"], h[f"calf_{s}"], h[f"foot_{s}"], h[f"ball_{s}"]
            t, sh = knee - hip, ankle - knee
            ab = ball - ankle
            self.legs[s] = dict(hip=hip, knee=knee, ankle=ankle, ball=ball, L1=t.length, L2=sh.length,
                                t=t.normalized(), s=sh.normalized(), n=t.cross(sh).normalized(),
                                heading=Vector((ab.x, ab.y, 0.0)).normalized(), heel=heel[s], toe=toe[s])
            shoulder, elbow, wrist = h[f"upperarm_{s}"], h[f"lowerarm_{s}"], h[f"hand_{s}"]
            u, f = (elbow - shoulder).normalized(), (wrist - elbow).normalized()
            self.arms[s] = dict(u=u, f=f, n=u.cross(f).normalized())
            along = (h[f"middle_01_{s}"] - h[f"hand_{s}"]).normalized()
            across = (h[f"index_01_{s}"] - h[f"pinky_01_{s}"]).normalized()
            palm = (along.cross(across) * (1.0 if s == "l" else -1.0)).normalized()  # toward the palm
            # a finger curls into the palm; the thumb across it too, so in a fist it lies over the fingers rather
            # than poking out in front of them
            thumb_way = (palm - across * THUMB_ACROSS).normalized()
            axes = {}
            for name in self.order:
                if name.endswith("_" + s) and name.split("_")[0] in FINGERS + ("thumb",):
                    d = self.rot[name].col[1].copy().normalized()
                    axes[name] = d.cross(thumb_way if name.startswith("thumb") else palm).normalized()
            self.fingers[s] = axes
        self.hip_mid = (h["thigh_l"] + h["thigh_r"]) / 2
        self.skirt = [n for n in ("skirt_f", "skirt_b", "skirt_l", "skirt_r") if n in self.mat]  # cloth bones
        self.helpers = {}
        for name, (parent, child) in HELPER_JOINTS.items():
            for s in "lr":
                if f"{name}_{s}" in self.mat:
                    p = parent if parent == "pelvis" else f"{parent}_{s}"
                    self.helpers[f"{name}_{s}"] = (p, f"{child}_{s}")


def posed(rest, P, offsets):
    """The posed bones' matrices in armature space. P: each bone's whole turn from rest, in armature space (a bone left
    out turns with its parent); offsets: bone -> a shift of its head (the pelvis's)."""
    turns, M = {}, {}
    for n in rest.order:
        p = rest.parent[n]
        R = P[n] if n in P else (turns[p] if p else Matrix.Identity(3))
        turns[n] = R
        head = (M[p] @ (rest.inv[p] @ rest.head[n])) if p else rest.head[n].copy()
        if n in offsets:
            head = head + offsets[n]
        m = (R @ rest.rot[n]).to_4x4()
        m.translation = head
        M[n] = m
    return M


def bases(rest, M):
    """Each pose bone's location and rotation (its own axes, from rest) for the posed matrices M."""
    out = {}
    for n in rest.order:
        p = rest.parent[n]
        ref = (M[p] @ rest.inv[p] @ rest.mat[n]) if p else rest.mat[n]
        loc, q, _ = (ref.inverted() @ M[n]).decompose()
        out[n] = (loc, q)
    return out


def two_bone(hip, target, L1, L2, pole):
    """The knee of a leg from hip to target, bending toward pole; also the ankle (pulled in if out of reach) and the
    hinge axis. stretch: how much of the leg's length the target asks for."""
    d = target - hip
    dist = d.length
    reach = (L1 + L2) * 0.9995
    stretch = dist / (L1 + L2)
    if dist > reach:
        d = d * (reach / dist)
        dist = reach
    dn = d.normalized()
    cos_a = (L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist)
    a = math.acos(min(max(cos_a, -1.0), 1.0))
    side = (pole - dn * pole.dot(dn)).normalized()
    knee = hip + (dn * math.cos(a) + side * math.sin(a)) * L1
    return knee, hip + d, side.cross(dn).normalized(), stretch


class Run:
    """A run cycle in a style; pose(phase) gives each bone's turn for a moment of it, phase 0 to 1 from the left foot
    landing (the right lands at 0.5)."""

    def __init__(self, rest, style):
        self.rest = rest
        self.k = k = dict(DEFAULTS, **{n: v for n, v in style.items() if n in DEFAULTS})
        self.frames = int(k["frames"])
        self.T = self.frames / FPS
        self.D = k["stance"]
        self.heading, self.flat = {}, {}
        for s in "lr":
            sign = 1.0 if s == "l" else -1.0
            hd = rot(UP, sign * k["toe_out"]) @ FWD
            h0 = rest.legs[s]["heading"]
            self.heading[s] = hd
            self.flat[s] = Matrix.Rotation(math.atan2(h0.cross(hd).z, h0.dot(hd)), 3, "Z")
        self._ends = {}
        self.swing_keys = {s: self._swing_keys(s) for s in "lr"}

    # the hips' height: sinking into each landing, flying between steps
    def hip_height(self, phase):
        k, D, T = self.k, self.D, self.T
        s = (phase % 0.5) / 0.5
        Ds = D / 0.5
        tf = (0.5 - D) * T
        v = k["float"] * G * tf / 2
        if s < Ds:
            tau = s / Ds
            return (k["hip"] - v * D * T / math.pi * math.sin(math.pi * tau)
                    - k["sink"] * (1 - math.cos(2 * math.pi * tau)) / 2)
        t = (s - Ds) * 0.5 * T
        return k["hip"] + k["float"] * (G * tf / 2 * t - G * t * t / 2)

    def pelvis_angles(self, phase):
        """The pelvis's turn (degrees, as turned): the hip of the leg in front turned forward (the left at the left
        foot's landing), the side of the leg in the air dropping, tipping forward."""
        k, D = self.k, self.D
        c = math.cos(2 * math.pi * (phase - D / 2))  # 1 at the left foot's mid-stance, -1 at the right's
        return (-k["pelvis_yaw"] * math.cos(2 * math.pi * (phase + 0.02)), -k["pelvis_drop"] * c,
                k["pelvis_tilt"] + k["tilt_swing"] * math.cos(4 * math.pi * (phase - D - 0.02)))

    def pelvis(self, phase):
        """The pelvis's turn and the shift of its head, the hips over the foot on the ground."""
        c = math.cos(2 * math.pi * (phase - self.D / 2))
        off = Vector((self.k["sway"] * c, 0.0, self.hip_height(phase) - self.rest.hip_mid.z))
        return turned(*self.pelvis_angles(phase)), off

    def head_turn(self, phase):
        """How far the head turns of itself, looking about (degrees): not while running."""
        return 0.0

    def thorax_yaw(self, phase):
        """The shoulders' turn: the right one forward as the left foot lands, with the right arm."""
        return self.k["twist"] * math.cos(2 * math.pi * (phase - self.k["arm_lag"]))

    def thorax_angles(self, phase, hunch=1.0):
        """The chest's turn (degrees, as turned), with this much of the run's hunch (none for the lower back's share
        of the lean)."""
        k, D = self.k, self.D
        c = math.cos(2 * math.pi * (phase - D / 2))
        dip = k["bounce_lean"] * math.cos(4 * math.pi * (phase - D / 2 - 0.05))
        return self.thorax_yaw(phase), k["rock"] * c, k["lean"] + dip + k["hunch"] * hunch

    def thorax(self, phase, hunch=1.0):
        """The chest's turn."""
        return turned(*self.thorax_angles(phase, hunch))

    # one foot on the ground, p from 0 (landing) to the stance's end
    def planted(self, s, p):
        k, leg = self.k, self.rest.legs[s]
        tau = p / self.D
        theta = k["strike"] * (1 - smooth(0.0, k["flat_at"], tau))
        rise = min(max((tau - k["heel_at"]) / (1.0 - k["heel_at"]), 0.0), 1.0)
        # half an S, half speeding up: the heel still rising as the foot leaves, so the knee starts to bend
        theta += k["push"] * (0.6 * smooth(0.0, 1.0, rise) + 0.4 * rise * rise)
        side = 1.0 if s == "l" else -1.0
        x = self.rest.hip_mid.x + side * k["track"] / 2
        A = Vector((x, leg["hip"].y - k["land"] + SPEED * p * self.T, leg["ankle"].z))
        F = self.flat[s]
        axis = UP.cross(self.heading[s]).normalized()
        Rp = Matrix.Rotation(math.radians(theta), 3, axis)
        pivot = A + F @ ((leg["ball"] if theta >= 0 else leg["heel"]) - leg["ankle"])
        ankle = pivot + Rp @ (A - pivot)
        foot = Rp @ F
        toes = F if theta > 0 else foot
        return ankle, foot, toes, theta

    def hip_at(self, s, phase):
        """Where a hip joint is at a moment of the cycle."""
        R, off = self.pelvis(phase)
        ph = self.rest.head["pelvis"]
        return ph + off + R @ (self.rest.legs[s]["hip"] - ph)

    def _swing_keys(self, s):
        """The ankle's path in the air, as keys of a curve over the swing (0 at toe-off, 1 at landing). Its points are
        kept within the leg's reach, and it leaves and meets the ground going round the hip, not away from it."""
        k, leg, D = self.k, self.rest.legs[s], self.D
        side = 1.0 if s == "l" else -1.0
        x = self.rest.hip_mid.x + side * k["track"] / 2
        hy = leg["hip"].y
        reach = (leg["L1"] + leg["L2"]) * 0.97

        def hip(t):
            return self.hip_at(s, (D + t * (1 - D) + (0.0 if s == "l" else 0.5)) % 1.0)

        def inside(t, pt):
            d = pt - hip(t)
            return hip(t) + d * (reach / d.length) if d.length > reach else pt

        def round_hip(t, pt, v):
            r = (pt - hip(t)).normalized()
            out = v.dot(r)
            return v - r * out if out > 0 else v
        e = 1e-4
        a0 = self.planted(s, D)[0]
        v0 = (a0 - self.planted(s, D - e)[0]) / e * (1 - D)  # per unit of the swing
        a5 = self.planted(s, 0.0)[0]
        v5 = (self.planted(s, e)[0] - a5) / e * (1 - D)
        pts = [(0.0, a0), (0.2, Vector((x, hy + k["back1"], k["z1"]))), (0.47, Vector((x, hy + k["back2"], k["z2"]))),
               (0.72, Vector((x, hy - k["fwd3"], k["z3"]))), (0.9, Vector((x, a5.y - k["reach"], k["z4"]))), (1.0, a5)]
        pts = [(t, pt if i in (0, len(pts) - 1) else inside(t, pt)) for i, (t, pt) in enumerate(pts)]
        keys = []
        for i, (t, pt) in enumerate(pts):
            if i == 0:  # toe-off: as the foot left the ground
                m = v0
            elif i == len(pts) - 1:  # landing: going back, but not yet at the ground's speed, and coming down
                m = round_hip(t, pt, v5) * k["catch"] - Vector((0.0, 0.0, k["land_drop"] * self.T * (1 - D)))
            else:
                m = (pts[i + 1][1] - pts[i - 1][1]) / (pts[i + 1][0] - pts[i - 1][0])
            keys.append((t, pt, m))
        return keys

    def ankle_swing(self, s, tau):
        """The ankle in the air, held softly within the leg's reach (the curve between its points can bulge): what
        stretches the leg past a limit is squeezed into the room left below full length. At toe-off and landing the
        limit is the stretch the foot on the ground had, so the ankle leaves and meets it at the same speed."""
        a = hermite(self.swing_keys[s], tau)
        side = 1.0 if s == "l" else -1.0
        a.x += side * self.k["bow"] * math.sin(math.pi * tau)
        leg = self.rest.legs[s]
        full = leg["L1"] + leg["L2"]
        hip = self.hip_at(s, (self.D + tau * (1 - self.D) + (0.0 if s == "l" else 0.5)) % 1.0)
        d = a - hip
        ends = self._swing_ends(s)
        soft = (0.95 * full + max(0.0, ends[0] - 0.95 * full) * (1 - smooth(0.0, 0.3, tau))
                + max(0.0, ends[1] - 0.95 * full) * smooth(0.7, 1.0, tau))
        room = max(0.995 * full - soft, 0.001)
        if d.length > soft:
            a = hip + d * ((soft + room * math.tanh((d.length - soft) / room)) / d.length)
        return a

    def _swing_ends(self, s):
        """How far the hip is from the ankle at toe-off and at landing."""
        if s not in self._ends:
            off = 0.0 if s == "l" else 0.5
            self._ends[s] = ((self.planted(s, self.D)[0] - self.hip_at(s, (self.D + off) % 1.0)).length,
                             (self.planted(s, 0.0)[0] - self.hip_at(s, off)).length)
        return self._ends[s]

    def leg(self, s, phase, P_pelvis, pelvis_head):
        """The turns of one leg's bones (thigh, calf, foot, ball) at this moment, and how far the leg stretched."""
        k, leg, D = self.k, self.rest.legs[s], self.D
        p = (phase - (0.0 if s == "l" else 0.5)) % 1.0
        if p < D:
            ankle, foot, toes, _ = self.planted(s, p)
            w_ground, w_toes = 1.0, 1.0
            tau = None
        else:
            tau = (p - D) / (1 - D)
            ankle = self.ankle_swing(s, tau)
            w_ground = 1.0 - smooth(0.0, 0.25, tau) + smooth(0.6, 0.97, tau)
            w_toes = 1.0 - smooth(0.0, 0.2, tau)
            if k["strike"] > 0:  # landing on the forefoot: the toes come up to meet the ground
                w_toes += smooth(0.8, 1.0, tau)
        hip = pelvis_head + P_pelvis @ (leg["hip"] - self.rest.head["pelvis"])
        sign = 1.0 if s == "l" else -1.0
        pole = rot(UP, sign * k["knee_out"]) @ FWD
        knee, ankle_got, hinge, stretch = two_bone(hip, ankle, leg["L1"], leg["L2"], pole)
        P_thigh = turn_to(leg["t"], leg["n"], knee - hip, hinge)
        P_calf = turn_to(leg["s"], leg["n"], ankle_got - knee, hinge)
        if tau is not None:
            # in the air the foot hangs off the shank, pointing a little down, and late in the swing comes up, the
            # toes toward the shin, so the heel leads it down
            beta = 18.0 * (1 - smooth(0.3, 0.85, tau)) - k["dorsi"] * smooth(0.5, 0.85, tau)
            free = P_calf @ rot(leg["n"], beta)  # beta above 0 points the toes down
            # the foot's pitch on the ground's terms: from toe-off, turning on as fast as it left the ground, to the
            # landing's, which it has by LANDING_PITCH of the swing and holds as it comes down
            u = min(tau / LANDING_PITCH, 1.0)
            m0 = 0.8 * k["push"] / (1.0 - k["heel_at"]) * (1.0 - D) / D * LANDING_PITCH
            u2, u3 = u * u, u * u * u
            theta = (k["push"] * (2 * u3 - 3 * u2 + 1) + m0 * (u3 - 2 * u2 + u)
                     + k["strike"] * (3 * u2 - 2 * u3))
            axis = UP.cross(self.heading[s]).normalized()
            ground = Matrix.Rotation(math.radians(theta), 3, axis) @ self.flat[s]
            foot = slerp(free, ground, w_ground)
            toes = slerp(foot, self.flat[s], w_toes)
        return {f"thigh_{s}": P_thigh, f"calf_{s}": P_calf, f"foot_{s}": foot, f"ball_{s}": toes}, stretch

    def arm(self, s, phase, P_thorax):
        k, arm = self.k, self.rest.arms[s]
        sign = 1.0 if s == "l" else -1.0
        peak = (0.5 if s == "l" else 0.0) + k["arm_lag"]
        c = wave(phase - peak, k["snap"])
        swing = k["arm_mean"] + k["arm_swing"] * c
        # the in and out lead the swing a little, so the hand goes round a loop, not back and forth on one arc:
        # coming in across the body on its way forward, out past the hip on its way back
        c_loop = math.cos(2.0 * math.pi * (phase - peak + k["arm_loop"]))
        out = k["arm_out"] + k["back_out"] * (1 - c_loop) / 2
        across = k["arm_across"] * (0.6 + 0.4 * c_loop)
        elbow = k["elbow"] + k["elbow_swing"] * wave(phase - peak - 0.04, k["snap"])
        lift = rot((1, 0, 0), -swing) @ rot((0, 1, 0), -sign * out)
        d = P_thorax @ (lift @ Vector((0.0, 0.0, -1.0)))
        n = P_thorax @ (lift @ Vector((-1.0, 0.0, 0.0)))
        n = Matrix.Rotation(math.radians(sign * across), 3, d) @ n
        f = Matrix.Rotation(math.radians(elbow), 3, n) @ d
        P_upper = turn_to(arm["u"], arm["n"], d, n)
        P_fore = turn_to(arm["f"], arm["n"], f, n)
        P_hand = P_fore @ rot(arm["n"], k["wrist"] + k["wrist_swing"] * wave(phase - peak - 0.1))
        clav = (P_thorax @ rot((0, 1, 0), -sign * (k["shrug"] * (1 + c) / 2 + k["shoulders"]))
                @ rot(UP, -sign * k["protract"] * c))
        out = {f"clavicle_{s}": clav, f"upperarm_{s}": P_upper, f"lowerarm_{s}": P_fore, f"hand_{s}": P_hand}
        out.update(self.hand(s, P_hand))
        return out

    def hand(self, s, P_hand, fist=None):
        f = self.k["fist"] if fist is None else fist
        axes = self.rest.fingers[s]
        bends = {1: 70.0 * f, 2: 85.0 * f, 3: 55.0 * f}
        out = {}
        for name in FINGERS + ("thumb",):
            parent = P_hand
            for i in (1, 2, 3):
                bone = f"{name}_0{i}_{s}"
                if bone not in axes:
                    continue
                deg = bends[i] * (THUMB[i - 1] if name == "thumb" else 1.0)
                parent = parent @ rot(axes[bone], deg)
                out[bone] = parent
        return out

    def pose(self, phase):
        """{bone: whole turn from rest}, {bone: head shift}, and how far each leg stretched."""
        k = self.k
        P_pelvis, off = self.pelvis(phase)
        pelvis_head = self.rest.head["pelvis"] + off
        P = {"pelvis": P_pelvis}
        P_thorax = self.thorax(phase)
        # the spine turning from the pelvis to the chest: its twist and roll evenly, its lean more low down (SPINE), a
        # hunch rounding only its upper part
        pelvis_angles = self.pelvis_angles(phase)
        for i, (name, hunch) in enumerate((("spine_01", 0.0), ("spine_02", 0.6), ("spine_03", 1.0))):
            (y0, r0, p0), (y1, r1, p1) = pelvis_angles, self.thorax_angles(phase, hunch)
            w = (i + 1) / 3
            P[name] = turned(y0 + (y1 - y0) * w, r0 + (r1 - r0) * w, p0 + (p1 - p0) * SPINE[i])
        nod = k["head_nod"] * math.cos(4 * math.pi * (phase - self.D / 2 - 0.09))
        P_head = (rot(UP, self.thorax_yaw(phase) * (1 - k["head_steady"]) + self.head_turn(phase))
                  @ rot((1, 0, 0), k["head_pitch"] + nod))
        P["neck_01"] = slerp(P_thorax, P_head, 0.5)
        P["head"] = P_head
        stretch = {}
        for s in "lr":
            legs, stretch[s] = self.leg(s, phase, P_pelvis, pelvis_head)
            P.update(legs)
            P.update(self.arm(s, phase, P_thorax))
        for h, (parent, child) in self.rest.helpers.items():
            P[h] = P[parent] @ slerp(Matrix.Identity(3), P[parent].transposed() @ P[child], 0.5)
        if self.rest.skirt:
            P.update(self.skirt(phase, P))
        return P, {"pelvis": off}, stretch

    def skirt(self, phase, P):
        """The cloth bones' turns: the skirt's front pushed out by the knee driving forward, its back by the leg behind,
        each side going with its thigh, and the hem swinging on after each landing."""
        k = self.k
        swing = {}
        for s in "lr":
            d = P["pelvis"].transposed() @ (P[f"thigh_{s}"] @ self.rest.legs[s]["t"])  # the thigh in the hips' frame
            swing[s] = math.degrees(math.atan2(-d.y, -d.z))  # forward of hanging straight down
        flutter = k["skirt_flutter"] * math.cos(4 * math.pi * (phase - self.D / 2 - 0.12))
        front = max(0.0, max(swing.values()) - 12.0) * k["skirt_push"] + flutter
        back = max(0.0, -min(swing.values()) - 4.0) * k["skirt_push"] + flutter
        X = (1, 0, 0)
        return {"skirt_f": P["pelvis"] @ rot(X, -front), "skirt_b": P["pelvis"] @ rot(X, back),
                "skirt_l": P["pelvis"] @ rot(X, -0.35 * swing["l"]),
                "skirt_r": P["pelvis"] @ rot(X, -0.35 * swing["r"])}


class Stand(Run):
    """Standing at ease, for when the hero stops: the weight on the left leg, the right hip lower and its knee easy,
    the shoulders tilting against the hips, the arms down; a slow breath, the weight swaying a little on its own
    timing, the head looking a little to either side (a 4 s loop)."""

    def __init__(self, rest):
        super().__init__(rest, dict(frames=240, arm_swing=0.0, arm_mean=-3.0, arm_out=7.0, arm_across=3.0,
                                    elbow=16.0, elbow_swing=3.0, arm_lag=0.0, shrug=1.5, protract=0.0, wrist=4.0,
                                    wrist_swing=1.0, fist=0.25, head_pitch=3.0, head_nod=0.0, twist=0.0, snap=0.0))

    def pelvis_angles(self, phase):  # the right hip lower and a little forward, with the free foot
        return 3.0, -3.5, 2.0

    def pelvis(self, phase):
        b = math.sin(2 * math.pi * phase + 0.6)  # the sway a little behind the breath
        off = Vector((0.025 + 0.004 * b, 0.0, -0.003))  # over the left foot, its leg straight, swaying a little
        return turned(*self.pelvis_angles(phase)), off

    def thorax_yaw(self, phase):
        return 0.0

    def head_turn(self, phase):  # a slow look to the left and the right, not quite even
        return 5.0 * math.sin(2 * math.pi * phase) + 1.5 * math.sin(4 * math.pi * phase + 0.8)

    def thorax_angles(self, phase, hunch=1.0):
        # the shoulders tilting against the hips, the right one higher; one slow breath a loop
        return -1.5, 2.5, 2.0 - 1.2 * math.sin(2 * math.pi * phase)

    def leg(self, s, phase, P_pelvis, pelvis_head):
        leg = self.rest.legs[s]
        sign = 1.0 if s == "l" else -1.0
        F = rot(UP, sign * (4.0 if s == "l" else 12.0)) @ self.flat[s]  # the free right foot turned out more
        ankle = Vector((self.rest.hip_mid.x + sign * 0.115, leg["hip"].y + (0.02 if s == "l" else -0.04),
                        leg["ankle"].z))
        hip = pelvis_head + P_pelvis @ (leg["hip"] - self.rest.head["pelvis"])
        knee, got, hinge, stretch = two_bone(hip, ankle, leg["L1"], leg["L2"], rot(UP, sign * 8.0) @ FWD)
        return {f"thigh_{s}": turn_to(leg["t"], leg["n"], knee - hip, hinge),
                f"calf_{s}": turn_to(leg["s"], leg["n"], got - knee, hinge), f"foot_{s}": F, f"ball_{s}": F}, stretch


def key_action(arm, name, run, rest):
    """An action of the run on arm's bones, one key a frame from 0 to run.frames (the last as the first), looping."""
    act = bpy.data.actions.get(name) or bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    if arm.animation_data.action_slot is None and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    prev = {}
    first = None
    for f in range(run.frames + 1):
        P, off, _ = run.pose(f / run.frames)
        b = bases(rest, posed(rest, P, off))
        if f == 0:
            first = b
        if f == run.frames:
            b = first
        for n, (loc, q) in b.items():
            if n in prev and prev[n].dot(q) < 0:
                q = -q
            prev[n] = q
            pb = arm.pose.bones[n]
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f, group=n)
            if n == "pelvis":
                pb.location = loc
                pb.keyframe_insert("location", frame=f, group=n)
    for fc in channelbag(act, arm).fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.modifiers.new("CYCLES")
    return act


def channelbag(act, ob):
    slot = ob.animation_data.action_slot or act.slots[0]
    return act.layers[0].strips[0].channelbag(slot)
