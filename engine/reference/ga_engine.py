#!/usr/bin/env python3
"""N-Ways address engine for Gabon: reference implementation (standard library only).

This file is the executable form of engine/SPEC.md. It is not a shared library: it exists
for Gabon only.

What it does
  * remembered form "Akébé 23 67": the area's plate name and a number of 3 to 5 digits, unique in
                   the whole country on its own (one national number range per plate name, a frozen
                   block per area, so the number says which Akébé). The plate name has at most
                   12 characters and 2 words and no digit (plate_names.py); the official name is printed small and, typed, still decodes when it maps
                   to one plate name
  * machine form   GA-<zone>-<area index>-<number>-<Damm check digit>, for systems only:
                   GA-1LV-021-2367-4. Zones are the 49 départements, keyed by their
                   province digit (La Poste's "01 LIBREVILLE") and two letters (model/zones.json)
  * spot code      GA-<zone> E<east> N<north>: metres east/north of the zone frame origin in
                   10 m units (4 digits per axis, 5 where the zone is wider than 99.99 km)
  * zone lookup    point in polygon over model/units/zones.geojson; for its spot code, a point in
                   no outline takes the zone of the nearest outline within 20 km whose frame holds it
  * registry       groups footprints into compounds (concessions), orders compounds along a
                   Hilbert curve and issues numbers with infill gaps and a tail reserve;
                   provisional numbers for new homes ("Ajouter ma maison" / "Add my home")

Command line
  ga_engine.py spot LAT LON            spot code + zone for a point
  ga_engine.py unspot "GA-1LV E1234 N5678"
  ga_engine.py check GA-1LV-021-2367  -> full machine code with its check digit
  ga_engine.py verify GA-1LV-021-2367-4
  ga_engine.py resolve Akébé 23 67    remembered form -> machine form, no context needed
  ga_engine.py frames                  (re)build model/units/frames.json (frozen once published)
"""
import json, math, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plate_names  # noqa: E402  (the plate-name rule: at most 12 characters, 2 words)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
UNITS = os.path.join(REPO, 'model', 'units')

# ---------------------------------------------------------------------------
# Damm check digit (H. M. Damm, 2004): a weakly totally anti-symmetric quasigroup of
# order 10. Detects every single-digit error and every adjacent transposition.
DAMM = [
    [0, 3, 1, 7, 5, 9, 8, 6, 4, 2],
    [7, 0, 9, 2, 1, 5, 4, 8, 6, 3],
    [4, 2, 0, 6, 8, 7, 1, 3, 5, 9],
    [1, 7, 5, 0, 9, 8, 3, 4, 2, 6],
    [6, 1, 2, 3, 0, 4, 5, 9, 7, 8],
    [3, 6, 7, 4, 2, 0, 9, 5, 8, 1],
    [5, 8, 6, 9, 7, 2, 0, 1, 3, 4],
    [8, 9, 4, 5, 3, 6, 2, 0, 1, 7],
    [9, 4, 3, 8, 6, 1, 7, 2, 0, 5],
    [2, 5, 8, 1, 4, 3, 6, 7, 9, 0],
]


def damm(digits):
    i = 0
    for d in digits:
        i = DAMM[i][int(d)]
    return i


# ---------------------------------------------------------------------------
# National names: "Akébé 2367" names one place in the whole country on
# its own. Every area with the same normalised plate name draws from one national range for that
# name, cut into frozen blocks, one per area (SPEC 2.4).

NAME_SPARE = 0.1  # top tenth of every name's range: blocks for areas that will carry the name later


plain = plate_names.plain


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).upper()


GENERIC_RE = re.compile(r"^\s*(village|quarter|campe?m\w*|camp\b|site\b|hameau\s*$|ferme\b|farm\b|chantier\b|zone\b)\s*$", re.I)


def is_generic(name):
    """Labels that are not place names ("village", "Campement", "Farm"): their homes take the nearest
    real name; they never get a block."""
    return bool(GENERIC_RE.match(name))


def name_key(name):
    """Normalised name for Gabon (French spellings of Fang, Punu, Myene, Nzebi, Téké
    and other names): accents and case folded; St/Ste expanded; a leading Q/Quartier/Quarter/Village
    (de)/Hameau and the articles le/la/les/l'/the dropped; everything but A-Z and 0-9 dropped; the
    French/English spelling pairs folded: tch=ch=c, dj=j, gh=g, ph=f, ou=w=u, ck=k, gu before i/e = g;
    doubled letters single (digits never). So Nzeng-Ayong = Nzeng Ayong, Owendo = Ouendo,
    Djoutsi = Joutsi, Tchibanga = Chibanga."""
    s = _fold(name)
    s = re.sub(r"(?<![A-Z])STE(?![A-Z])\.?", 'SAINTE', s)
    s = re.sub(r"(?<![A-Z])ST(?![A-Z])\.?", 'SAINT', s)
    s = re.sub(r"^(Q|QUARTIER|QUARTER|HAMEAU|VILLAGE DE|VILLAGE)[\s\-.]+", '', s)
    s = re.sub(r"^(LES|LE|LA|THE)\s+|^L'", '', s)
    s = re.sub(r"[^A-Z0-9]", '', s)
    for a, b in (('TCH', 'C'), ('CH', 'C'), ('DJ', 'J'), ('GH', 'G'), ('PH', 'F'), ('CK', 'K'),
                 ('OU', 'U'), ('W', 'U')):
        s = s.replace(a, b)
    s = re.sub(r'GU(?=[IE])', 'G', s)
    return re.sub(r'([A-Z])\1+', r'\1', s)  # doubled letters single; digits stay


def floors_from_height(h):
    """Floors from an OpenStreetMap height (m): h / 3, rounded, at least 1. The Google/Microsoft
    height is a rendering filler and never gives floors (SPEC 8.1)."""
    return max(1, int(round(h / 3.0)))


def block_size(compounds):
    """Block of one area in its name's range: twice today's compounds (room to grow), rounded up
    to a multiple of 10, at least 20."""
    return max(20, -(-2 * int(compounds) // 10) * 10)


# ---------------------------------------------------------------------------
# Zones (the 49 départements) and their frames

def _rings(geom):
    if geom['type'] == 'Polygon':
        return [geom['coordinates']]
    return geom['coordinates']


def _inside(x, y, polys):
    for poly in polys:
        ins = False
        for ring in poly:
            j = len(ring) - 1
            for i in range(len(ring)):
                xi, yi = ring[i][0], ring[i][1]
                xj, yj = ring[j][0], ring[j][1]
                if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    ins = not ins
                j = i
        if ins:
            return True
    return False


_ZONES = None


def _load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def zones():
    """[{key, index, name, region, language, polys, box}] in the order of model/units/zones.geojson."""
    global _ZONES
    if _ZONES is None:
        meta = {z['key']: z for z in _load(os.path.join(REPO, 'model', 'zones.json'))['zones']}
        g = _load(os.path.join(UNITS, 'zones.geojson'))
        out = []
        for f in g['features']:
            polys = _rings(f['geometry'])
            xs = [p[0] for poly in polys for p in poly[0]]
            ys = [p[1] for poly in polys for p in poly[0]]
            m = meta[f['properties']['key']]
            out.append({'key': m['key'], 'index': m['index'], 'name': m['name'], 'nameEn': m.get('nameEn'),
                        'region': m['region'], 'language': m['language'], 'polys': polys,
                        'box': (min(xs), min(ys), max(xs), max(ys))})
        _ZONES = out
    return _ZONES


def zone(key):
    for z in zones():
        if z['key'] == key:
            return z
    raise ValueError(f'unknown zone {key!r}')


def zone_at(lat, lon):
    for z in zones():
        x0, y0, x1, y1 = z['box']
        if x0 <= lon <= x1 and y0 <= lat <= y1 and _inside(lon, lat, z['polys']):
            return z
    return None


def plate_lang(zone_key):
    """Plate rules: French in every zone of Gabon."""
    return zone(zone_key)['language'] if zone_key else 'fr'


def plate_ok(name, lang='fr'):
    """A plate name: at most 12 characters (an accented letter, a hyphen or an apostrophe count one)
    and 2 words (linking words do not count), no digit."""
    return plate_names.fits(name, lang)


M_PER_DEG_LAT = 110574.0
M_PER_DEG_LON_EQ = 111320.0
UNIT_M = 10.0


def frame_for_box(box):
    """Frame of a zone: origin = box SW corner floored to 0.01 degree; reference latitude = box centre
    rounded to 0.01 degree; digits per axis = 4 if the frame spans <= 99,990 m, else 5."""
    x0, y0, x1, y1 = box
    lon0 = math.floor(x0 * 100) / 100
    lat0 = math.floor(y0 * 100) / 100
    latc = round((y0 + y1) / 2, 2)
    kx = M_PER_DEG_LON_EQ * math.cos(math.radians(latc))
    w = (x1 - lon0) * kx
    h = (y1 - lat0) * M_PER_DEG_LAT
    return {'lon0': lon0, 'lat0': lat0, 'latc': latc,
            'dx': 4 if w < 99990 else 5, 'dy': 4 if h < 99990 else 5}


_FRAMES = None


def frames():
    global _FRAMES
    if _FRAMES is None:
        p = os.path.join(UNITS, 'frames.json')
        _FRAMES = _load(p) if os.path.exists(p) else {}
    return _FRAMES


def build_frames():
    out = {}
    for z in zones():
        f = frame_for_box(z['box'])
        f['zone'] = z['name']
        out[z['key']] = f
    with open(os.path.join(UNITS, 'frames.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(out.items())), f, ensure_ascii=False, indent=1)
    return out


SPOT_NEAR_CELLS = 100   # a point at most 1,000 m beyond a frame takes the frame's nearest cell
SPOT_OUTLINE_M = 20000.0  # a point in no outline is in Gabon when an outline lies within 20 km


def _cells(lat, lon, f):
    """Cell (E, N) of a point in a frame; either may fall outside the frame."""
    kx = M_PER_DEG_LON_EQ * math.cos(math.radians(f['latc']))
    return (int(math.floor((lon - f['lon0']) * kx / UNIT_M)),
            int(math.floor((lat - f['lat0']) * M_PER_DEG_LAT / UNIT_M)))


def _beyond(v, digits):
    """Cells by which an index lies outside 0 .. 10^digits - 1 (0 inside)."""
    return -v if v < 0 else max(0, v - (10 ** digits - 1))


def edge_d2(lat, lon, polys):
    """Squared distance from a point to the nearest edge of any ring of an outline, in degrees
    of latitude, with longitude differences scaled by cos(latitude of the point)."""
    c = math.cos(math.radians(lat))
    best = math.inf
    for poly in polys:
        for ring in poly:
            j = len(ring) - 1
            for i in range(len(ring)):
                ax, ay = (ring[j][0] - lon) * c, ring[j][1] - lat
                vx, vy = (ring[i][0] - lon) * c - ax, (ring[i][1] - lat) - ay
                ll = vx * vx + vy * vy
                t = 0.0
                if ll > 0:
                    t = min(1.0, max(0.0, -(ax * vx + ay * vy) / ll))
                px, py = ax + t * vx, ay + t * vy
                d = px * px + py * py
                if d < best:
                    best = d
                j = i
    return best


def spot_zone(lat, lon, outlines=None):
    """Zone key of the spot grid for a point (SPEC 5): the zone whose outline holds it; else,
    among the zones whose outline lies within 20 km and whose frame holds the point, the one
    with the nearest outline; else, among those whose outline lies within 20 km and whose
    frame lies at most 1,000 m away on each axis, the one with the nearest outline (the point
    then takes that frame's nearest cell); ties to the lower key. None: refused.
    ``outlines`` is [(key, polygons, box)] in lookup order (default: zones())."""
    if outlines is None:
        outlines = [(z['key'], z['polys'], z['box']) for z in zones()]
    for key, polys, (x0, y0, x1, y1) in outlines:
        if x0 <= lon <= x1 and y0 <= lat <= y1 and _inside(lon, lat, polys):
            return key
    fr = frames()
    lim = SPOT_OUTLINE_M / M_PER_DEG_LAT
    lim = lim * lim
    best = None
    for key, polys, _box in outlines:
        f = fr[key]
        e, n = _cells(lat, lon, f)
        over = max(_beyond(e, f['dx']), _beyond(n, f['dy']))
        if over > SPOT_NEAR_CELLS:
            continue
        d = edge_d2(lat, lon, polys)
        if d > lim:
            continue
        k = (over > 0, d, key)
        if best is None or k < best:
            best = k
    return best[2] if best else None


def spot_encode(lat, lon, zkey=None):
    """Spot code of a point; zkey: its zone for the grid (default: spot_zone)."""
    if zkey is None:
        zkey = spot_zone(lat, lon)
        if zkey is None:
            raise ValueError('point is outside Gabon: in no zone, and no zone within 20 km has a frame within 1,000 m')
    f = frames()[zkey]
    e, n = _cells(lat, lon, f)
    if max(_beyond(e, f['dx']), _beyond(n, f['dy'])) > SPOT_NEAR_CELLS:
        raise ValueError('point is more than 1,000 m beyond the zone frame')
    e = min(max(e, 0), 10 ** f['dx'] - 1)
    n = min(max(n, 0), 10 ** f['dy'] - 1)
    return f'GA-{zkey} E{e:0{f["dx"]}d} N{n:0{f["dy"]}d}'


SPOT_RE = re.compile(r'^GA-?([1-9][A-Z]{2})\s*E(\d{4,5})\s*N(\d{4,5})$')


def spot_decode(code):
    m = SPOT_RE.match(code.strip().upper())
    if not m:
        raise ValueError(f'not a Gabon spot code: {code!r}')
    zkey, e, n = m.group(1), m.group(2), m.group(3)
    if zkey not in frames():
        raise ValueError(f'unknown zone {zkey}')
    f = frames()[zkey]
    if len(e) != f['dx'] or len(n) != f['dy']:
        raise ValueError('wrong number of digits for this zone frame')
    kx = M_PER_DEG_LON_EQ * math.cos(math.radians(f['latc']))
    lon = f['lon0'] + (int(e) + 0.5) * UNIT_M / kx
    lat = f['lat0'] + (int(n) + 0.5) * UNIT_M / M_PER_DEG_LAT
    return round(lat, 7), round(lon, 7)


# ---------------------------------------------------------------------------
# Names, machine form, decoding

_NAMES = None


def names():
    """model/areas/name-ranges.json, indexed: plate key -> entry, (zone, index) -> [(key, lo, hi)],
    and official-name key -> plate key (aliases that map to one plate name only)."""
    global _NAMES
    if _NAMES is None:
        d = _load(os.path.join(REPO, 'model', 'areas', 'name-ranges.json'))
        by_area = {}
        for k, v in d['names'].items():
            for zk, ix, _c, lo, hi in v['blocks']:
                by_area.setdefault((zk, ix), []).append((k, lo, hi))
            for zk, ix in v['areasWithoutCompounds']:
                by_area.setdefault((zk, ix), []).append((k, None, None))
        _NAMES = {'names': d['names'], 'byArea': by_area, 'aliases': d.get('aliasKeys', {})}
    return _NAMES


_PLATES = None


def area_plates():
    """(zone, index) -> the area's plate name, from engine/data/register.json."""
    global _PLATES
    if _PLATES is None:
        reg = _load(os.path.join(REPO, 'engine', 'data', 'register.json'))
        _PLATES = {(a['zone'], a['index']): a['name'] for a in reg['areas']}
    return _PLATES


def name_id(zkey, index):
    hits = names()['byArea'].get((zkey, str(index)))
    if not hits:
        raise ValueError(f'no area {index} in zone {zkey}')
    return names()['names'][hits[0][0]]['id']


def check_input(zkey, index, number, nid=None):
    """Digits under the Damm check: the frozen national name id (5 digits) + the zone's frozen index
    (3 digits) + the area index (3 digits) + the number, so the check binds name, zone, area and number."""
    if nid is None:
        nid = name_id(zkey, index)
    return f'{int(nid):05d}{int(zone(zkey)["index"]):03d}{index}{number}'


def machine(zkey, index, number, nid=None):
    """GA-1LV-021-2367-c."""
    zkey, index, number = str(zkey), str(index), str(number)
    if not re.fullmatch(r'[1-9][A-Z]{2}', zkey):
        raise ValueError('zone is a province digit and two letters')
    if not re.fullmatch(r'\d{3}', index):
        raise ValueError('area index is 3 digits')
    if not re.fullmatch(r'[1-9]\d{2,4}', number):
        raise ValueError('number is 3-5 digits without a leading zero')
    return f'GA-{zkey}-{index}-{number}-{damm(check_input(zkey, index, number, nid))}'


MACHINE_RE = re.compile(r'^GA-([1-9][A-Z]{2})-(\d{3})-([1-9]\d{2,4})(?:-(\d))?$')


def parse_machine(code, nid=None):
    m = MACHINE_RE.match(code.strip().upper().replace(' ', ''))
    if not m:
        raise ValueError(f'not a Gabon N-Ways code: {code!r}')
    zkey, index, number, c = m.groups()
    ok = c is None or damm(check_input(zkey, index, number, nid)) == int(c)
    hits = names()['byArea'].get((zkey, index), [])
    in_area = any(lo is not None and lo <= int(number) <= hi for _k, lo, hi in hits)
    return {'zone': zkey, 'index': index, 'number': number, 'check': int(c) if c is not None else None,
            'valid': ok and in_area, 'inArea': in_area}


def block_of(key, number):
    """The area (zone, index) whose block holds this number in the name's range, or None."""
    n = int(number)
    for zk, ix, _c, lo, hi in names()['names'][key]['blocks']:
        if lo <= n <= hi:
            return zk, ix
    return None


CHECK_TAIL = r'(?:\s*-\s*(\d))?'  # a check digit a system may send after the number: "Akébé 23 67-4"
REMEMBERED = re.compile(r'^\s*(.+?)\s+([1-9][\d ]{2,6}?)' + CHECK_TAIL + r'\s*$')


def resolve_remembered(text):
    """Remembered form -> machine form, with no context: no position, no zone asked ("Akébé 23 67":
    the number says which Akébé). Returns the machine code and the area, or raises ValueError."""
    t = text.replace('·', ' ').strip()
    m = REMEMBERED.match(t)
    if not m:
        raise ValueError(f'not a remembered Gabon address: {text!r}')
    key, num = name_key(m.group(1)), m.group(2).replace(' ', '')
    via = None
    if key not in names()['names'] and key in names()['aliases']:
        via, key = m.group(1), names()['aliases'][key]  # the official name typed: decodes to its plate name
    entry = names()['names'].get(key)
    if entry is None:
        raise ValueError(f'unknown place name {m.group(1)!r}')
    if len(num) != entry['digits']:
        raise ValueError(f'{m.group(1).strip()} numbers have {entry["digits"]} digits')  # the name typed
    hit = block_of(key, num)
    if hit is None:
        raise ValueError(f'{m.group(1).strip()} {num} is not issued (spare or free space)')
    zk, ix = hit
    res = {'code': machine(zk, ix, num, entry['id']), 'zone': zk, 'index': ix, 'number': num,
           # the area's own plate (Njinga II), not its range's first name (Njinga I): names that fold to one
           # key share a range, each area keeping its own plate
           'area': area_plates().get((zk, ix), entry['plateName']), 'nameId': entry['id']}
    if via:
        res['typedOfficialName'] = via
    c = m.group(3)
    if c is not None and int(c) != int(res['code'][-1]):
        raise ValueError(f'check digit {c} does not match: mistyped name or number')
    res['checked'] = c is not None
    return res


def group_number(number):
    """How the number is written and said: 3 digits '217', 4 digits '23 67', 5 digits '48 217'."""
    n = str(number)
    if len(n) >= 4:
        return f'{n[:2]} {n[2:]}'
    return n


def remembered(area_name, number):
    """The form people remember: no letters to learn, no check digit, unique in the whole country."""
    return f'{area_name} {group_number(number)}'


# ---------------------------------------------------------------------------
# Registry: compounds and numbers (SPEC 6)

CITY = {'annex_m2': 25.0, 'attach_m': 8.0, 'hut_m2': 0.0}
RURAL = {'annex_m2': 25.0, 'attach_m': 8.0, 'hut_m2': 40.0, 'hut_gap_m': 3.0, 'hut_max': 25}


def grouping_params(zkey):
    """Grouping parameters of a zone: no hut clusters in Libreville (1LV) and Port-Gentil's département (8PG)."""
    return CITY if str(zkey) in ('1LV', '8PG') else RURAL


def _metres(lat0):
    p = math.radians(lat0)
    return 111132.92 - 559.82 * math.cos(2 * p) + 1.175 * math.cos(4 * p), 111412.84 * math.cos(p) - 93.5 * math.cos(3 * p)


def _plane(poly, lat0, lon0):
    m_lat, m_lon = _metres(lat0)
    return [((x - lon0) * m_lon, (y - lat0) * m_lat) for x, y in poly]


def _in_ring_xy(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _seg_dist_xy(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _gap_plane(pa, pb):
    """Smallest distance in metres between two closed outlines in local metres (0 if they touch or overlap)."""
    if any(_in_ring_xy(x, y, pb) for x, y in pa) or any(_in_ring_xy(x, y, pa) for x, y in pb):
        return 0.0
    d = min(_seg_dist_xy(q, pb[i], pb[i + 1]) for q in pa for i in range(len(pb) - 1))
    return min(d, min(_seg_dist_xy(q, pa[i], pa[i + 1]) for q in pb for i in range(len(pa) - 1)))


def group_footprints(fs, params=RURAL):
    """Grouping of one code area.

    fs: dicts with id (stable structure id), ring ([lon, lat] closed), area (m2), eid (the smallest
    closed enclosure of at most 6,000 m2 holding the centre, or None). Footprints are taken in id order,
    neighbours found on a 40 m grid, so the result never depends on the data's order. Rules, in order:
      enclosure    every footprint inside one enclosure is one compound;
      annex        a footprint under annex_m2 joins the nearest footprint of at least annex_m2 within
                   attach_m, outline to outline (only annexes join, and only to a building);
      hut-cluster  (outside Libreville and Port-Gentil) huts under hut_m2 that belong to no house chain within
                   hut_gap_m, at most hut_max per compound: a cluster never joins two houses;
      single       everything else.
    Returns [(member indexes largest first, rule)] sorted by the main footprint's id."""
    if not fs:
        return []
    lat0 = sum(f['ring'][0][1] for f in fs) / len(fs)
    lon0 = sum(f['ring'][0][0] for f in fs) / len(fs)
    order = sorted(range(len(fs)), key=lambda i: fs[i]['id'])
    pts = [_plane(f['ring'], lat0, lon0) for f in fs]
    cent = [(sum(p[0] for p in q[:-1]) / max(1, len(q) - 1), sum(p[1] for p in q[:-1]) / max(1, len(q) - 1)) for q in pts]
    parent = list(range(len(fs)))
    rule = ['single'] * len(fs)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    first_in = {}
    for i in order:
        e = fs[i].get('eid')
        if e:
            r = first_in.setdefault(e, i)
            parent[find(i)] = find(r)
            rule[i] = 'enclosure'
    CELL = 40.0
    grid = {}
    for i in order:
        grid.setdefault((int(cent[i][0] // CELL), int(cent[i][1] // CELL)), []).append(i)

    def around(i, reach):
        cx, cy = int(cent[i][0] // CELL), int(cent[i][1] // CELL)
        k = int(reach // CELL) + 2
        for dx in range(-k, k + 1):
            for dy in range(-k, k + 1):
                for j in grid.get((cx + dx, cy + dy), ()):
                    if j != i and math.dist(cent[i], cent[j]) <= 60:
                        yield j
    for i in order:
        if rule[i] != 'single' or fs[i]['area'] >= params['annex_m2']:
            continue
        best = None
        for j in around(i, params['attach_m']):
            if fs[j]['area'] < params['annex_m2']:
                continue
            g = _gap_plane(pts[i], pts[j])
            if g <= params['attach_m'] and (best is None or (g, fs[j]['id']) < (best[0], fs[best[1]]['id'])):
                best = (g, j)
        if best:
            parent[find(i)] = find(best[1])
            rule[i] = 'annex'
            if rule[best[1]] == 'single':
                rule[best[1]] = 'annex'
    if params.get('hut_m2'):
        size = {}
        for i in range(len(fs)):
            size[find(i)] = size.get(find(i), 0) + 1
        for i in order:
            if fs[i]['area'] >= params['hut_m2'] or rule[i] not in ('single', 'hut-cluster'):
                continue
            for j in sorted(around(i, params['hut_gap_m']), key=lambda j: fs[j]['id']):
                if fs[j]['area'] >= params['hut_m2'] or rule[j] not in ('single', 'hut-cluster'):
                    continue
                if _gap_plane(pts[i], pts[j]) > params['hut_gap_m']:
                    continue
                ri, rj = find(i), find(j)
                if ri != rj and size[ri] + size[rj] <= params['hut_max']:
                    parent[rj] = ri
                    size[ri] += size[rj]
                    rule[i] = rule[j] = 'hut-cluster'
    groups = {}
    for i in order:
        groups.setdefault(find(i), []).append(i)
    conf = {'enclosure': 0.85, 'annex': 0.6, 'hut-cluster': 0.5, 'single': 0.4}
    out = []
    for ms in groups.values():
        ms.sort(key=lambda i: (-fs[i]['area'], fs[i]['id']))
        out.append((ms, max((rule[m] for m in ms), key=lambda x: conf[x])))
    return sorted(out, key=lambda g: fs[g[0][0]]['id'])


def hilbert_index(order, x, y):
    """Distance along a Hilbert curve of side 2**order for integer cell (x, y)."""
    n = 1 << order
    d = 0
    s = n >> 1
    while s > 0:
        rx = 1 if (x & s) else 0
        ry = 1 if (y & s) else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x, y = n - 1 - x, n - 1 - y
            x, y = y, x
        s >>= 1
    return d


ORDER = 16


def curve_pos(lon, lat, box):
    x0, y0, x1, y1 = box
    n = (1 << ORDER) - 1
    gx = min(n, max(0, int((lon - x0) / (x1 - x0) * n)))
    gy = min(n, max(0, int((lat - y0) / (y1 - y0) * n)))
    return hilbert_index(ORDER, gx, gy)


def number_range(block):
    """(lo, main_hi, hi) of an area's block: the top third is the tail reserve."""
    lo, hi = block
    size = hi - lo + 1
    return lo, lo + (size * 2) // 3 - 1, hi


def issue_numbers(points, box, block):
    """points: {compound_key: (lon, lat)}. Returns {key: number} in Hilbert order with infill gaps,
    in the area's frozen block (lo, hi) of its name's national range (SPEC 2.4)."""
    keys = sorted(points, key=lambda k: (curve_pos(points[k][0], points[k][1], box), k))
    n = len(keys)
    if n * 2 > block[1] - block[0] + 1:
        raise ValueError('capacity rule broken: compounds x 2 exceed the block')
    lo, main_hi, hi = number_range(block)
    step = max(1, (main_hi - lo + 1) // max(1, int(n * 1.5)))
    out = {k: lo + i * step for i, k in enumerate(keys)}
    assert not out or max(out.values()) <= main_hi
    return out


def provisional_number(point, issued, points, box, block):
    """Number for a new compound: a free number between its Hilbert neighbours, nearest the
    midpoint m = floor((a + b) / 2) of the neighbours' numbers a and b, m itself first, then m - 1,
    m + 1, m - 2...; otherwise the lowest free number of the tail reserve. Never reuses a number."""
    lo, main_hi, hi = number_range(block)
    used = set(issued.values())
    p = curve_pos(point[0], point[1], box)
    prev = nxt = None
    for k in sorted(issued, key=lambda k: (curve_pos(points[k][0], points[k][1], box), k)):
        if curve_pos(points[k][0], points[k][1], box) <= p:
            prev = issued[k]
        elif nxt is None:
            nxt = issued[k]
    a = prev if prev is not None else lo - 1
    b = nxt if nxt is not None else main_hi + 1
    free = [x for x in range(a + 1, b) if x not in used and lo <= x <= main_hi]
    if free:
        mid = (a + b) // 2
        return min(free, key=lambda x: (abs(x - mid), x > mid))
    for x in range(main_hi + 1, hi + 1):
        if x not in used:
            return x
    raise ValueError('area full: extension block from the name spare')


def spare_block(entry, compounds, taken=()):
    """Next block for a new area (or an extension of a full one) with an existing name: from the
    name's spare space upward from entry['spareFrom']; existing blocks are never renumbered."""
    lo = max([entry['spareFrom']] + [b[1] + 1 for b in taken])
    hi = lo + block_size(compounds) - 1
    return (lo, hi) if hi <= entry['range'][1] else None


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == 'spot':
        lat, lon = float(argv[2]), float(argv[3])
        zk = spot_zone(lat, lon)
        z = zone(zk) if zk else None
        print(json.dumps({'spot': spot_encode(lat, lon), 'zone': zk,
                          'name': z['name'] if z else None}, ensure_ascii=False))
    elif cmd == 'unspot':
        print(spot_decode(' '.join(argv[2:])))
    elif cmd == 'check':
        m = re.match(r'^GA-([1-9][A-Z]{2})-(\d{3})-(\d{3,5})$', argv[2].upper())
        print(machine(*m.groups()))
    elif cmd == 'resolve':
        print(json.dumps(resolve_remembered(' '.join(argv[2:])), ensure_ascii=False))
    elif cmd == 'verify':
        print(json.dumps(parse_machine(argv[2])))
    elif cmd == 'frames':
        print(len(build_frames()), 'frames written')
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
