#!/usr/bin/env python3
"""Data files of the paper's figures (docs/figures/*.dat), from the published registry and model.

  python3 tools/paper-figures.py

Reads only files in this repository: registry/, model/units/zones.geojson, model/zones.json,
model/stats/building-stats.json and the reference engine. Standard library only. The figure
sources (docs/figures/*.tex) read these files; docs/paper/build.sh compiles them.

  zones-map-<c>.dat    the outlines of the 49 départements, simplified (Douglas-Peucker, 0.01°),
                       one file per density class c of their compounds (0: < 0.5 per km², ... 4: >= 50)
  zones-labels.dat     the label point and key of each département
  area-sizes.dat       areas by number of compounds (logarithmic bins), split by the digits of their name
  name-totals.dat      the empirical distribution of a name's total block size T
  mandji-blocks.dat    the blocks of the national range of Mandji: start, main part, tail reserve, numbers used
  louis-points.dat     the compounds of Louis (1LV-070) in local metres, in number order
  hilbert-order3.dat   a Hilbert curve of order 3, for the schematic panel
  spot-cells.dat       the compounds within 55 m of Louis 12 01, in spot-grid units
  sources.dat          footprints per province from OpenStreetMap and from Google / Microsoft
"""
import csv, gzip, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'docs', 'figures')
sys.path.insert(0, os.path.join(REPO, 'engine', 'reference'))
import ga_engine as G  # noqa: E402


def write(name, header, rows):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        f.write(header + '\n')
        for r in rows:
            f.write(r + '\n' if isinstance(r, str) else ' '.join(str(x) for x in r) + '\n')


def areas():
    with gzip.open(os.path.join(REPO, 'registry', 'areas.csv.gz'), 'rt', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def blocks(a):
    return [tuple(int(x) for x in b.split('-')) for b in a['blocks'].split()]


def dp(pts, tol):
    """Douglas-Peucker simplification of an open polyline."""
    if len(pts) < 3:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    den = math.hypot(dx, dy) or 1e-12
    best, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        x, y = pts[i]
        d = abs(dy * (x - x0) - dx * (y - y0)) / den if (dx or dy) else math.hypot(x - x0, y - y0)
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [pts[0], pts[-1]]
    return dp(pts[:idx + 1], tol)[:-1] + dp(pts[idx:], tol)


def zones_map():
    gj = json.load(open(os.path.join(REPO, 'model', 'units', 'zones.geojson'), encoding='utf-8'))
    meta = {z['key']: z for z in json.load(open(os.path.join(REPO, 'model', 'zones.json'), encoding='utf-8'))['zones']}
    manifest = json.load(open(os.path.join(REPO, 'registry', 'MANIFEST.json'), encoding='utf-8'))
    counts = manifest['byUnit']
    # density classes, compounds per km²: < 0.5, 0.5-1, 1-5, 5-50, >= 50
    edges = [0.5, 1, 5, 50]
    rows, labels = {c: [] for c in range(len(edges) + 1)}, []
    for f in gj['features']:
        key = f['properties']['key']
        dens = counts[key] / meta[key]['areaKm2']
        cls = sum(1 for e in edges if dens >= e)
        g = f['geometry']
        polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        big = max(polys, key=lambda p: len(p[0]))
        for p in polys:
            ring = [(round(x, 4), round(y, 4)) for x, y in p[0]]
            s = dp(ring, 0.01)
            if len(s) < 4:
                continue
            rows[cls] += [f'{x:.3f} {y:.3f}' for x, y in s] + ['nan nan']  # nan: a jump to the next outline
        xs = [x for x, _ in big[0]]
        ys = [y for _, y in big[0]]
        labels.append((key, round(sum(xs) / len(xs), 3), round(sum(ys) / len(ys), 3), cls, counts[key], round(dens, 2)))
    for c, r in rows.items():
        write(f'zones-map-{c}.dat', 'x y', r)
    write('zones-labels.dat', 'key x y c compounds density', labels)


def area_sizes(ar):
    # bins: 1, 2-3, 4-9, 10-31, 32-99, 100-316, 317-999, 1000-3162, 3163-9999, 10000+
    bounds = [1, 2, 4, 10, 32, 100, 317, 1000, 3163, 10000, 10 ** 9]
    rows = []
    for i in range(len(bounds) - 1):
        lo, hi = bounds[i], bounds[i + 1]
        c = {'3': 0, '4': 0, '5': 0}
        for a in ar:
            n = int(a['compounds'])
            if lo <= n < hi:
                c[a['digits']] += 1
        rows.append((i, lo, hi - 1, c['3'], c['4'], c['5']))
    write('area-sizes.dat', 'bin lo hi d3 d4 d5', rows)


def name_totals(ar):
    t = {}
    for a in ar:
        t[a['name_id']] = t.get(a['name_id'], 0) + sum(hi - lo + 1 for lo, hi in blocks(a))
    vals = sorted(v for v in t.values() if v > 0)
    n = len(vals)
    rows, last = [], None
    for i, v in enumerate(vals):
        if v != last or i == n - 1:
            rows.append((v, round((i + 1) / n, 5)))
        last = v
    # keep the last point of each value only
    dedup = {}
    for v, p in rows:
        dedup[v] = p
    write('name-totals.dat', 'T F', sorted(dedup.items()))


def mandji(ar):
    rows = []
    for a in ar:
        if a['name_key'] != 'MANJI':
            continue
        for lo, hi in blocks(a):
            size = hi - lo + 1
            main_hi = lo + size * 2 // 3 - 1
            n = int(a['compounds'])
            step = max(1, (main_hi - lo + 1) // max(1, int(n * 1.5)))
            used_hi = lo + (n - 1) * step  # the last number issued at first issue (SPEC 6.4)
            rows.append((a['zone'], lo, hi, main_hi, used_hi, n))
    rows.sort(key=lambda r: r[1])
    write('mandji-blocks.dat', 'area lo hi mainhi usedhi n', rows)


def louis(ar):
    a = [x for x in ar if x['zone'] == '1LV-070'][0]
    box = tuple(float(v) for v in a['frame'].split())
    lat0 = (box[1] + box[3]) / 2
    kx = 111320 * math.cos(math.radians(lat0))
    with gzip.open(os.path.join(REPO, 'registry', '1LV.csv.gz'), 'rt', encoding='utf-8') as f:
        pts = [(int(r['number']), float(r['entrance_lng']), float(r['entrance_lat']))
               for r in csv.DictReader(f) if r['zone'] == '1LV-070']
    pts.sort()
    rows = [(n, round((lon - box[0]) * kx, 1), round((lat - box[1]) * 110574, 1)) for n, lon, lat in pts]
    write('louis-points.dat', 'n x y', rows)
    w, h = (box[2] - box[0]) * kx, (box[3] - box[1]) * 110574
    write('louis-frame.dat', 'w h', [(round(w, 1), round(h, 1))])


def hilbert3():
    n = 8
    cells = sorted(((G.hilbert_index(3, x, y), x, y) for x in range(n) for y in range(n)))
    write('hilbert-order3.dat', 'd x y', [(d, x + 0.5, y + 0.5) for d, x, y in cells])


def spot():
    f = G.frames()['1LV']
    kx = G.M_PER_DEG_LON_EQ * math.cos(math.radians(f['latc']))
    lat, lon = 0.4085002, 9.4314043
    ex = (lon - f['lon0']) * kx / 10
    ny = (lat - f['lat0']) * G.M_PER_DEG_LAT / 10
    rows = []
    with gzip.open(os.path.join(REPO, 'registry', '1LV.csv.gz'), 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            x = (float(r['entrance_lng']) - f['lon0']) * kx / 10
            y = (float(r['entrance_lat']) - f['lat0']) * G.M_PER_DEG_LAT / 10
            if abs(x - ex) <= 5.5 and abs(y - ny) <= 5.5:
                rows.append((round(x, 3), round(y, 3), 1 if r['machine'] == 'GA-1LV-070-1201-1' else 0,
                             r['written'].replace(' ', '~')))
    write('spot-cells.dat', 'x y me label', rows)


def sources():
    st = json.load(open(os.path.join(REPO, 'model', 'stats', 'building-stats.json'), encoding='utf-8'))
    rows = []
    for name, v in sorted(st['regions'].items(), key=lambda kv: kv[1]['structures']):
        osm = v['fromOpenStreetMap']
        rows.append((name.replace(' ', '~'), osm, v['structures'] - osm, v['structures']))
    write('sources.dat', 'province osm ml total', rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    ar = areas()
    zones_map()
    area_sizes(ar)
    name_totals(ar)
    mandji(ar)
    louis(ar)
    hilbert3()
    spot()
    sources()


if __name__ == '__main__':
    main()
