"""Helpers the demo's areas share: the mockups' noise and geometry (mockups/act1_world.py), and the parts of an area
module that only depend on its outline and paths. An area module (see storskogen.py) sets BOUNDARY, BAKE, FAR_R,
START, PATHS and the rest, and can take these:

    from areas.common import *
    path_dist, inside, boundary_dist = paths_and_outline(PATHS, BOUNDARY)
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "mockups"))
import act1_world as A  # noqa: E402

smoothstep, fbm, seg_dist, in_poly = A.smoothstep, A.fbm, A.seg_dist, A.in_poly
catmull_open, catmull_closed, ell = A.catmull_open, A.catmull_closed, A.ell
SPECIES = ["ScotsPine", "NorwaySpruce", "SilverBirch", "Aspen", "Rowan", "Alder"]
PINE, SPRUCE, BIRCH, ASPEN, ROWAN, ALDER = range(6)


def paths_and_outline(paths, boundary):
    """path_dist (distance from the nearest path's centre line, in its half-widths: 1 at its edge), inside (in the
    walkable outline) and boundary_dist (metres from the outline, positive inside) for an area."""

    def path_dist(X, Y):
        best = np.full(np.shape(X), 1e9)
        for pts, w, _kind in paths.values():
            best = np.minimum(best, seg_dist(X, Y, pts) / (w / 2))
        return best

    def inside(X, Y):
        return in_poly(X, Y, boundary)

    def boundary_dist(X, Y):
        X = np.asarray(X, dtype=float)
        Y = np.asarray(Y, dtype=float)
        d = seg_dist(X, Y, boundary + boundary[:1])
        return np.where(inside(X, Y), d, -d)

    return path_dist, inside, boundary_dist


def rim(boundary_dist, X, Y, lo=2.0, hi=8.0):
    """0 inside the walkable outline, rising to 1 a few metres beyond it, where the forest closes in."""
    return smoothstep(lo, hi, -boundary_dist(X, Y))


def bowl(X, Y, c, r, depth, soft=0.5):
    """A round hollow: depth metres deep over its middle, out to soft x r, its sides easing up to nothing at r."""
    return -depth * (1 - smoothstep(soft * r, r, np.hypot(X - c[0], Y - c[1])))


def polyline_frames(pts):
    """Each point's distance along a polyline and its unit tangent."""
    pts = np.asarray(pts, dtype=float)
    seg = np.diff(pts, axis=0)
    lengths = np.hypot(seg[:, 0], seg[:, 1])
    s = np.concatenate([[0.0], np.cumsum(lengths)])
    tang = np.zeros_like(pts)
    tang[1:-1] = pts[2:] - pts[:-2]
    tang[0] = pts[1] - pts[0]
    tang[-1] = pts[-1] - pts[-2]
    tang /= np.hypot(tang[:, 0], tang[:, 1])[:, None]
    return s, tang


def signed_dist(X, Y, pts):
    """For each point, its distance to a polyline, positive on the polyline's left (north of one running east), and
    how far along the polyline the nearest point lies (metres)."""
    pts = np.asarray(pts, dtype=float)
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    s, _ = polyline_frames(pts)
    best = np.full(X.shape, 1e9)
    along = np.zeros(X.shape)
    side = np.ones(X.shape)
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        dx, dy = bx - ax, by - ay
        ll = dx * dx + dy * dy
        if ll < 1e-12:
            continue
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / ll, 0.0, 1.0)
        d = np.hypot(X - (ax + t * dx), Y - (ay + t * dy))
        closer = d < best
        best = np.where(closer, d, best)
        along = np.where(closer, s[i] + t * math.sqrt(ll), along)
        side = np.where(closer, np.where(dx * (Y - ay) - dy * (X - ax) >= 0, 1.0, -1.0), side)
    return best * side, along


def point_at(pts, along):
    """The point along a polyline, and its unit tangent and left normal there."""
    pts = np.asarray(pts, dtype=float)
    s, tang = polyline_frames(pts)
    x, y = np.interp(along, s, pts[:, 0]), np.interp(along, s, pts[:, 1])
    tx, ty = np.interp(along, s, tang[:, 0]), np.interp(along, s, tang[:, 1])
    n = np.hypot(tx, ty) + 1e-12
    return (x, y), (tx / n, ty / n), (-ty / n, tx / n)


def nearest_on(X, Y, pts):
    """For each point, the distance to a polyline and how far along it the nearest point lies (metres)."""
    pts = np.asarray(pts, dtype=float)
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    s, _ = polyline_frames(pts)
    best = np.full(X.shape, 1e9)
    along = np.zeros(X.shape)
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        dx, dy = bx - ax, by - ay
        ll = dx * dx + dy * dy
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / ll, 0.0, 1.0)
        d = np.hypot(X - (ax + t * dx), Y - (ay + t * dy))
        closer = d < best
        best = np.where(closer, d, best)
        along = np.where(closer, s[i] + t * math.sqrt(ll), along)
    return best, along
