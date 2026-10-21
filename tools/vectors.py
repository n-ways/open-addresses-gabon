#!/usr/bin/env python3
"""Conformance vectors for every port of the engine: engine/reference/vectors.json.

Computed by the reference engine (engine/reference/ga_engine.py) on the frozen register
(model/areas/name-ranges.json, model/areas/register.json, engine/data/register.json); every port
(the N-Ways issuer among them) must reproduce them value for value.

  python3 tools/vectors.py
"""
import csv, glob, gzip, json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'engine', 'reference'))
import ga_engine as E  # noqa: E402

reg = json.load(open(os.path.join(REPO, 'engine', 'data', 'register.json'), encoding='utf-8'))
areas = reg['areas']
by_pc = {}
for a in areas:
    by_pc.setdefault(a['zone'], []).append(a)


def area_at(lat, lon):
    """The code area of a point (tools/assign-areas.py): nearest place of the zone, ties to the lower key."""
    c = E.zone_at(lat, lon)
    if c is None:
        return None
    cl = math.cos(math.radians(lat)) ** 2
    return min(by_pc[c['key']], key=lambda a: ((a['point'][0] - lon) ** 2 * cl + (a['point'][1] - lat) ** 2, a['key']))


def spot_case(lat, lon, fair=True):
    """A point in no outline (SPEC 5): its grid zone and spot code. With ``fair``, None when two candidate
    zones lie within 1 m of each other, or the point within 5 m of an outline or 1 m of the 20 km limit
    (the decoders' outlines are rounded to 6 decimals, the reference's to 7, so such a point is not a
    fair test; the issued compounds are all kept, checked against both)."""
    if E.zone_at(lat, lon) is not None:
        return None
    fr = E.frames()
    cands = []
    for z in E.zones():
        f = fr[z['key']]
        e, n = E._cells(lat, lon, f)
        over = max(E._beyond(e, f['dx']), E._beyond(n, f['dy']))
        if over <= E.SPOT_NEAR_CELLS:
            d = math.sqrt(E.edge_d2(lat, lon, z['polys'])) * E.M_PER_DEG_LAT
            if fair and abs(d - E.SPOT_OUTLINE_M) < 1:
                return None
            if d <= E.SPOT_OUTLINE_M:
                cands.append((over > 0, d, z['key'], over))
    cands.sort()
    if fair and (any(c[1] < 5 for c in cands) or (len(cands) > 1 and cands[0][0] == cands[1][0] and cands[1][1] - cands[0][1] < 1)):
        return None
    if not cands:
        try:
            E.spot_encode(lat, lon)
        except ValueError as e:
            return {'lat': lat, 'lon': lon, 'error': str(e)}
        raise AssertionError('a point beyond every frame must be refused')
    code = E.spot_encode(lat, lon)
    assert code.startswith('GA-' + cands[0][2] + ' ')
    return {'lat': lat, 'lon': lon, 'zone': cands[0][2], 'clamped': cands[0][0], 'code': code, 'decoded': list(E.spot_decode(code))}


def spots_outside(rnd):
    """Spot codes of points in no outline: every issued compound of the registry whose entrance lies in
    no outline, then random points in slivers, at sea, beyond the frames (the frame's nearest cell)
    and refused (more than 20 km from every outline, or 1,000 m beyond every frame)."""
    out = []
    for f in sorted(glob.glob(os.path.join(REPO, 'registry', '[0-9]*.csv.gz'))):
        with gzip.open(f, 'rt', encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                lat, lon = float(r['entrance_lat']), float(r['entrance_lng'])
                if E.zone_at(lat, lon) is None:
                    out.append(dict(spot_case(lat, lon, fair=False), machine=r['machine']))
    want = {'nearest': 150, 'clamped': 40, 'refused': 40}
    got = dict.fromkeys(want, 0)
    zs = E.zones()
    for _ in range(200000):
        if got == want:
            break
        if rnd.random() < 0.5:
            lat, lon = rnd.uniform(-4.3, 2.6), rnd.uniform(8.4, 14.8)
        else:  # just beyond a frame edge, where clamping happens
            f = E.frames()[rnd.choice(zs)['key']]
            kx = E.M_PER_DEG_LON_EQ * math.cos(math.radians(f['latc']))
            w, h = 10 ** f['dx'] * E.UNIT_M / kx, 10 ** f['dy'] * E.UNIT_M / E.M_PER_DEG_LAT
            lon = f['lon0'] + rnd.choice((-1, 1)) * rnd.uniform(0, 1500) / kx + (w if rnd.random() < 0.5 else 0)
            lat = f['lat0'] + rnd.uniform(0, h)
            if rnd.random() < 0.5:
                lat = f['lat0'] + rnd.choice((-1, 1)) * rnd.uniform(0, 1500) / E.M_PER_DEG_LAT + (h if rnd.random() < 0.5 else 0)
                lon = f['lon0'] + rnd.uniform(0, w)
        c = spot_case(lat, lon)
        if c is None:
            continue
        kind = 'refused' if 'error' in c else 'clamped' if c['clamped'] else 'nearest'
        if got[kind] < want[kind]:
            got[kind] += 1
            out.append(c)
    return out


def decode(text):
    try:
        if text.upper().startswith('GA-'):
            p = E.parse_machine(text)
            if not p['valid']:
                return {'text': text, 'error': 'invalid'}
            return {'text': text, 'machine': E.machine(p['zone'], p['index'], p['number'])}
        return {'text': text, 'machine': E.resolve_remembered(text)['code']}
    except ValueError as e:
        return {'text': text, 'error': str(e)}


def main():
    rnd = random.Random(248)
    num = [a for a in areas if a['blocks']]
    words = sorted({a['name'] for a in areas} | {a['officialName'] for a in areas})
    tricky = ['Akébé', 'Akebe', 'Nzeng-Ayong', 'Nzeng Ayong', 'Mont-Bouët', 'Mont Bouet', 'Lalala-Droite', 'Lalala Droite',
              'Glass', 'Louis', 'Owendo', 'Oloumi', 'Nkembo', 'Charbonnages', 'Batterie IV', 'Okala', 'Montagne Sainte',
              'Saint-Hilaire', 'St Hilaire', 'Mbengué', 'Mbengui', 'Moussa-Moukougou', 'Ngouéliga', "L'Église"]
    keys = [[w, E.name_key(w)] for w in tricky + rnd.sample(words, 700)]
    forms, found = [], []
    for a in rnd.sample(num, 500):
        lo, hi = a['blocks'][0]
        n = rnd.randint(lo, hi)
        m = E.machine(a['zone'], a['index'], n, a['nameId'])
        forms.append({'zone': a['key'], 'number': n, 'check': int(m[-1]), 'home': '%s %d' % (a['name'], n),
                      'written': '%s %s' % (a['name'], E.group_number(n)), 'machine': m})
        for text in ('%s %d' % (a['name'], n), '%s %s' % (a['name'], E.group_number(n)), m, '%s %s-%s' % (a['name'], E.group_number(n), m[-1])):
            found.append(decode(text))
    off = [a for a in num if E.name_key(a['officialName']) != E.name_key(a['name']) and E.name_key(a['officialName']) in reg['aliases']]
    for a in rnd.sample(off, min(150, len(off))):
        found.append(decode('%s %d' % (a['officialName'], a['blocks'][0][0] + 1)))
    for a in rnd.sample(num, 80):
        n = a['blocks'][0][0] + 3
        good = E.machine(a['zone'], a['index'], n, a['nameId'])
        found.append(decode(good[:-1] + str((int(good[-1]) + 1) % 10)))
        found.append(decode('%s %d-%d' % (a['name'], n, (int(good[-1]) + 1) % 10)))
        found.append(decode('%s %d' % (a['name'], a['blocks'][-1][1] + 1)))
    found += [decode(t) for t in ('Nulle Part 1234', 'Nowhere Town 48 217', 'Akébé 23 67 9', 'GA-9ZZ-001-2367-4')]
    spots = []
    while len(spots) < 500:
        lat, lon = rnd.uniform(1.7, 13.0), rnd.uniform(8.5, 16.1)
        a = area_at(lat, lon)
        if a is None:
            continue
        code = E.spot_encode(lat, lon)
        spots.append({'lat': lat, 'lon': lon, 'area': a['key'], 'code': code, 'decoded': list(E.spot_decode(code))})
    for box in ((9.40, 0.34, 9.52, 0.48), (8.70, -0.80, 8.86, -0.60)):   # Libreville, Port-Gentil
        for _ in range(100):
            lat, lon = rnd.uniform(box[1], box[3]), rnd.uniform(box[0], box[2])
            a = area_at(lat, lon)
            if a is None:
                continue
            code = E.spot_encode(lat, lon)
            spots.append({'lat': lat, 'lon': lon, 'area': a['key'], 'code': code, 'decoded': list(E.spot_decode(code))})
    big = max(num, key=lambda a: a['blocks'][0][1] - a['blocks'][0][0])
    x0, y0, x1, y1 = big['frame']
    comps = [{'id': 'c%02d' % k, 'lat': y0 + rnd.uniform(0, y1 - y0), 'lon': x0 + rnd.uniform(0, x1 - x0)} for k in range(41)]
    nums = E.issue_numbers({c['id']: (c['lon'], c['lat']) for c in comps}, tuple(big['frame']), tuple(big['blocks'][0]))
    issued = dict(nums)
    points = {c['id']: (c['lon'], c['lat']) for c in comps}
    inserts = []
    for i in range(60):
        lat, lon = y0 + rnd.uniform(0, y1 - y0), x0 + rnd.uniform(0, x1 - x0)
        n = E.provisional_number((lon, lat), issued, points, tuple(big['frame']), tuple(big['blocks'][0]))
        inserts.append({'lat': lat, 'lon': lon, 'number': n})
        k = 'i%02d' % i
        issued[k], points[k] = n, (lon, lat)
    hil = [[x, y, E.hilbert_index(16, x, y)] for x, y in ((0, 0), (1, 0), (65535, 65535), (12345, 54321), (40000, 2))]
    outside = spots_outside(rnd)
    out = {'note': 'Computed by engine/reference/ga_engine.py on the frozen register; every port must match.',
           'nameKeys': keys, 'forms': forms, 'found': found, 'spots': spots, 'spotsOutside': outside,
           'numbering': {'zone': big['key'], 'compounds': comps, 'numbers': nums, 'inserts': inserts},
           'hilbert': hil, 'groups': [[n, E.group_number(n)] for n in (217, 1000, 4117, 48217, 10000, 99999)]}
    json.dump(out, open(os.path.join(REPO, 'engine', 'reference', 'vectors.json'), 'w'), ensure_ascii=False, indent=0)
    print(len(keys), 'name keys,', len(forms), 'forms,', len(found), 'decodings,', len(spots), 'spots,', len(outside), 'spots outside every outline,',
          len(inserts), 'inserts')


if __name__ == '__main__':
    main()
