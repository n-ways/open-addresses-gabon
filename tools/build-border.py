#!/usr/bin/env python3
"""Gabon's national border for the issue rule: engine/data/border.json.

Reads <work>/country.geojson (tools/prepare-inputs.py: OpenStreetMap's admin_level 2 boundary of
Gabon), simplifies every ring with Douglas-Peucker at 50 m on a local plane (110,574 m per degree
of latitude, 111,320 x cos(lat) per degree of longitude at the country's mean latitude), measures
how far the simplified line strays from the true one, and writes:

  {"source": ..., "toleranceM": 50, "maxDeviationM": ..., "rings": [[[lng, lat], ...], ...]}

The guard (engine/reference/ga_border.py) refuses a point more than 300 - 50 - 5 = 245 m outside the
simplified line, so no point more than 300 m outside the true border passes. Standard library only.

  python3 tools/build-border.py <work folder>
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'engine', 'reference'))
import ga_border as B  # noqa: E402

TOL_M = 50.0
work = os.path.abspath(sys.argv[1])
src = os.path.join(work, 'country.geojson')
true = B.Border.from_geojson(src)
lat0 = sum(p[1] for r in true.rings for p in r) / sum(len(r) for r in true.rings)
K = B.M_LON_EQ * math.cos(math.radians(lat0))


def xy(p):
    return p[0] * K, p[1] * B.M_LAT


def dp(pts):
    """Douglas-Peucker on an open polyline; keeps both ends."""
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        (ax, ay), (bx, by) = xy(pts[i]), xy(pts[j])
        far, fd = None, TOL_M
        for k in range(i + 1, j):
            px, py = xy(pts[k])
            d = B._seg_m(px, py, ax, ay, bx, by)
            if d > fd:
                far, fd = k, d
        if far is not None:
            keep[far] = True
            stack += [(i, far), (far, j)]
    return [p for p, k in zip(pts, keep) if k]


rings = []
for r in true.rings:
    if len(r) < 3:
        continue
    # split the closed ring at its first point and the point farthest from it
    x0, y0 = xy(r[0])
    m = max(range(len(r)), key=lambda k: math.hypot(xy(r[k])[0] - x0, xy(r[k])[1] - y0))
    s = dp(r[:m + 1])[:-1] + dp(r[m:] + [r[0]])[:-1]
    if len(s) < 3:
        s = r  # a ring smaller than the tolerance stays whole
    rings.append([[round(p[0], 6), round(p[1], 6)] for p in s])

# how far the simplified line strays from the true one (every true vertex to the simplified line)
simple = B.Border(rings)
dev = 0.0
for r in true.rings:
    for p in r:
        k = B.M_LON_EQ * math.cos(math.radians(p[1]))
        best = math.inf
        cj, ck = math.floor(p[0] / B.CELL), math.floor(p[1] / B.CELL)
        for j in (cj - 1, cj, cj + 1):
            for kk in (ck - 1, ck, ck + 1):
                for (ax, ay), (bx, by) in simple.cells.get((j, kk), ()):
                    best = min(best, B._seg_m(p[0] * k, p[1] * B.M_LAT, ax * k, ay * B.M_LAT, bx * k, by * B.M_LAT))
        dev = max(dev, best)
if dev > TOL_M + 1:
    sys.exit(f'the simplified border strays {dev:.1f} m from the true one, over {TOL_M:.0f} m')
out = {'source': 'OpenStreetMap admin_level 2 boundary of Gabon (ODbL), Douglas-Peucker at 50 m',
       'borderM': B.BORDER_M, 'toleranceM': TOL_M, 'maxDeviationM': round(dev, 1), 'rings': rings}
path = os.path.join(REPO, 'engine', 'data', 'border.json')
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, separators=(',', ':'))
print(sum(len(r) for r in true.rings), 'vertices ->', sum(len(r) for r in rings), 'in', len(rings), 'rings;',
      f'max deviation {dev:.1f} m;', os.path.getsize(path), 'bytes')
