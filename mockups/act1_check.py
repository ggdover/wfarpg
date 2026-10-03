import sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import act1_world as A
t=time.time()
x = np.arange(-1400, 990, 2.0); y = np.arange(-100, 1010, 2.0)
X, Y = np.meshgrid(x, y)
masks = A.zone_masks(X, Y)
walk = A.walkable(X, Y, masks)
H = A.height(X, Y, masks)
gy, gx = np.gradient(H, 2.0)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))
print("grid", X.shape, "time %.1fs" % (time.time()-t))
print("walkable km2 %.2f" % (walk.sum()*4/1e6))
for k,m in masks.items(): print("  zone %-12s %.3f km2" % (k, m.sum()*4/1e6))
ws = slope[walk]
print("slope walkable: max %.1f  p99 %.1f  p95 %.1f" % (ws.max(), np.percentile(ws,99), np.percentile(ws,95)))
print("height range walkable %.1f .. %.1f" % (H[walk].min(), H[walk].max()))
def inside(px,py):
    X1=np.array([[px]]); Y1=np.array([[py]])
    return bool(A.walkable(X1,Y1)[0,0])
bad=[]
for name,(pts,w,kind) in A.PATHS.items():
    out=[p for p in pts if not inside(*p)]
    if out: bad.append((name,len(out),len(pts),out[:3]))
print("paths with points outside:", bad)
for q in A.QUESTS:
    if not inside(*q[5]): print("quest outside", q[0], q[3])
for s in A.SHOTS:
    if not inside(*s[3]): print("shot outside", s[0])
for k,v in A.WAYSTONES.items():
    if not inside(*v): print("waystone outside", k)
# where is the steepest walkable slope?
idx=np.argmax(np.where(walk, slope, 0)); iy,ix=np.unravel_index(idx, slope.shape)
print("steepest at", X[iy,ix], Y[iy,ix])
