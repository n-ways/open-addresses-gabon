#!/usr/bin/env python3
"""Tests of the Gabon reference engine (ga_engine.py) on the frozen register.

  python3 engine/reference/test_ga.py
"""
import os, random, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ga_engine as e  # noqa: E402
import ga_border  # noqa: E402
import plate_names as P  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VECTORS = os.path.join(HERE, 'vectors.json')


class Damm(unittest.TestCase):
    def test_published_vector(self):
        self.assertEqual(e.damm('572'), 4)

    def test_every_single_error_and_swap(self):
        rnd = random.Random(7)
        for _ in range(300):
            s = ''.join(rnd.choice('0123456789') for _ in range(14))
            c = e.damm(s)
            for i in range(len(s)):
                for d in '0123456789':
                    if d != s[i]:
                        self.assertNotEqual(e.damm(s[:i] + d + s[i + 1:]), c)
                if i + 1 < len(s) and s[i] != s[i + 1]:
                    self.assertNotEqual(e.damm(s[:i] + s[i + 1] + s[i] + s[i + 2:]), c)


class NameKeys(unittest.TestCase):
    def test_equal(self):
        for group in (('Nzeng-Ayong', 'Nzeng Ayong', 'NZENG AYONG'), ('Mont-Bouët', 'Mont Bouet'), ('Akébé', 'Akebe'),
                      ('Quartier Louis', 'Louis'), ('St Hilaire', 'Saint-Hilaire')):
            self.assertEqual(len({e.name_key(x) for x in group}), 1, group)

    def test_digits_never_squeezed(self):
        self.assertNotEqual(e.name_key('Mile 22'), e.name_key('Mile 2'))

    def test_generic(self):
        self.assertTrue(e.is_generic('Village') and e.is_generic('quarter') and e.is_generic('Campement'))
        self.assertFalse(e.is_generic('Villa Rosa'))


class Plates(unittest.TestCase):
    def test_limits(self):
        self.assertTrue(P.fits('Akébé', 'fr'))
        self.assertFalse(P.fits('Nzeng-Ayong Centre Ville', 'fr'))
        self.assertFalse(P.fits('PK 8', 'fr'))  # no digit in a plate name


class Register(unittest.TestCase):
    def test_one_area_per_number(self):
        for k, v in e.names()['names'].items():
            last = v['range'][0] - 1
            for zk, ix, c, lo, hi in v['blocks']:
                self.assertEqual(lo, last + 1, k)  # blocks follow each other, never overlap
                self.assertGreaterEqual(hi - lo + 1, 2 * c)  # room to grow inside the block
                self.assertEqual(len(str(lo)), v['digits'])
                self.assertLessEqual(v['digits'], 5)  # never more than five digits
                last = hi
            self.assertLessEqual(last, v['range'][0] - 1 + int(9 * 10 ** (v['digits'] - 1) * (1 - e.NAME_SPARE)))

    def test_machine_round_trip(self):
        rnd = random.Random(11)
        reg = e._load(os.path.join(e.REPO, 'engine', 'data', 'register.json'))
        for a in rnd.sample([a for a in reg['areas'] if a['blocks']], 300):
            lo, hi = a['blocks'][0]
            n = rnd.randint(lo, hi)
            m = e.machine(a['zone'], a['index'], n, a['nameId'])
            p = e.parse_machine(m)
            self.assertTrue(p['valid'], m)
            r = e.resolve_remembered(f"{a['name']} {e.group_number(n)}")
            self.assertEqual(r['code'], m)
            bad = m[:-1] + str((int(m[-1]) + 1) % 10)
            self.assertFalse(e.parse_machine(bad)['valid'])

    def test_refusals(self):
        with self.assertRaises(ValueError):
            e.resolve_remembered('Nulle Part 1234')


class Spots(unittest.TestCase):
    def test_round_trip(self):
        rnd = random.Random(3)
        done = 0
        while done < 200:
            lat, lon = rnd.uniform(-3.9, 2.3), rnd.uniform(8.7, 14.5)
            if e.zone_at(lat, lon) is None:
                continue
            code = e.spot_encode(lat, lon)
            la, lo = e.spot_decode(code)
            self.assertLess(abs(la - lat) * 110574, 6)
            self.assertLess(abs(lo - lon) * 111320, 6.5)
            self.assertEqual(e.spot_encode(la, lo), code)
            done += 1

    def test_example(self):
        self.assertEqual(e.spot_encode(0.3925, 9.4536), 'GA-1LV E1041 N0580')  # Libreville

    def test_outside_every_outline(self):
        # Moka, Komo-Mondah: an island compound 18 km from the nearest outline keeps a spot code
        lat, lon = 0.8104524, 9.3792151
        self.assertIsNone(e.zone_at(lat, lon))
        self.assertEqual(e.spot_zone(lat, lon), '1KM')
        code = e.spot_encode(lat, lon)
        self.assertEqual(code, 'GA-1KM E0881 N6971')
        la, lo = e.spot_decode(code)
        self.assertLess(abs(la - lat) * 110574, 6)
        self.assertLess(abs(lo - lon) * 111320, 6.5)
        with self.assertRaises(ValueError):
            e.spot_encode(4.05, 9.70)  # Douala, Cameroon: no outline within 20 km


class Numbering(unittest.TestCase):
    def test_hilbert(self):
        self.assertEqual([e.hilbert_index(1, x, y) for x, y in ((0, 0), (0, 1), (1, 1), (1, 0))], [0, 1, 2, 3])

    def test_block_and_infill(self):
        pts = {f'c{i}': (11.5 + i * 0.0001, 3.86 + (i % 5) * 0.0001) for i in range(40)}
        box = (11.4999, 3.8599, 11.5041, 3.8606)
        nums = e.issue_numbers(pts, box, (1000, 1199))
        self.assertEqual(len(set(nums.values())), 40)
        self.assertTrue(all(1000 <= n <= 1132 for n in nums.values()))  # the tail reserve stays free
        n = e.provisional_number((11.50005, 3.86), nums, pts, box, (1000, 1199))
        self.assertNotIn(n, nums.values())


class Vectors(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(VECTORS), 'run tools/vectors.py first')
    def test_vectors(self):
        v = e._load(VECTORS)
        for w, k in v['nameKeys']:
            self.assertEqual(e.name_key(w), k)
        for s in v['spots']:
            self.assertEqual(e.spot_encode(s['lat'], s['lon']), s['code'])
        issued = 0
        for s in v['spotsOutside']:
            self.assertIsNone(e.zone_at(s['lat'], s['lon']))
            if 'error' in s:
                with self.assertRaises(ValueError):
                    e.spot_encode(s['lat'], s['lon'])
                continue
            issued += 'machine' in s
            self.assertEqual(e.spot_zone(s['lat'], s['lon']), s['zone'])
            self.assertEqual(e.spot_encode(s['lat'], s['lon']), s['code'])
            self.assertEqual(list(e.spot_decode(s['code'])), s['decoded'])
        self.assertEqual(issued, 80)



class Border(unittest.TestCase):
    """The border decides (SPEC 6.6): engine/data/border.json and the 300 m rule."""

    @classmethod
    def setUpClass(cls):
        cls.b = ga_border.Border.load()

    def test_shipped_file(self):
        self.assertLess(os.path.getsize(ga_border.BORDER_JSON), 1 << 20)
        self.assertEqual(self.b.tolerance_m, 50.0)
        self.assertEqual(self.b.limit_m, 245.0)  # 300 m less the simplification and the plane's margin

    def test_inside_and_across(self):
        for lat, lng in ((0.3927, 9.4536), (-0.7193, 8.7815), (1.5995, 11.5793), (-2.2, 13.55)):
            self.assertEqual(self.b.outside_m(lat, lng), 0.0, (lat, lng))
            self.assertTrue(self.b.allows(lat, lng))
        # in a neighbouring country, kilometres from the line
        for lat, lng in ((-2.3927, 13.5882), (4.05, 9.70), (-4.27, 15.28)):
            self.assertFalse(self.b.allows(lat, lng), (lat, lng))

    def test_tolerance(self):
        self.assertTrue(self.b.allows(1.4397, 13.22687))       # about 150 m out
        self.assertFalse(self.b.allows(1.22136, 14.30894))     # about 285 m out
        self.assertTrue(self.b.allows(1.22136, 14.30829))      # about 220 m out

if __name__ == '__main__':
    unittest.main()
