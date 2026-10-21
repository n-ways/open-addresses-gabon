#!/usr/bin/env python3
"""Gabon's national border: the rule that a Gabon code is only ever given to a point inside it
(engine/SPEC.md 6.1 and 6.6). Standard library only.

The border is OpenStreetMap's admin_level 2 boundary of Gabon, simplified to 50 m and shipped in
engine/data/border.json (tools/build-border.py). A code's entrance may lie at most BORDER_M = 300 m
outside the true line. The shipped line may sit up to `toleranceM` (50 m) from the true one, and
distances here are measured on a local plane (under 1 % from the ellipsoid at these lengths), so a
point is refused when it lies more than BORDER_M - toleranceM - PLANE_MARGIN_M (245 m) outside the
shipped line: nothing more than 300 m outside the true border ever passes, and nothing inside it
is ever refused.

  border = Border.load()             engine/data/border.json
  border.outside_m(lat, lng)         0 inside, else metres to the shipped line
  border.allows(lat, lng)            False when the point is in a neighbouring country

  ga_border.py check LAT LNG
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BORDER_JSON = os.path.join(REPO, 'engine', 'data', 'border.json')

BORDER_M = 300.0       # how far outside the border line an entrance may lie (the line's own accuracy, gates on it)
PLANE_MARGIN_M = 5.0   # the local plane against the ellipsoid, over a few hundred metres
M_LAT = 110574.0
M_LON_EQ = 111320.0
CELL = 0.05            # degrees: the edge index (wider than any distance asked of it)


def _seg_m(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


class Border:
    def __init__(self, rings, tolerance_m=0.0):
        """rings: [[lng, lat], ...] outlines (outer rings and holes alike, even-odd rule)."""
        self.rings = [[(float(p[0]), float(p[1])) for p in r] for r in rings]
        self.tolerance_m = float(tolerance_m)
        self.limit_m = BORDER_M - self.tolerance_m - (PLANE_MARGIN_M if self.tolerance_m else 0.0)
        self.bands, self.cells = {}, {}
        for r in self.rings:
            n = len(r)
            for i in range(n):
                a, b = r[i], r[(i + 1) % n]
                if a == b:
                    continue
                e = (a, b)
                for k in range(math.floor(min(a[1], b[1]) / CELL), math.floor(max(a[1], b[1]) / CELL) + 1):
                    self.bands.setdefault(k, []).append(e)
                    for j in range(math.floor(min(a[0], b[0]) / CELL), math.floor(max(a[0], b[0]) / CELL) + 1):
                        self.cells.setdefault((j, k), []).append(e)

    @classmethod
    def load(cls, path=BORDER_JSON):
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        return cls(d['rings'], d.get('toleranceM', 0.0))

    @classmethod
    def from_geojson(cls, path, tolerance_m=0.0):
        """Every ring of every polygon of a GeoJSON file (FeatureCollection, Feature or geometry)."""
        with open(path, encoding='utf-8') as f:
            o = json.load(f)
        geoms = [ft['geometry'] for ft in o['features']] if o.get('type') == 'FeatureCollection' else [o.get('geometry', o)]
        rings = []
        for g in geoms:
            polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates'] if g['type'] == 'MultiPolygon' else []
            for poly in polys:
                for ring in poly:
                    rings.append(ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring)
        return cls(rings, tolerance_m)

    def inside(self, lat, lng):
        ins = False
        for (xi, yi), (xj, yj) in self.bands.get(math.floor(lat / CELL), ()):
            if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                ins = not ins
        return ins

    def outside_m(self, lat, lng, cap=5000.0):
        """0 inside the border; else the distance to its line in metres (cap when farther than
        one index cell, about 5 km)."""
        if self.inside(lat, lng):
            return 0.0
        k = M_LON_EQ * math.cos(math.radians(lat))
        px, py = lng * k, lat * M_LAT
        best = cap
        cj, ck = math.floor(lng / CELL), math.floor(lat / CELL)
        seen = set()
        for j in (cj - 1, cj, cj + 1):
            for kk in (ck - 1, ck, ck + 1):
                for e in self.cells.get((j, kk), ()):
                    if id(e) in seen:
                        continue
                    seen.add(id(e))
                    (ax, ay), (bx, by) = e
                    best = min(best, _seg_m(px, py, ax * k, ay * M_LAT, bx * k, by * M_LAT))
        return best

    def allows(self, lat, lng):
        """The point may have a Gabon code: inside the border, or at most the limit outside it."""
        return self.outside_m(lat, lng) <= self.limit_m


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'check':
        b = Border.load()
        lat, lng = float(sys.argv[2]), float(sys.argv[3])
        d = b.outside_m(lat, lng)
        print(json.dumps({'outsideM': round(d, 1), 'allowed': d <= b.limit_m, 'limitM': b.limit_m}))
    else:
        sys.exit(__doc__)
