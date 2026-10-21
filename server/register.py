"""The register in force: Gabon's code areas, their national name ranges and
blocks, and the numbering rules for new compounds.

The areas, names, aliases and zone frames come from ``engine/data/register.json``
(what every decoder ships); the blocks come from the database, because an
issuing deployment adds blocks after first issue. Parsing, check digits, spot
codes, name keys and the Hilbert curve are the reference engine's own
functions (``engine/reference/ga_engine.py``); this module only indexes the
register and applies the issue rules of engine/SPEC.md sections 6.4 and 6.5
exactly as the N-Ways issuer applies them.
"""
import json
import math
import os
import re
import sys

from . import geo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'engine', 'reference'))
import ga_engine as E  # noqa: E402
import ga_border  # noqa: E402

COUNTRY = 'GA'
COUNTRY_NAME = 'Gabon'
CREDIT = 'N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)'
CREDIT_URL = 'https://github.com/n-ways/open-addresses-gabon'
ENGINE = 'internal/addressing/ga (SPEC v1.0)'
LICENCES = {'data': 'ODbL 1.0 (LICENSE-DATA)', 'code': 'Apache-2.0 (LICENSE)', 'documents': 'CC BY 4.0 (LICENSE-DOCS)'}

# Distances of the issue rules (metres).
FOUND_M = 12.0        # "the code at this point": the nearest compound within 12 m
SPOT_M = 15.0         # a spot code names a compound when one lies within 15 m of its cell centre
EXISTS_M = 3.0        # a new code is refused when a compound already lies within 3 m
PLACE_NEAR_M = 250.0  # a new home joins the area of the nearest issued code within 250 m
DOOR_M = 80.0         # another door of a compound is at most 80 m from its entrance
MIN_AREA_M2 = 6.0     # an outline of a home is between 6 m² and 2 ha
MAX_AREA_M2 = 20000.0

REGISTER_JSON = os.path.join(ROOT, 'engine', 'data', 'register.json')
UNITS_JSON = os.path.join(ROOT, 'engine', 'data', 'units.json')


class Area:
    __slots__ = ('key', 'id', 'zone', 'index', 'plate', 'official', 'name_id', 'name_key', 'digits', 'blocks',
                 'frame', 'point', 'compounds', 'provisional', 'zone_index')

    def __init__(self, d, zone_index):
        self.key = d['key']
        self.id = d['id']
        self.zone = d['zone']
        self.index = d['index']
        self.plate = d['name']
        self.official = d['officialName']
        self.name_id = d['nameId']
        self.name_key = d['nameKey']
        self.digits = d['digits']
        self.blocks = [tuple(b) for b in d['blocks']]
        self.frame = tuple(d['frame'])
        self.point = tuple(d['point']) if d.get('point') else None  # lon, lat
        self.compounds = d['compounds']
        self.provisional = bool(d.get('provisional'))
        self.zone_index = zone_index

    def numbered(self):
        return bool(self.blocks)

    def holds(self, number):
        return any(lo <= number <= hi for lo, hi in self.blocks)

    def copy(self):
        c = object.__new__(Area)
        for k in Area.__slots__:
            setattr(c, k, getattr(self, k))
        c.blocks = list(self.blocks)
        return c


def blocks_text(blocks):
    return '|'.join(f'{lo}-{hi}' for lo, hi in blocks)


def parse_blocks(text):
    if not text:
        return []
    return [tuple(int(x) for x in b.split('-')) for b in text.split('|')]


class Register:
    """Areas, names and zones, with the blocks in force."""

    def __init__(self, blocks=None):
        with open(REGISTER_JSON, encoding='utf-8') as f:
            d = json.load(f)
        self.zones = {z['key']: z for z in d['zones']}
        self.zone_order = [z['key'] for z in d['zones']]
        self.names = {n['key']: n for n in d['names']}
        self.aliases = d['aliases']
        self.areas = [Area(a, self.zones[a['zone']]['index']) for a in d['areas']]
        self.by_key = {a.key: a for a in self.areas}
        self.by_id = {a.id: a for a in self.areas}
        if blocks:
            for k, bs in blocks.items():
                if k in self.by_key:
                    self.by_key[k].blocks = list(bs)
        self.families = {}
        self.in_zone = {}
        for a in sorted(self.areas, key=lambda a: a.key):
            self.families.setdefault(a.name_key, []).append(a)
            self.in_zone.setdefault(a.zone, []).append(a)
        with open(UNITS_JSON, encoding='utf-8') as f:
            units = json.load(f)
        self.units = []
        for key, polys in units.items():
            xs = [p[0] for poly in polys for p in poly[0]]
            ys = [p[1] for poly in polys for p in poly[0]]
            self.units.append((key, polys, (min(xs), min(ys), max(xs), max(ys))))
        self.border = ga_border.Border.load()

    # ------------------------------------------------------------ names

    def name_of(self, typed):
        """The national name record of a typed name: its plate name, else the
        official name it is an alias of (engine/SPEC.md 2.5)."""
        k = E.name_key(typed)
        if k in self.names:
            return self.names[k]
        if k in self.aliases:
            return self.names.get(self.aliases[k])
        return None

    def decode(self, typed, number):
        n = self.name_of(typed)
        if n is None or len(str(number)) != n['digits']:
            return None
        for a in self.families.get(n['key'], ()):
            if a.holds(number):
                return a
        return None

    def areas_named(self, typed):
        """Areas whose plate name or official name is the typed name (alias-aware)."""
        k = E.name_key(typed)
        keys = {k}
        if k in self.aliases:
            keys.add(self.aliases[k])
        out = [a for a in self.areas if a.name_key in keys or E.name_key(a.official) == k]
        return sorted(out, key=lambda a: a.key)

    # ------------------------------------------------------------ forms

    def forms(self, a, number):
        machine = E.machine(a.zone, a.index, number, a.name_id)
        written = E.remembered(a.plate, number)
        return {'home': f'{a.plate} {number}', 'written': written, 'spoken': f'{a.plate}, {E.group_number(number)}',
                'machine': machine, 'check': int(machine[-1])}

    # ------------------------------------------------------------ places

    def zone_at(self, lat, lng):
        """The zone (département) holding a point: even-odd rule over the outlines
        that decoders ship (engine/data/units.json), in their published order."""
        for key, polys, (x0, y0, x1, y1) in self.units:
            if x0 <= lng <= x1 and y0 <= lat <= y1 and E._inside(lng, lat, polys):
                return self.zones[key]
        return None

    def area_at(self, lat, lng):
        """The code area of a point: the nearest named place of its zone
        (cos² of the latitude on the longitude axis; ties to the lower key)."""
        z = self.zone_at(lat, lng)
        if z is None:
            return None
        best, bd = None, math.inf
        cl = math.cos(math.radians(lat)) ** 2
        for a in self.in_zone.get(z['key'], ()):
            if a.point is None:
                continue
            dx, dy = a.point[0] - lng, a.point[1] - lat
            d = dx * dx * cl + dy * dy
            if d < bd:
                best, bd = a, d
        return best

    def nearest_area(self, lat, lng):
        """The numbered area whose place point is nearest, anywhere (ties to the lower id)."""
        best, bd = None, math.inf
        for a in self.areas:
            if not a.numbered() or a.point is None:
                continue
            d = geo.plane_m(a.point[1], a.point[0], lat, lng)
            if d < bd:
                best, bd = a, d
        return best

    def spot_zone(self, lat, lng):
        """The zone of the spot grid for a point (SPEC 5): the zone whose outline holds it, else the
        zone of the nearest outline within 20 km whose frame holds it (or lies within 1,000 m); None
        outside Gabon."""
        k = E.spot_zone(lat, lng, self.units)
        return self.zones[k] if k else None

    def in_country(self, lat, lng):
        """The point is in Gabon: in a zone outline, or close enough to one to have a spot
        code (spot_zone), as the compounds in the slivers between outlines, on the shoreline
        and on islands are."""
        return self.spot_zone(lat, lng) is not None

    def within_border(self, lat, lng):
        """The point is inside Gabon's national border (OpenStreetMap admin_level 2,
        engine/data/border.json) or at most 300 m outside it. The border decides: a zone
        outline or a spot zone that spills into a neighbouring country never does."""
        return self.border.allows(lat, lng)

    def spot(self, lat, lng):
        z = self.spot_zone(lat, lng)
        if z is None:
            raise ValueError('the point is outside Gabon: in no département, and none within 20 km has a frame within 1,000 m')
        return E.spot_encode(lat, lng, z['key'])

    # ------------------------------------------------------------ numbering (SPEC 6.5)

    def next_block(self, a, compounds):
        """The next block of the area's name, from the name's spare upward and above
        every block given since; appended to ``a``. None when the range is used up."""
        nm = self.names.get(a.name_key)
        if nm is None:
            return None
        lo = nm['spareFrom']
        for x in self.families.get(a.name_key, ()):
            for b in x.blocks:
                lo = max(lo, b[1] + 1)
        for b in a.blocks:
            lo = max(lo, b[1] + 1)
        hi = lo + E.block_size(compounds) - 1
        if hi > nm['range'][1]:
            return None
        a.blocks.append((lo, hi))
        return lo, hi


def next_free(a, issued, lat, lng):
    """A new compound's number in the area's first block: the free number between
    its curve neighbours nearest their midpoint (lower first), below the tail
    reserve; else the lowest free number of the tail reserve; else of the
    area's later blocks. ``issued``: [(key, lat, lng, number)], retired codes
    included (a number is never reused). None when every block is full."""
    h = E.curve_pos(lng, lat, a.frame)
    lo, hi = a.blocks[0]
    tail = E.number_range(a.blocks[0])[1] + 1
    used = set()
    seq = []
    for key, clat, clng, n in issued:
        used.add(n)
        seq.append((E.curve_pos(clng, clat, a.frame), key, n))
    seq.sort(key=lambda s: (s[0], s[1]))
    low, high, found = lo - 1, tail, False
    for ch, _k, n in seq:
        if ch <= h:
            low = n
        elif not found:
            high, found = n, True
    if high - low > 1:
        mid = (low + high) // 2
        for d in range(high - low):
            for c in (mid - d, mid + d):
                if low < c < high and lo <= c < tail and c not in used:
                    return c
    for c in range(tail, hi + 1):
        if c not in used:
            return c
    for blo, bhi in a.blocks[1:]:
        for c in range(blo, bhi + 1):
            if c not in used:
                return c
    return None


def insert(reg, a, issued, lat, lng):
    """A new compound's number in area ``a`` (a copy: blocks it takes are appended
    to it), or None when the name's range is used up."""
    if not a.blocks:
        b = reg.next_block(a, 1)
        return b[0] if b else None
    n = next_free(a, issued, lat, lng)
    if n is not None:
        return n
    b = reg.next_block(a, len(issued) + 1)
    return b[0] if b else None


_LETTER_DIGIT = re.compile(r'(?<=[^\W\d_])(?=\d)')


def split_remembered(text):
    """Name, number and optional check digit of a remembered form typed any way
    ("Louis 12 01", "louis 1201", "LOUIS1201", "Louis · 12 01-1"), with the
    reference parser (ga_engine.REMEMBERED)."""
    t = ' '.join(text.replace('·', ' ').split())
    t = _LETTER_DIGIT.sub(' ', t)
    m = E.REMEMBERED.match(t)
    if not m:
        return None
    return m.group(1), int(m.group(2).replace(' ', '')), m.group(3)
