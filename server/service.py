"""What the API does: cards, look-ups, verification and issue.

Issue follows the N-Ways issuer rule for rule (engine/SPEC.md 6.5 and 7):
the "already has a code" checks, the outline limits, the area a new home
takes, the numbering with its tail reserve and extension blocks, the forms,
``status: provisional`` and ``issued: on-demand``, and a daily limit per key.
"""
import datetime as dt
import hashlib
import hmac
import json
import threading

from . import geo
from . import register as R
from . import store as S
from .register import E


class ApiError(Exception):
    def __init__(self, status, code, message, **extra):
        super().__init__(message)
        self.status, self.code, self.message, self.extra = status, code, message, extra


def _bool(text):
    return text == 'true'



class Service:
    def __init__(self, store, issue_keys=(), per_day=5):
        self.st = store
        self.issue_keys = {k.strip() for k in issue_keys if k.strip()}
        self.per_day = per_day
        self.lock = threading.Lock()
        self.reg = R.Register(store.blocks())

    # ------------------------------------------------------------ cards

    def zone_info(self, key):
        z = self.reg.zones[key]
        return {'key': z['key'], 'name': z['name'], 'region': z['region'], 'index': z['index']}

    def area_brief(self, a):
        return {'key': a.key, 'id': a.id, 'plateName': a.plate, 'officialName': a.official, 'provisionalName': a.provisional,
                'zone': a.zone, 'zoneName': self.reg.zones[a.zone]['name']}

    def card(self, row):
        if 'class' not in row.keys():
            row = self.st.code(row['machine'])
        a = self.reg.by_key[row['zone']]
        f = self.reg.forms(a, row['num'])
        record = {c: row[c] for c in S.CODE_COLS}
        lat, lng = float(row['entrance_lat']), float(row['entrance_lng'])
        return {
            'country': R.COUNTRY,
            'machine': row['machine'],
            'home': row['home'],
            'written': row['written'],
            'spoken': f['spoken'],
            'number': row['num'],
            'check': int(row['check']),
            'status': row['status'],
            'issued': row['issued'],
            'issuedAt': row['issued_at'],
            'area': self.area_brief(a),
            'zone': self.zone_info(a.zone),
            'officialAddress': row['official_address'] or None,
            'entrance': {'lat': lat, 'lng': lng, 'kind': row['entrance_kind']},
            'spotCode': row['spot_code'],
            'plusCode': geo.plus_code(lat, lng),
            'profile': {'class': row['class'], 'use': row['use'], 'kind': row['kind'],
                        'structures': int(row['structures'] or 0), 'floorAreaM2': float(row['floor_area_m2'] or 0),
                        'rule': row['rule'] or None, 'estate': row['estate'] or None},
            'record': record,
            'credit': R.CREDIT,
        }

    def brief(self, row, distance=None):
        out = {'machine': row['machine'], 'home': row['home'], 'written': row['written'], 'status': row['status'],
               'area': row['zone'], 'entrance': {'lat': float(row['entrance_lat']), 'lng': float(row['entrance_lng'])}}
        if row['official_address']:
            out['officialAddress'] = row['official_address']
        if distance is not None:
            out['distanceM'] = round(distance, 1)
        return out

    # ------------------------------------------------------------ read

    def health(self):
        m = self.st.meta()
        n = self.st.con().execute('SELECT count(*) FROM codes').fetchone()[0]
        return {'status': 'ok', 'country': R.COUNTRY, 'codes': n, 'registryExported': m.get('exported'),
                'issuing': bool(self.issue_keys)}

    def info(self):
        m = self.st.meta()
        by_unit, by_status, by_issued = self.st.counts()
        zones = []
        for k in self.reg.zone_order:
            z = self.reg.zones[k]
            zones.append({'key': k, 'name': z['name'], 'region': z['region'], 'codes': by_unit.get(k, 0),
                          'areas': len(self.reg.in_zone.get(k, ()))})
        return {'country': R.COUNTRY, 'name': R.COUNTRY_NAME, 'codes': sum(by_unit.values()), 'byStatus': by_status,
                'byIssue': by_issued, 'zones': zones, 'areas': len(self.reg.areas),
                'areasWithCodes': len(self.st.area_counts()), 'names': len(self.reg.names),
                'registryExported': m.get('exported'), 'importedAt': m.get('imported_at'),
                'engine': R.ENGINE, 'spec': 'engine/SPEC.md', 'licences': R.LICENCES, 'credit': R.CREDIT,
                'creditUrl': R.CREDIT_URL, 'issuing': bool(self.issue_keys),
                'issuePerDay': self.per_day if self.issue_keys else None,
                'example': {'remembered': 'Louis 12 01', 'machine': 'GA-1LV-070-1201-1', 'spot': 'GA-1LV E0794 N0757'}}

    def _full_machine(self, machine):
        """A complete machine form (check digit included), checked against the register."""
        m = E.MACHINE_RE.match(machine.strip().upper().replace(' ', ''))
        if not m:
            raise ApiError(400, 'bad_code', f'“{machine}” is not a machine code (GA-<zone>-<area>-<number>-<check>).')
        if m.group(4) is None:
            raise ApiError(400, 'bad_code', 'A machine code ends with its check digit; use /v1/find to look up a code without it.')
        return self._machine(m)

    def get(self, machine):
        f = self._full_machine(machine)
        row = self.st.code(f['machine'])
        if row is None:
            raise ApiError(404, 'not_issued', f'{f["machine"]} is a valid code but no compound has it.')
        return self.card(row)

    def _machine(self, m):
        """Check a parsed machine form against the register: the area exists, the
        number is in one of its blocks, the check digit (when given) is right."""
        zkey, index, number, chk = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        a = self.reg.by_key.get(f'{zkey}-{index}')
        if a is None:
            raise ApiError(404, 'unknown_area', f'There is no area {index} in zone {zkey}.')
        if not a.holds(number):
            raise ApiError(404, 'not_in_area', f'{number} is in none of the blocks of {a.plate} ({a.key}): a digit is wrong.')
        f = self.reg.forms(a, number)
        if chk is not None and int(chk) != f['check']:
            raise ApiError(422, 'check_digit', 'The check digit does not match: a digit is wrong or two are swapped.')
        f['area'], f['checked'] = a, chk is not None
        return f

    def find(self, q, limit=20):
        text = (q or '').strip()
        if not text:
            raise ApiError(400, 'missing_q', 'Give q: a remembered code ("Louis 12 01"), a machine code, an official address or a spot code.')
        up = text.upper()
        if E.SPOT_RE.match(up):
            try:
                lat, lng = E.spot_decode(text)
            except ValueError as e:
                raise ApiError(422, 'bad_spot', str(e).capitalize() + '.')
            _d, row = self.st.nearest(lat, lng, R.SPOT_M)
            if row is None:
                raise ApiError(404, 'no_code_here', f'The spot {text} is not on a compound with a code.',
                               point={'lat': lat, 'lng': lng})
            return {'query': text, 'kind': 'spot', 'matches': [self.card(row)], 'total': 1}
        m = E.MACHINE_RE.match(up.replace(' ', ''))
        if m:
            f = self._machine(m)
            row = self.st.code(f['machine'])
            if row is None:
                raise ApiError(404, 'not_issued', f'{f["machine"]} is a valid code but no compound has it.')
            return {'query': text, 'kind': 'machine', 'checked': f['checked'], 'matches': [self.card(row)], 'total': 1}
        parts = R.split_remembered(text)
        if parts:
            name, number, chk = parts
            nm = self.reg.name_of(name)
            if nm is not None:
                if len(str(number)) != nm['digits']:
                    raise ApiError(404, 'wrong_length', f'Numbers of {nm["plateName"]} have {nm["digits"]} digits.')
                a = self.reg.decode(name, number)
                if a is None:
                    raise ApiError(404, 'not_issued', f'{nm["plateName"]} {E.group_number(number)} is not issued: no area holds this number.')
                f = self.reg.forms(a, number)
                if chk is not None and int(chk) != f['check']:
                    raise ApiError(422, 'check_digit', 'The check digit does not match: a mistyped name or number.')
                row = self.st.code_by_number(a.name_id, number)
                if row is None or row['zone'] != a.key:
                    raise ApiError(404, 'not_issued', f'No compound has {f["written"]} yet (the number is in the block of {a.plate}, '
                                                      f'{self.reg.zones[a.zone]["name"]}).')
                return {'query': text, 'kind': 'remembered', 'matches': [self.card(row)], 'total': 1}
        n, rows = self.st.codes_by_address(text, limit)
        if rows:
            return {'query': text, 'kind': 'officialAddress', 'matches': [self.card(r) for r in rows], 'total': n}
        if parts:
            raise ApiError(404, 'unknown_name', f'No area of Gabon is called “{parts[0]}”.')
        raise ApiError(404, 'not_found', 'Nothing matches: give a remembered code ("Louis 12 01"), a machine code '
                                         '("GA-1LV-070-1201-1"), an official address or a spot code ("GA-1LV E0794 N0757").')

    def verify(self, code):
        text = (code or '').strip()
        m = E.MACHINE_RE.match(text.upper().replace(' ', ''))
        out = {'code': text, 'syntax': bool(m), 'checkDigit': None, 'inBlocks': None, 'valid': False, 'issued': False}
        if not m:
            out['reason'] = 'not a machine code: GA-<zone>-<area>-<number>-<check>'
            return out
        zkey, index, number, chk = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        a = self.reg.by_key.get(f'{zkey}-{index}')
        if a is None:
            out['reason'] = f'no area {index} in zone {zkey}'
            return out
        out['area'] = a.key
        out['inBlocks'] = a.holds(number)
        f = self.reg.forms(a, number)
        out['checkDigit'] = 'absent' if chk is None else ('ok' if int(chk) == f['check'] else 'wrong')
        if out['checkDigit'] == 'wrong':
            out['reason'] = 'the check digit does not match: a digit is wrong or two are swapped'
            return out
        if not out['inBlocks']:
            out['reason'] = 'the number is in none of the area\'s blocks'
            return out
        out['valid'] = out['checkDigit'] == 'ok'
        if chk is None:
            out['reason'] = 'no check digit: the code cannot be validated'
        row = self.st.code(f['machine'])
        if row is not None:
            out['issued'] = True
            out['status'] = row['status']
            out['machine'] = row['machine']
            out['home'] = row['home']
        return out

    def place_for(self, lat, lng):
        """The area a new compound takes: the area of the nearest issued code within
        250 m (a new house joins its neighbours); else the code area of the point;
        else the nearest numbered area."""
        _d, row = self.st.nearest(lat, lng, R.PLACE_NEAR_M)
        if row is not None:
            a = self.reg.by_key.get(row['zone'])
            if a is not None:
                return a
        a = self.reg.area_at(lat, lng)
        if a is not None and a.numbered():
            return a
        return self.reg.nearest_area(lat, lng)

    def code_at(self, lat, lng, metres):
        """The live code at a point: an outline issued here that holds it, else the
        nearest entrance within ``metres``."""
        for row, ring in self.st.outlines_near(lat, lng):
            if row['status'] != 'retired' and geo.in_ring(lng, lat, ring):
                return 0.0, row
        return self.st.nearest(lat, lng, metres)

    def at(self, lat, lng):
        if not self.reg.in_country(lat, lng):
            raise ApiError(404, 'outside', 'The point is outside Gabon.')
        pa = self.place_for(lat, lng)
        d, row = self.code_at(lat, lng, R.FOUND_M)
        area = self.area_brief(pa) if pa else None
        if row is not None:
            return {'status': 'found', 'code': self.card(row), 'distanceM': round(d), 'area': area}
        out = {'status': 'none', 'canIssue': bool(self.issue_keys), 'area': area}
        d, near = self.st.nearest(lat, lng, 100.0)
        if near is not None:
            out['nearest'] = self.brief(near, d)
        return out

    def near(self, lat, lng, radius, limit):
        if not self.reg.in_country(lat, lng):
            raise ApiError(404, 'outside', 'The point is outside Gabon.')
        hits = self.st.near(lat, lng, radius)
        return {'point': {'lat': lat, 'lng': lng}, 'radiusM': radius, 'total': len(hits),
                'codes': [self.brief(r, d) for d, r in hits[:limit]]}

    def spot(self, lat, lng):
        z = self.reg.spot_zone(lat, lng)
        if z is None:
            raise ApiError(404, 'outside', 'The point is outside Gabon.')
        try:
            code = E.spot_encode(lat, lng, z['key'])
        except ValueError as e:
            raise ApiError(422, 'outside_frame', str(e).capitalize() + '.')
        clat, clng = E.spot_decode(code)
        return {'spot': code, 'zone': self.zone_info(z['key']), 'cellM': 10, 'centre': {'lat': clat, 'lng': clng}}

    def spot_decode(self, code):
        text = (code or '').strip()
        if not E.SPOT_RE.match(text.upper()):
            raise ApiError(400, 'bad_spot', 'A spot code is GA-<zone> E<east> N<north>, e.g. GA-1LV E0794 N0757.')
        try:
            lat, lng = E.spot_decode(text)
        except ValueError as e:
            raise ApiError(422, 'bad_spot', str(e).capitalize() + '.')
        zk = E.SPOT_RE.match(text.upper()).group(1)
        out = {'spot': text.upper(), 'zone': self.zone_info(zk), 'centre': {'lat': lat, 'lng': lng}, 'cellM': 10}
        d, row = self.st.nearest(lat, lng, R.SPOT_M)
        out['code'] = self.brief(row, d) if row is not None else None
        return out

    def zones(self):
        by_unit, _s, _i = self.st.counts()
        out = []
        for k in self.reg.zone_order:
            z = self.reg.zones[k]
            out.append({'key': k, 'index': z['index'], 'name': z['name'], 'region': z['region'], 'codes': by_unit.get(k, 0),
                        'areas': len(self.reg.in_zone.get(k, ()))})
        return {'zones': out, 'total': len(out)}

    def zone(self, key):
        k = key.upper()
        if k not in self.reg.zones:
            raise ApiError(404, 'unknown_zone', f'There is no zone “{key}”; see /v1/zones.')
        z = self.reg.zones[k]
        areas = self.reg.in_zone.get(k, [])
        counts = self.st.area_counts([a.key for a in areas])
        out = dict(self.zone_info(k))
        out['frame'] = {'lon0': z['lon0'], 'lat0': z['lat0'], 'latc': z['latc'], 'digitsE': z['dx'], 'digitsN': z['dy']}
        out['codes'] = sum(counts.values())
        out['areas'] = [dict(self.area_brief(a), codes=counts.get(a.key, 0), blocks=[list(b) for b in a.blocks])
                        for a in areas]
        return out

    def area(self, ident):
        a = self.reg.by_id.get(int(ident)) if ident.isdigit() else self.reg.by_key.get(ident.upper())
        if a is None:
            raise ApiError(404, 'unknown_area', f'There is no area “{ident}”.')
        row = self.st.area_rows()[a.key]
        n = self.st.area_counts([a.key]).get(a.key, 0)
        nm = self.reg.names.get(a.name_key)
        out = self.area_brief(a)
        out.update({'index': a.index, 'nameKey': a.name_key, 'nameId': a.name_id, 'digits': a.digits,
                    'blocks': [list(b) for b in a.blocks], 'codes': n, 'compoundsAtFirstIssue': a.compounds,
                    'place': {'lat': a.point[1], 'lng': a.point[0]} if a.point else None,
                    'frame': list(a.frame), 'alertZone': _bool(row['alert_zone']),
                    'nameRange': {'range': nm['range'], 'spareFrom': nm['spareFrom'],
                                  'areas': [x.key for x in self.reg.families.get(a.name_key, [])]} if nm else None})
        return out

    def areas_named(self, name):
        if not (name or '').strip():
            raise ApiError(400, 'missing_name', 'Give name: a plate name or an official name.')
        hits = self.reg.areas_named(name)
        if not hits:
            raise ApiError(404, 'unknown_name', f'No area of Gabon is called “{name}”.')
        counts = self.st.area_counts([a.key for a in hits])
        return {'name': name, 'total': len(hits),
                'areas': [dict(self.area_brief(a), codes=counts.get(a.key, 0), blocks=[list(b) for b in a.blocks]) for a in hits]}

    def page(self, key, after, limit):
        k = key.upper()
        if k not in self.reg.zones:
            raise ApiError(404, 'unknown_zone', f'There is no zone “{key}”; see /v1/zones.')
        rows = self.st.page(k, after or '', limit + 1)
        more = len(rows) > limit
        rows = rows[:limit]
        return {'zone': k, 'codes': [self.brief(r) for r in rows], 'count': len(rows),
                'next': rows[-1]['machine'] if more else None}

    # ------------------------------------------------------------ write

    def key_id(self, auth):
        if not self.issue_keys:
            raise ApiError(403, 'read_only', 'This deployment is read-only: it is not designated to issue codes.')
        if not auth or not auth.startswith('Bearer '):
            raise ApiError(401, 'unauthorised', 'Send the issuing key as "Authorization: Bearer <key>".')
        key = auth[7:].strip().encode()
        if not any(hmac.compare_digest(key, k.encode()) for k in self.issue_keys):
            raise ApiError(401, 'unauthorised', 'That key is not one of this deployment\'s issuing keys.')
        return 'key:' + hashlib.sha256(key).hexdigest()[:16]

    def issue(self, body, who):
        lat, lng = _point(body)
        outline, of = body.get('outline'), body.get('of')
        if of is not None and not isinstance(of, str):
            raise ApiError(400, 'bad_request', '"of" is the machine code of the compound this door belongs to.')
        of = (of or '').strip()
        since = S.rfc3339(S.now_utc() - dt.timedelta(hours=24))
        n = self.st.issued_by_since(who, since)
        if n >= self.per_day:
            raise ApiError(429, 'limit', f'This key has issued {n} codes in the last 24 hours, its limit. Try again later.')
        with self.lock, self.st.write_lock:
            reg = self.reg
            if not reg.in_country(lat, lng):
                raise ApiError(422, 'outside', 'That point is outside Gabon, so it cannot have a Gabon code.')
            if not reg.within_border(lat, lng):
                raise ApiError(422, 'outside', 'That point is across Gabon\'s border, in a neighbouring country, so it cannot have a Gabon code.')
            ring, area_m2 = None, 0.0
            if not of:
                d, row = self.code_at(lat, lng, R.EXISTS_M)
                if row is not None:
                    raise ApiError(409, 'exists', f'This building already has its code: {row["home"]}.', existing=self.card(row))
                if outline is not None:
                    ring = _ring(outline)
                    if len(ring) >= 3:
                        area_m2 = geo.ring_area_m2(ring)
                    if len(ring) < 3 or area_m2 < R.MIN_AREA_M2 or area_m2 > R.MAX_AREA_M2:
                        raise ApiError(422, 'bad_outline', f'That outline is {area_m2:.0f} m², but a home\'s is between 6 m² and 2 ha.')
                    row = self._overlap(ring)
                    if row is not None:
                        raise ApiError(409, 'exists', f'This building already has its code: {row["home"]}.', existing=self.card(row))
            if of:
                base = self.st.code(of.upper())
                if base is None or base['status'] == 'retired':
                    raise ApiError(404, 'unknown_code', f'There is no code {of} to add a door to.')
                if geo.door_m(float(base['entrance_lat']), float(base['entrance_lng']), lat, lng) > R.DOOR_M:
                    raise ApiError(422, 'too_far', f'That door is more than 80 m from {base["home"]}.')
                a = reg.by_key[base['zone']]
            else:
                a = self.place_for(lat, lng)
            if a is None:
                raise ApiError(422, 'outside', 'There is no named place for this point yet.')
            a = a.copy()
            issued = self.st.area_numbers(a.key)
            nb = len(a.blocks)
            num = R.insert(reg, a, issued, lat, lng)
            if num is None:
                raise ApiError(409, 'full', f'{a.plate} has used every number of its name: its commune chooses a qualifier first.')
            new_blocks = a.blocks[nb:]
            f = reg.forms(a, num)
            now = S.rfc3339(S.now_utc())
            if area_m2 > 0:
                cls, structures, floor = 'residential', 1, round(round(area_m2 * 10) / 10 * 10) / 10
            else:
                cls, structures, floor = '', 0, 0.0
            fields = {'machine': f['machine'], 'home': f['home'], 'written': f['written'], 'zone': a.key,
                      'official_name': a.official, 'number': str(num), 'check': str(f['check']), 'status': 'provisional',
                      'issued': 'on-demand', 'issued_at': now, 'entrance_lat': f'{lat:.7f}', 'entrance_lng': f'{lng:.7f}',
                      'entrance_kind': 'door' if of else 'centre', 'spot_code': _spot(reg, lat, lng), 'official_address': '',
                      'class': cls, 'use': 'residential', 'kind': 'door' if of else 'building',
                      'structures': str(structures), 'floor_area_m2': f'{floor:.1f}', 'rule': '', 'estate': ''}
            extra = {'unit': a.zone, 'name_id': a.name_id, 'num': num, 'lat': float(fields['entrance_lat']),
                     'lng': float(fields['entrance_lng']), 'anchor_lat': lat, 'anchor_lng': lng, 'address_key': None,
                     'outline': json.dumps(ring) if ring else None, 'issued_by': who, 'changed_at': now}
            self.st.add_code(fields, extra, new_blocks, who, a.key, a.blocks)
            if new_blocks:
                reg.by_key[a.key].blocks = list(a.blocks)
            out = self.card(self.st.code(f['machine']))
            if new_blocks:
                out['newBlocks'] = [list(b) for b in new_blocks]
            return out

    def _overlap(self, ring):
        """A live code whose compound the outline covers: its entrance (the centre of a
        mapped compound) inside the outline, or an outline issued here overlapping it."""
        cx, cy = geo.ring_centroid(ring)
        span = max(geo.ground_m(cy, cx, p[1], p[0]) for p in ring)
        for _d, row in self.st.near(cy, cx, span + 1):
            if row['entrance_kind'] == 'centre' and geo.in_ring(row['lng'], row['lat'], ring):
                return row
        for row, other in self.st.outlines_near(cy, cx, span + 150):
            if row['status'] == 'retired':
                continue
            ox, oy = geo.ring_centroid(other)
            if geo.in_ring(cx, cy, other) or geo.in_ring(ox, oy, ring):
                return row
        return None

    def change(self, machine, body, who):
        code = self._full_machine(machine)['machine']
        if not isinstance(body, dict) or not ({'status', 'entrance'} & set(body)):
            raise ApiError(400, 'bad_request', 'Send "status" (confirmed, provisional or retired) and/or "entrance" {lat, lng, kind}.')
        with self.lock, self.st.write_lock:
            row = self.st.code(code)
            if row is None:
                raise ApiError(404, 'unknown_code', f'There is no code {machine}.')
            if row['status'] == 'retired':
                raise ApiError(409, 'retired', f'{row["home"]} is retired; a retired code never comes back and its number is never reused.')
            sets, detail = {}, {'by': who}
            if 'status' in body:
                st = body['status']
                if st not in ('provisional', 'confirmed', 'retired'):
                    raise ApiError(400, 'bad_status', 'status is provisional, confirmed or retired.')
                if st != row['status']:
                    sets['status'] = st
                    detail['status'] = [row['status'], st]
            if 'entrance' in body:
                e = body['entrance']
                if not isinstance(e, dict):
                    raise ApiError(400, 'bad_request', 'entrance is {"lat", "lng", "kind"}.')
                lat, lng = _point(e)
                kind = e.get('kind', 'gate')
                if kind not in ('gate', 'door'):
                    raise ApiError(400, 'bad_request', 'entrance kind is gate or door.')
                d = geo.door_m(float(row['entrance_lat']), float(row['entrance_lng']), lat, lng)
                if d > R.DOOR_M:
                    raise ApiError(422, 'too_far', f'The new entrance is {d:.0f} m from the old one; it may move at most 80 m.')
                if not self.reg.within_border(lat, lng):
                    raise ApiError(422, 'outside', 'That entrance is across Gabon\'s border, in a neighbouring country.')
                sets.update({'entrance_lat': f'{lat:.7f}', 'entrance_lng': f'{lng:.7f}', 'entrance_kind': kind,
                             'spot_code': _spot(self.reg, lat, lng), 'lat': round(lat, 7), 'lng': round(lng, 7)})
                detail['entrance'] = [[row['entrance_lat'], row['entrance_lng']], [sets['entrance_lat'], sets['entrance_lng']]]
            if sets:
                self.st.change_code(code, sets, 'change', detail, S.rfc3339(S.now_utc()))
            return self.card(self.st.code(code))


def _spot(reg, lat, lng):
    try:
        return reg.spot(lat, lng)
    except ValueError:
        return ''


def _point(body):
    if not isinstance(body, dict):
        raise ApiError(400, 'bad_request', 'The body is a JSON object.')
    try:
        lat, lng = float(body['lat']), float(body['lng'])
    except (KeyError, TypeError, ValueError):
        raise ApiError(400, 'bad_point', 'lat and lng are numbers (WGS 84 degrees).')
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ApiError(400, 'bad_point', 'lat is between -90 and 90, lng between -180 and 180.')
    return lat, lng


def _ring(outline):
    try:
        ring = geo.open_ring(outline)
    except (TypeError, ValueError, IndexError):
        raise ApiError(400, 'bad_outline', 'outline is a list of [lng, lat] points.')
    if len(ring) > 500:
        raise ApiError(400, 'bad_outline', 'An outline has at most 500 points.')
    return ring
