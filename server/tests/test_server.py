"""Tests of the registry server on the fixture registry (server/testdata).

  python3 -m unittest discover -s server/tests -t .     (from the repository root)
"""
import csv
import gzip
import hashlib
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from server import register as R
from server import store as S
from server.api import make_server
from server.service import Service

HERE = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(os.path.dirname(HERE), 'testdata')
FIXTURE = os.path.join(TESTDATA, 'registry')
KEY = 'test-issuing-key'


def quiet(*_a, **_k):
    pass


class Running:
    """A server on a fresh copy of the fixture database, on a free port."""

    def __init__(self, keys=(KEY,), per_day=1000, registry=FIXTURE):
        self.dir = tempfile.mkdtemp(prefix='nways-ga-')
        self.db = os.path.join(self.dir, 'addresses.sqlite')
        S.import_registry(registry, self.db, log=quiet)
        self.svc = Service(S.Store(self.db), keys, per_day)
        self.srv = make_server(self.svc, '127.0.0.1', 0, ['*'])
        self.url = 'http://127.0.0.1:%d' % self.srv.server_address[1]
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.thread.start()

    def call(self, method, path, body=None, key=KEY, headers=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.url + path, data=data, method=method)
        if body is not None:
            req.add_header('Content-Type', 'application/json')
        if key:
            req.add_header('Authorization', 'Bearer ' + key)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read() or b'null'), r.headers
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b'null'), e.headers

    def get(self, path):
        return self.call('GET', path, key=None)

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.svc.st.close()
        shutil.rmtree(self.dir)


def load_json(path, encoding='utf-8'):
    with open(path, encoding=encoding) as f:
        return json.load(f)


def dump_json(obj, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f)


def with_gaps(dest):
    """The fixture registry plus server/testdata/gaps.csv: real issued compounds whose
    entrance lies in no département outline (an island 18.4 km off the nearest outline,
    the shoreline, slivers between départements), one file per département."""
    shutil.copytree(FIXTURE, dest)
    with open(os.path.join(TESTDATA, 'gaps.csv'), encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    man = load_json(os.path.join(dest, 'MANIFEST.json'))
    for unit in sorted({r[3][:3] for r in rows[1:]}):
        data = ''.join(S.csv_line(r) for r in [rows[0]] + [r for r in rows[1:] if r[3][:3] == unit]).encode('utf-8')
        with open(os.path.join(dest, unit + '.csv.gz'), 'wb') as raw, \
                gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz:
            gz.write(data)
        man['sha256'][unit + '.csv'] = hashlib.sha256(data).hexdigest()
        man['byUnit'][unit] = data.count(b'\n') - 1
    man['codes'] = sum(man['byUnit'].values())
    dump_json(man, os.path.join(dest, 'MANIFEST.json'))
    return [dict(zip(rows[0], r)) for r in rows[1:]]


def uncompressed(folder):
    out = {}
    for f in sorted(os.listdir(folder)):
        p = os.path.join(folder, f)
        with (gzip.open(p) if f.endswith('.gz') else open(p, 'rb')) as fh:
            out[f] = fh.read()
    return out


class ImportExport(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='nways-ga-')
        self.db = os.path.join(self.dir, 'a.sqlite')

    def tearDown(self):
        shutil.rmtree(self.dir)

    def copy_fixture(self):
        d = os.path.join(self.dir, 'registry')
        shutil.copytree(FIXTURE, d)
        return d

    def test_round_trip_is_byte_identical(self):
        n = S.import_registry(FIXTURE, self.db, log=quiet)
        self.assertEqual(n, load_json(os.path.join(FIXTURE, 'MANIFEST.json'))['codes'])
        out = os.path.join(self.dir, 'out')
        S.export_registry(self.db, out, log=quiet)
        self.assertEqual(uncompressed(out), uncompressed(FIXTURE))

    def test_reimport_is_a_no_op(self):
        S.import_registry(FIXTURE, self.db, log=quiet)
        said = []
        S.import_registry(FIXTURE, self.db, log=said.append)
        self.assertIn('nothing to do', said[0])

    def test_tampered_file_is_refused(self):
        d = self.copy_fixture()
        p = os.path.join(d, '2OL.csv.gz')
        raw = gzip.open(p).read().replace(b'Mvoumou 100', b'Mvoumou 101', 1)
        with gzip.open(p, 'wb') as f:
            f.write(raw)
        with self.assertRaisesRegex(S.RegistryError, 'SHA-256'):
            S.import_registry(d, self.db, log=quiet)
        self.assertFalse(os.path.exists(self.db))

    def test_wrong_totals_are_refused(self):
        d = self.copy_fixture()
        p = os.path.join(d, 'MANIFEST.json')
        m = load_json(p)
        m['codes'] += 1
        dump_json(m, p)
        with self.assertRaisesRegex(S.RegistryError, 'MANIFEST'):
            S.import_registry(d, self.db, log=quiet)

    def test_missing_file_is_refused(self):
        d = self.copy_fixture()
        os.remove(os.path.join(d, '2OL.csv.gz'))
        with self.assertRaises(S.RegistryError):
            S.import_registry(d, self.db, log=quiet)

    def test_other_country_is_refused(self):
        d = self.copy_fixture()
        p = os.path.join(d, 'MANIFEST.json')
        m = load_json(p)
        m['country'] = 'XX'
        dump_json(m, p)
        with self.assertRaisesRegex(S.RegistryError, 'XX'):
            S.import_registry(d, self.db, log=quiet)

    def test_local_codes_are_kept_unless_replace(self):
        S.import_registry(FIXTURE, self.db, log=quiet)
        svc = Service(S.Store(self.db), [KEY], 10)
        svc.issue({'lat': -2.3247, 'lng': 13.6243}, 'key:test')
        svc.st.close()
        with self.assertRaisesRegex(S.RegistryError, 'Export it first'):
            S.import_registry(FIXTURE, self.db, log=quiet)
        S.import_registry(FIXTURE, self.db, replace=True, log=quiet)
        self.assertEqual(S.local_changes(self.db), 0)

    def test_grid_index_without_rtree(self):
        """Where SQLite has no R*Tree, the integer grid answers the same radius searches."""
        S.import_registry(FIXTURE, self.db, log=quiet)
        rtree = S.Store(self.db)
        real = S.has_rtree
        S.has_rtree = lambda con: False
        try:
            db2 = os.path.join(self.dir, 'grid.sqlite')
            S.import_registry(FIXTURE, db2, log=quiet)
        finally:
            S.has_rtree = real
        grid = S.Store(db2)
        self.assertEqual(grid.spatial, 'grid')
        for lat, lng, m in ((-2.3388350, 13.3561600, 300), (-2.2335413, 13.6015500, 120), (-2.2, 13.55, 500)):
            a = [(round(d, 6), r['machine']) for d, r in rtree.near(lat, lng, m)]
            b = [(round(d, 6), r['machine']) for d, r in grid.near(lat, lng, m)]
            self.assertEqual(a, b)
        self.assertTrue(rtree.near(-2.3388350, 13.3561600, 300))
        rtree.close()
        grid.close()

    def test_csv_quoting_matches_the_issuer(self):
        self.assertEqual(S.csv_line(['a', 'b,c', 'say "x"', '', ' lead', '\\.']), 'a,"b,c","say ""x""",," lead","\\."\n')


class Endpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Running()
        cls.code = 'GA-2OL-027-100-4'

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def ok(self, path):
        st, body, _h = self.s.get(path)
        self.assertEqual(st, 200, body)
        return body

    def err(self, path, status, code):
        st, body, _h = self.s.get(path)
        self.assertEqual(st, status, body)
        self.assertEqual(body['error']['code'], code)
        self.assertTrue(body['error']['message'])
        return body

    def test_health_and_info(self):
        h = self.ok('/v1/health')
        self.assertEqual((h['status'], h['country'], h['codes']), ('ok', 'GA', 685))
        i = self.ok('/v1/info')
        self.assertEqual(i['codes'], 685)
        self.assertEqual(len(i['zones']), 49)
        self.assertEqual(i['credit'], R.CREDIT)
        self.assertIn('data', i['licences'])

    def test_card_has_every_registry_column(self):
        c = self.ok('/v1/codes/' + self.code)
        self.assertEqual(list(c['record']), S.CODE_COLS)
        self.assertEqual(c['home'], 'Mvoumou 100')
        self.assertEqual(c['written'], 'Mvoumou 100')
        self.assertEqual(c['zone']['key'], '2OL')
        self.assertEqual(c['area']['key'], '2OL-027')
        self.assertTrue(c['spotCode'].startswith('GA-2OL E'))

    def test_card_errors(self):
        self.err('/v1/codes/GA-2OL-027-100-7', 422, 'check_digit')
        self.err('/v1/codes/GA-2OL-027-100', 400, 'bad_code')
        self.err('/v1/codes/hello', 400, 'bad_code')
        self.err('/v1/codes/GA-2OL-999-100-1', 404, 'unknown_area')
        self.err('/v1/codes/GA-2OL-027-9999-1', 404, 'not_in_area')
        free = R.Register().forms(R.Register().by_key['2OL-027'], 399)['machine']
        self.err('/v1/codes/' + free, 404, 'not_issued')

    def test_find_remembered_any_spelling(self):
        for q in ('Mvoumou 100', 'mvoumou 100', 'MVOUMOU100', '  Mvoumou   100 ', 'Mvoumou 100-4', 'Mvoumou · 100'):
            b = self.ok('/v1/find?q=' + urllib.request.quote(q))
            self.assertEqual(b['matches'][0]['machine'], self.code, q)
            self.assertEqual(b['kind'], 'remembered')

    def test_find_accents_and_official_alias(self):
        b = self.ok('/v1/find?q=' + urllib.request.quote('MOSSETE 120'))
        self.assertEqual(b['matches'][0]['home'], 'Mossété 120')

    def test_find_machine_and_spot(self):
        b = self.ok('/v1/find?q=' + self.code.lower())
        self.assertEqual((b['kind'], b['matches'][0]['machine'], b['checked']), ('machine', self.code, True))
        spot = b['matches'][0]['spotCode']
        b = self.ok('/v1/find?q=' + urllib.request.quote(spot))
        self.assertEqual(b['kind'], 'spot')

    def test_find_errors(self):
        self.err('/v1/find?q=', 400, 'missing_q')
        self.err('/v1/find?q=GA-2OL-027-100-7', 422, 'check_digit')
        self.err('/v1/find?q=Mvoumou%20100-7', 422, 'check_digit')
        self.err('/v1/find?q=Mvoumou%201000', 404, 'wrong_length')
        self.err('/v1/find?q=Mvoumou%20399', 404, 'not_issued')
        self.err('/v1/find?q=Qwertyville%20123', 404, 'unknown_name')
        self.err('/v1/find?q=hello', 404, 'not_found')

    def test_at(self):
        c = self.ok('/v1/codes/' + self.code)
        e = c['entrance']
        b = self.ok('/v1/at?lat=%s&lng=%s' % (e['lat'], e['lng'] + 0.00005))
        self.assertEqual((b['status'], b['code']['machine']), ('found', self.code))
        b = self.ok('/v1/at?lat=-2.05&lng=13.85')
        self.assertEqual(b['status'], 'none')
        self.assertTrue(b['area']['key'])
        self.err('/v1/at?lat=4.5&lng=9', 404, 'outside')
        self.err('/v1/at?lat=x&lng=9', 400, 'bad_lat')
        self.err('/v1/at?lat=1', 400, 'missing_lng')

    def test_near(self):
        e = self.ok('/v1/codes/' + self.code)['entrance']
        b = self.ok('/v1/near?lat=%s&lng=%s&radius=200' % (e['lat'], e['lng']))
        self.assertEqual(b['codes'][0]['machine'], self.code)
        d = [x['distanceM'] for x in b['codes']]
        self.assertEqual(d, sorted(d))
        self.assertTrue(all(x <= 200 for x in d))
        self.assertLessEqual(len(self.ok('/v1/near?lat=%s&lng=%s&radius=500&limit=3' % (e['lat'], e['lng']))['codes']), 3)
        self.err('/v1/near?lat=%s&lng=%s&radius=501' % (e['lat'], e['lng']), 400, 'bad_radius')
        self.err('/v1/near?lat=%s&lng=%s&limit=101' % (e['lat'], e['lng']), 400, 'bad_limit')

    def test_verify(self):
        b = self.ok('/v1/verify?code=' + self.code)
        self.assertEqual((b['valid'], b['issued'], b['checkDigit']), (True, True, 'ok'))
        b = self.ok('/v1/verify?code=GA-2OL-027-100-7')
        self.assertEqual((b['valid'], b['checkDigit']), (False, 'wrong'))
        self.assertNotIn('machine', b)  # a wrong check digit is never corrected
        b = self.ok('/v1/verify?code=GA-2OL-027-100')
        self.assertEqual((b['valid'], b['checkDigit']), (False, 'absent'))
        b = self.ok('/v1/verify?code=nonsense')
        self.assertFalse(b['syntax'])
        self.err('/v1/verify', 400, 'missing_code')

    def test_spot(self):
        b = self.ok('/v1/spot?lat=-2.3245863&lng=13.6240468')
        self.assertEqual(b['zone']['key'], '2OL')
        d = self.ok('/v1/spot/decode?code=' + urllib.request.quote(b['spot']))
        self.assertEqual(d['code']['machine'], 'GA-2OL-033-100-7')
        self.err('/v1/spot?lat=4.5&lng=9', 404, 'outside')
        # in no département outline: the nearest outline within 20 km whose frame holds the point
        b = self.ok('/v1/spot?lat=0.8104524&lng=9.3792151')
        self.assertEqual((b['spot'], b['zone']['key']), ('GA-1KM E0881 N6971', '1KM'))
        self.err('/v1/spot/decode?code=hello', 400, 'bad_spot')
        self.err('/v1/spot/decode?code=GA-2OL%20E123%20N1234', 400, 'bad_spot')
        self.err('/v1/spot/decode?code=GA-2OL%20E01234%20N1234', 422, 'bad_spot')

    def test_zones_and_areas(self):
        z = self.ok('/v1/zones')
        self.assertEqual(z['total'], 49)
        one = self.ok('/v1/zones/2ol')
        self.assertEqual((one['key'], one['codes'], len(one['areas'])), ('2OL', 685, 33))
        self.err('/v1/zones/XYZ', 404, 'unknown_zone')
        a = self.ok('/v1/areas/2OL-027')
        self.assertEqual((a['plateName'], a['codes'], a['blocks']), ('Mvoumou', 150, [[100, 399]]))
        self.assertEqual(self.ok('/v1/areas/%d' % a['id'])['key'], '2OL-027')
        self.err('/v1/areas/99999', 404, 'unknown_area')
        m = self.ok('/v1/areas?name=maloundou')
        self.assertIn('2OL-015', [x['key'] for x in m['areas']])
        self.err('/v1/areas?name=Qwertyville', 404, 'unknown_name')
        self.err('/v1/areas', 400, 'missing_name')

    def test_paging(self):
        seen, after = [], ''
        while True:
            b = self.ok('/v1/zones/2OL/codes?limit=250&after=' + after)
            seen += [c['machine'] for c in b['codes']]
            if not b['next']:
                break
            after = b['next']
        self.assertEqual(len(seen), 685)
        self.assertEqual(seen, sorted(seen))
        self.err('/v1/zones/2OL/codes?limit=0', 400, 'bad_limit')

    def test_routing_errors(self):
        self.err('/v1/nothing', 404, 'not_found')
        st, body, _h = self.s.call('DELETE', '/v1/codes/' + self.code)
        self.assertEqual((st, body['error']['code']), (405, 'method_not_allowed'))

    def test_cors(self):
        st, _b, h = self.s.call('GET', '/v1/health', key=None, headers={'Origin': 'https://example.org'})
        self.assertEqual(h['Access-Control-Allow-Origin'], '*')


class Issue(unittest.TestCase):
    def setUp(self):
        self.s = Running(per_day=1000)

    def tearDown(self):
        self.s.close()

    def post(self, body, key=KEY):
        return self.s.call('POST', '/v1/codes', body, key=key)

    def test_parity_with_the_issuer(self):
        """Every point of server/testdata/parity.json, posted in order, gets the number,
        forms and blocks the N-Ways issuer gives it."""
        cases = load_json(os.path.join(TESTDATA, 'parity.json'), encoding='utf-8')
        status = {'exists': 409, 'outside': 422, 'too_far': 422, 'full': 409}
        codes = {'too_far': 'too_far', 'exists': 'exists', 'outside': 'outside', 'full': 'full'}
        for c in cases['issue']:
            body = {k: v for k, v in c['input'].items() if k != 'note'}
            st, out, _h = self.post(body)
            want = c['expected']
            if 'error' in want:
                self.assertEqual(st, status[want['error']], (c, out))
                self.assertEqual(out['error']['code'], codes[want['error']], c)
                if 'existing' in want:
                    self.assertEqual(out['existing']['machine'], want['existing'])
                continue
            self.assertEqual(st, 201, (c, out))
            got = {'machine': out['machine'], 'home': out['home'], 'written': out['written'], 'number': out['number'],
                   'area': out['area']['key']}
            self.assertEqual(got, {k: want[k] for k in got}, c['input'].get('note'))
            self.assertEqual(out.get('newBlocks'), want.get('newBlocks'), c['input'].get('note'))
            self.assertEqual((out['status'], out['issued']), ('provisional', 'on-demand'))
        # the extension block and every new code are in the export
        out = os.path.join(self.s.dir, 'export')
        S.export_registry(self.s.db, out, log=quiet)
        areas = gzip.open(os.path.join(out, 'areas.csv.gz')).read().decode()
        self.assertIn('2OL-033,', areas)
        self.assertIn(',100-119|120-169,', areas)
        rows = gzip.open(os.path.join(out, '2OL.csv.gz')).read().decode()
        self.assertEqual(rows.count(',on-demand,'), sum(1 for c in cases['issue']
                                                         if 'error' not in c['expected'] and c['expected']['area'].startswith('2OL')))
        # and a re-import of that export serves the same codes
        db2 = os.path.join(self.s.dir, 'again.sqlite')
        S.import_registry(out, db2, log=quiet)
        again = os.path.join(self.s.dir, 'again')
        S.export_registry(db2, again, log=quiet)
        self.assertEqual(uncompressed(out), uncompressed(again))

    def test_insert_and_places_parity(self):
        cases = load_json(os.path.join(TESTDATA, 'parity.json'), encoding='utf-8')
        reg = R.Register()
        st = self.s.svc.st
        for c in cases['insert']:
            a = reg.by_key[c['input']['area']].copy()
            nb = len(a.blocks)
            n = R.insert(reg, a, st.area_numbers(a.key), c['input']['lat'], c['input']['lng'])
            want = c['expected']
            self.assertEqual((n, [list(b) for b in a.blocks], len(a.blocks) - nb), (want['number'], want['blocks'], want['newBlocks']))
        from server import geo
        for c in cases['places']:
            lat, lng = c['input']['lat'], c['input']['lng']
            want = c['expected']
            z = reg.zone_at(lat, lng)
            self.assertEqual(z['key'] if z else None, want.get('zone'))
            if z:
                self.assertEqual(reg.area_at(lat, lng).key, want['area'])
            if 'spot' in want:
                self.assertEqual(reg.spot(lat, lng), want['spot'])
            else:
                self.assertIsNone(z)
                with self.assertRaises(ValueError):
                    reg.spot(lat, lng)
            self.assertEqual(reg.nearest_area(lat, lng).key, want['nearestArea'])
            self.assertEqual(geo.plus_code(lat, lng), want['plusCode'])

    def test_outline_rules(self):
        lat, lng = -2.2, 13.55
        d = 0.00004
        small = [[lng, lat], [lng + d / 4, lat], [lng + d / 4, lat + d / 4], [lng, lat + d / 4]]
        st, out, _h = self.post({'lat': lat, 'lng': lng, 'outline': small})
        self.assertEqual((st, out['error']['code']), (422, 'bad_outline'))
        huge = [[lng, lat], [lng + 0.003, lat], [lng + 0.003, lat + 0.003], [lng, lat + 0.003]]
        st, out, _h = self.post({'lat': lat, 'lng': lng, 'outline': huge})
        self.assertEqual((st, out['error']['code']), (422, 'bad_outline'))
        ring = [[lng, lat], [lng + 0.0001, lat], [lng + 0.0001, lat + 0.0001], [lng, lat + 0.0001], [lng, lat]]
        st, out, _h = self.post({'lat': lat + 0.00005, 'lng': lng + 0.00005, 'outline': ring})
        self.assertEqual(st, 201, out)
        self.assertEqual((out['profile']['class'], out['profile']['structures']), ('residential', 1))
        self.assertGreater(out['profile']['floorAreaM2'], 100)
        # the same building again: inside its outline, then an overlapping outline
        st, again, _h = self.post({'lat': lat + 0.00009, 'lng': lng + 0.00002})
        self.assertEqual((st, again['error']['code'], again['existing']['machine']), (409, 'exists', out['machine']))
        shifted = [[x + 0.00002, y + 0.00002] for x, y in ring]
        st, again, _h = self.post({'lat': lat + 0.00030, 'lng': lng + 0.00030, 'outline': shifted})
        self.assertEqual((st, again['error']['code']), (409, 'exists'))
        st, again, _h = self.post({'lat': lat - 0.01, 'lng': lng, 'outline': [[1, 2]]})
        self.assertEqual((st, again['error']['code']), (422, 'bad_outline'))

    def test_auth_and_body_errors(self):
        st, out, _h = self.post({'lat': -2.2, 'lng': 13.55}, key=None)
        self.assertEqual((st, out['error']['code']), (401, 'unauthorised'))
        st, out, _h = self.post({'lat': -2.2, 'lng': 13.55}, key='wrong')
        self.assertEqual((st, out['error']['code']), (401, 'unauthorised'))
        st, out, _h = self.post({'lat': 'x'})
        self.assertEqual((st, out['error']['code']), (400, 'bad_point'))
        st, out, _h = self.post({'lat': -2.2, 'lng': 13.55, 'of': 'GA-2OL-027-399-3'})
        self.assertEqual((st, out['error']['code']), (404, 'unknown_code'))
        req = urllib.request.Request(self.s.url + '/v1/codes', data=b'{oops', method='POST',
                                     headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + KEY})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        with e.exception:
            self.assertEqual(json.loads(e.exception.read())['error']['code'], 'bad_json')

    def test_change_status_and_entrance(self):
        code = 'GA-2OL-027-100-4'
        st, out, _h = self.s.call('PATCH', '/v1/codes/' + code, {'status': 'confirmed'})
        self.assertEqual((st, out['status']), (200, 'confirmed'))
        e = out['entrance']
        st, out, _h = self.s.call('PATCH', '/v1/codes/' + code, {'entrance': {'lat': e['lat'] + 0.0002, 'lng': e['lng']}})
        self.assertEqual((st, out['entrance']['kind']), (200, 'gate'))
        self.assertAlmostEqual(out['entrance']['lat'], e['lat'] + 0.0002, places=7)
        st, out, _h = self.s.call('PATCH', '/v1/codes/' + code, {'entrance': {'lat': e['lat'] + 0.002, 'lng': e['lng']}})
        self.assertEqual((st, out['error']['code']), (422, 'too_far'))
        st, out, _h = self.s.call('PATCH', '/v1/codes/' + code, {'status': 'gone'})
        self.assertEqual((st, out['error']['code']), (400, 'bad_status'))
        st, out, _h = self.s.call('PATCH', '/v1/codes/' + code, {'status': 'retired'})
        self.assertEqual((st, out['status']), (200, 'retired'))
        st, out, _h = self.s.call('PATCH', '/v1/codes/' + code, {'status': 'confirmed'})
        self.assertEqual((st, out['error']['code']), (409, 'retired'))
        # a retired code is never found by point, and its number is never given again
        st, at, _h = self.s.get('/v1/at?lat=%s&lng=%s' % (e['lat'], e['lng']))
        self.assertNotEqual((at.get('code') or {}).get('machine'), code)
        st, out, _h = self.s.call('PATCH', '/v1/codes/GA-2OL-027-399-3', {'status': 'confirmed'})
        self.assertEqual(st, 404)
        # a wrong check digit is refused as such, never treated as another code
        st, out, _h = self.s.call('PATCH', '/v1/codes/GA-2OL-027-100-5', {'status': 'confirmed'})
        self.assertEqual((st, out['error']['code']), (422, 'check_digit'))
        st, out, _h = self.s.call('PATCH', '/v1/codes/GA-2OL-027-100', {'status': 'confirmed'})
        self.assertEqual((st, out['error']['code']), (400, 'bad_code'))


class Gaps(unittest.TestCase):
    """A point in no département outline is in Gabon when the spot-code rule gives it a
    spot code (SPEC 5): found by point, and issued, like any other."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='nways-ga-gaps-')
        cls.rows = with_gaps(os.path.join(cls.tmp, 'registry'))
        cls.reg = R.Register()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def setUp(self):
        self.s = Running(registry=os.path.join(self.tmp, 'registry'))

    def tearDown(self):
        self.s.close()

    def row(self, machine):
        return next(r for r in self.rows if r['machine'] == machine)

    def test_fixture_rows_lie_in_no_outline(self):
        self.assertGreaterEqual(len(self.rows), 8)
        for r in self.rows:
            lat, lng = float(r['entrance_lat']), float(r['entrance_lng'])
            self.assertIsNone(self.reg.zone_at(lat, lng), r['machine'])
            self.assertTrue(self.reg.in_country(lat, lng), r['machine'])
            self.assertEqual(self.reg.spot(lat, lng), r['spot_code'])

    def test_at_finds_each_code(self):
        for r in self.rows:
            st, b, _h = self.s.get('/v1/at?lat=%s&lng=%s' % (r['entrance_lat'], r['entrance_lng']))
            self.assertEqual((st, b.get('status'), (b.get('code') or {}).get('machine')), (200, 'found', r['machine']))
            # the area: that of the issued code within 250 m (placeFor)
            self.assertEqual(b['area']['key'], r['zone'])

    def test_near_in_a_gap(self):
        r = self.row('GA-1KM-068-108-8')
        st, b, _h = self.s.get('/v1/near?lat=%s&lng=%s&radius=50' % (r['entrance_lat'], r['entrance_lng']))
        self.assertEqual((st, b['codes'][0]['machine']), (200, r['machine']))

    def test_issue_in_a_gap(self):
        r = self.row('GA-1KM-068-108-8')
        lat, lng = float(r['entrance_lat']), float(r['entrance_lng']) + 0.0015
        self.assertIsNone(self.reg.zone_at(lat, lng))
        st, b, _h = self.s.get('/v1/at?lat=%s&lng=%s' % (lat, lng))
        self.assertEqual((st, b['status'], b['area']['key']), (200, 'none', '1KM-068'))
        st, out, _h = self.s.call('POST', '/v1/codes', {'lat': lat, 'lng': lng})
        self.assertEqual(st, 201, out)
        self.assertEqual(out['area']['key'], '1KM-068')
        self.assertEqual(out['spotCode'], self.reg.spot(lat, lng))
        st, b, _h = self.s.get('/v1/at?lat=%s&lng=%s' % (lat, lng))
        self.assertEqual((b['status'], b['code']['machine']), ('found', out['machine']))
        # another door of a compound in a gap
        st, door, _h = self.s.call('POST', '/v1/codes', {'lat': float(r['entrance_lat']) + 0.0002,
                                                         'lng': float(r['entrance_lng']), 'of': r['machine']})
        self.assertEqual((st, door['area']['key']), (201, r['zone']), door)

    def test_far_outside_is_refused(self):
        # 25 km off the nearest outline (beyond 20 km), the open sea, Douala
        for lat, lng in ((0.81, 9.20), (0.0, 5.0), (4.05, 9.70)):
            self.assertFalse(self.reg.in_country(lat, lng))
            st, b, _h = self.s.get('/v1/at?lat=%s&lng=%s' % (lat, lng))
            self.assertEqual((st, b['error']['code']), (404, 'outside'))
            st, b, _h = self.s.get('/v1/near?lat=%s&lng=%s' % (lat, lng))
            self.assertEqual((st, b['error']['code']), (404, 'outside'))
            st, b, _h = self.s.call('POST', '/v1/codes', {'lat': lat, 'lng': lng})
            self.assertEqual((st, b['error']['code']), (422, 'outside'))

    def test_move_entrance_in_a_gap(self):
        r = self.row('GA-1KO-037-239-6')
        lat, lng = float(r['entrance_lat']) + 0.0002, float(r['entrance_lng'])
        self.assertIsNone(self.reg.zone_at(lat, lng))
        st, out, _h = self.s.call('PATCH', '/v1/codes/' + r['machine'], {'entrance': {'lat': lat, 'lng': lng}})
        self.assertEqual(st, 200, out)
        self.assertEqual(out['spotCode'], self.reg.spot(lat, lng))


class Border(unittest.TestCase):
    """The border decides (engine/SPEC.md 6.6): a point more than 300 m outside Gabon's national
    border is refused even when a spot zone reaches it."""

    @classmethod
    def setUpClass(cls):
        cls.reg = R.Register()

    def setUp(self):
        self.s = Running()

    def tearDown(self):
        self.s.close()

    def test_well_across_the_border_is_refused(self):
        # over 4 km into a neighbouring country, within 20 km of a département, so it has a spot zone
        lat, lng = -2.3927, 13.5882
        self.assertTrue(self.reg.in_country(lat, lng))
        self.assertGreater(self.reg.border.outside_m(lat, lng), 4000)
        st, b, _h = self.s.call('POST', '/v1/codes', {'lat': lat, 'lng': lng})
        self.assertEqual((st, b['error']['code']), (422, 'outside'), b)

    def test_inside_is_accepted(self):
        lat, lng = -2.2, 13.55
        self.assertEqual(self.reg.border.outside_m(lat, lng), 0.0)
        st, b, _h = self.s.call('POST', '/v1/codes', {'lat': lat, 'lng': lng})
        self.assertEqual(st, 201, b)

    def test_on_the_border_line_is_accepted(self):
        # about 150 m outside the line: the line's own accuracy
        lat, lng = 1.4397, 13.22687
        self.assertTrue(0 < self.reg.border.outside_m(lat, lng) < 200)
        st, b, _h = self.s.call('POST', '/v1/codes', {'lat': lat, 'lng': lng})
        self.assertEqual(st, 201, b)

    def test_entrance_never_moves_across(self):
        st, b, _h = self.s.call('POST', '/v1/codes', {'lat': 1.22136, 'lng': 14.30829})   # about 220 m out
        self.assertEqual(st, 201, b)
        lat, lng = 1.22136, 14.30894   # 72 m farther out
        d = self.reg.border.outside_m(lat, lng)
        self.assertGreater(d, 245, d)
        st, out, _h = self.s.call('PATCH', '/v1/codes/' + b['machine'], {'entrance': {'lat': lat, 'lng': lng}})
        self.assertEqual((st, out['error']['code']), (422, 'outside'), out)


class Limits(unittest.TestCase):
    def test_daily_limit_per_key(self):
        s = Running(per_day=2)
        try:
            for i in range(2):
                st, out, _h = s.call('POST', '/v1/codes', {'lat': -2.2 + i * 0.001, 'lng': 13.55})
                self.assertEqual(st, 201, out)
            st, out, _h = s.call('POST', '/v1/codes', {'lat': -2.21, 'lng': 13.55})
            self.assertEqual((st, out['error']['code']), (429, 'limit'))
        finally:
            s.close()

    def test_read_only_deployment(self):
        s = Running(keys=())
        try:
            st, out, _h = s.call('POST', '/v1/codes', {'lat': -2.2, 'lng': 13.55})
            self.assertEqual((st, out['error']['code']), (403, 'read_only'))
            # refused before the body is read, whatever the body is
            req = urllib.request.Request(s.url + '/v1/codes', data=b'lat=1', method='POST',
                                         headers={'Content-Type': 'text/plain'})
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(req)
            with e.exception:
                self.assertEqual((e.exception.code, json.loads(e.exception.read())['error']['code']), (403, 'read_only'))
            self.assertFalse(s.get('/v1/health')[1]['issuing'])
        finally:
            s.close()


if __name__ == '__main__':
    unittest.main()
