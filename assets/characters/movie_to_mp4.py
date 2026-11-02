"""Turns Godot's recordings (--write-movie, an MJPEG .avi) into H.264 .mp4 clips a web page can play, in Blender's
video editor, leaving out the seconds the demo spends loading.
    blender -b --factory-startup -P movie_to_mp4.py -- <in.avi> <out.mp4> [skip seconds] [width]"""
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
src, dst = os.path.abspath(args[0]), os.path.abspath(args[1])
skip = float(args[2]) if len(args) > 2 else 3.4
width = int(args[3]) if len(args) > 3 else 1280
scene = bpy.context.scene
scene.sequence_editor_create()
strip = scene.sequence_editor.strips.new_movie("Recording", src, 1, 1)
fps = round(strip.fps) or 30
scene.render.fps = fps
first = 1 + round(skip * fps)
scene.frame_start, scene.frame_end = first, strip.right_handle - 1  # its last frame
w, h = strip.elements[0].orig_width, strip.elements[0].orig_height
scene.render.resolution_x, scene.render.resolution_y = width, round(width * h / w / 2) * 2
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"  # the recording's colours as they are (AgX would wash them out)
ims = scene.render.image_settings
ims.media_type = "VIDEO"
ims.file_format = "FFMPEG"
ff = scene.render.ffmpeg
ff.format, ff.codec = "MPEG4", "H264"
ff.constant_rate_factor, ff.ffmpeg_preset = "MEDIUM", "GOOD"
base = os.path.splitext(dst)[0] + "_"
scene.render.filepath = base
scene.render.use_sequencer = True
bpy.ops.render.render(animation=True)
made = [f for f in os.listdir(os.path.dirname(dst)) if f.startswith(os.path.basename(base)) and f.endswith(".mp4")]
if made:
    os.replace(os.path.join(os.path.dirname(dst), made[0]), dst)
print("mp4", dst, f"{scene.frame_end - first + 1} frames at {fps}")
