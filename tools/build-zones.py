#!/usr/bin/env python3
"""Build Gabon's code zones (model/zones.json, model/zones.geojson).

A zone is a département (OpenStreetMap admin_level 6, 49 polygons on
2026-10-18). Its key is the province digit (ISO 3166-2 GA-1..GA-9, the same
number La Poste writes as 01..09 before the town) plus two letters for the
département's chef-lieu. Grid settings are computed once here and then
frozen: a published zone never changes its frame, cell or index.

  tools/build-zones.py STAGED.duckdb ZONE_STATS.json

STAGED.duckdb and ZONE_STATS.json come from tools/stage.py and
tools/analyze.py (see tools/README.md).
"""
import json, math, os, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALPHABET_LEN = 20
SPOT_COLS, SPOT_ROWS = 40000, 32000      # 7 characters: 5^4*4^3 by 4^4*5^3 (landscape)
M_LAT, M_LON = 110574.0, 111320.0

# département (OSM name) -> (key letters, chef-lieu). Keys come from the town people say.
KEYS = {
    'Libreville': ('LV', 'Libreville'), 'Komo-Mondah': ('KM', 'Ntoum'), 'Komo': ('KG', 'Kango'),
    'Komo-Ocèan': ('KO', 'Ndzomoe'), 'Noya': ('NY', 'Cocobeach'),
    'Mpassa': ('FV', 'Franceville'), 'Lebombi Leyou': ('MD', 'Moanda'), 'Lekoni Lekori': ('AK', 'Akiéni'),
    'Plateaux': ('PL', 'Lékoni'), 'Sebe Brikolo': ('OK', 'Okondja'), 'Djoue': ('DJ', 'Onga'),
    'Djouori Agnili': ('BG', 'Bongoville'), 'Bayi Brikolo': ('BB', 'Aboumi'), 'Lekabi Lewolo': ('LW', 'Ngouoni'),
    'Lekoko': ('BK', 'Bakoumba'), 'Ogooué-Létili': ('OL', 'Boumango'),
    'Ogooue Et Lacs': ('LB', 'Lambaréné'), 'Abanga Bigne': ('NJ', 'Ndjolé'),
    'Douya Onoye': ('MU', 'Mouila'), 'Tsamba Magotsi': ('FG', 'Fougamou'), 'Louetsi Wano': ('LE', 'Lébamba'),
    'Boumi Louetsi': ('MB', 'Mbigou'), 'Dola': ('ND', 'Ndendé'), 'Ndolou': ('MJ', 'Mandji'),
    'Ogoulou': ('MM', 'Mimongo'), 'Louetsi Bibaka': ('ML', 'Malinga'), 'Mougalaba': ('GT', 'Guiétsou'),
    'Mougoutsi': ('TC', 'Tchibanga'), 'Basse Banio': ('MY', 'Mayumba'), 'Douigni': ('MO', 'Moabi'),
    'Doutsila': ('MA', 'Mabanda'), 'Haute Banio': ('NI', 'Ndindi'), 'Mongo': ('MG', 'Moulengui-Binza'),
    'Ivindo': ('MK', 'Makokou'), 'Lope': ('BO', 'Booué'), 'Zadie': ('ME', 'Mékambo'), 'Mvoung': ('OV', 'Ovan'),
    'Lolo Bouenguidi': ('KL', 'Koulamoutou'), 'Mouloundou': ('LT', 'Lastoursville'),
    'Lombo-Bouenguidi (Pana)': ('PN', 'Pana'), 'Offoue Onoye': ('IB', 'Iboundji'),
    'Bendje': ('PG', 'Port-Gentil'), 'Etimboue': ('OM', 'Omboué'), 'Ndougou': ('GB', 'Gamba'),
    'Woleu': ('OY', 'Oyem'), 'Département de Ntem': ('BT', 'Bitam'), 'Haut-Ntem': ('MV', 'Minvoul'),
    'Okano': ('MZ', 'Mitzic'), 'Haut-Komo': ('MN', 'Médouneu'),
}


def main(db, stats_path):
    stats = {s['osm']: s for s in json.load(open(stats_path)) if s['level'] == 6}
    rows = subprocess.run(['duckdb', db, '-json'], capture_output=True, text=True, check=True, input=
        "LOAD spatial; SELECT osm, ST_AsGeoJSON(ST_SimplifyPreserveTopology(g, 0.0002)) gj FROM admin WHERE level=6;").stdout
    shapes = {r['osm']: (r['gj'] if isinstance(r['gj'], dict) else json.loads(r['gj'])) for r in json.loads(rows)}
    zones, feats = [], []
    order = sorted(stats.values(), key=lambda s: (s['region'], KEYS[s['name']][0]))
    for i, s in enumerate(order):
        letters, town = KEYS[s['name']]
        digit = s['region'].split('-')[1]
        key = digit + letters
        west, south = math.floor(s['w'] * 1000) / 1000, math.floor(s['s'] * 1000) / 1000
        east, north = math.ceil(s['e'] * 1000) / 1000, math.ceil(s['n_'] * 1000) / 1000
        ref_lat = round((south + north) / 2, 3)
        w_m = (east - west) * M_LON * math.cos(math.radians(ref_lat))
        h_m = (north - south) * M_LAT
        orient = 'landscape' if w_m >= h_m else 'portrait'
        cols, rows_ = (SPOT_COLS, SPOT_ROWS) if orient == 'landscape' else (SPOT_ROWS, SPOT_COLS)
        cell = max(3.0, math.ceil(max(w_m / cols, h_m / rows_) * 4) / 4)
        structures = s['buildings']
        clen = 4 if structures * 2 <= ALPHABET_LEN ** 4 else 5
        zones.append({
            'index': i, 'key': key, 'province': s['region'], 'departement': s['name'], 'chefLieu': town,
            'osm': s['osm'], 'areaKm2': s['area_km2'], 'box': [west, south, east, north],
            'grid': {'west': west, 'south': south, 'refLat': ref_lat, 'orient': orient, 'cellMetres': cell},
            'structures2026': structures, 'compoundLength': clen,
        })
        feats.append({'type': 'Feature', 'properties': {'key': key, 'name': s['name']}, 'geometry': shapes[s['osm']]})
    out = {'country': 'GA', 'version': '1.0', 'frozen': True,
           'note': 'Zone index, key, frame and cell are frozen at first issue: a published zone never changes.',
           'zones': zones}
    json.dump(out, open(os.path.join(REPO, 'model', 'zones.json'), 'w'), ensure_ascii=False, indent=1)
    json.dump({'type': 'FeatureCollection', 'features': feats},
              open(os.path.join(REPO, 'model', 'zones.geojson'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print(len(zones), 'zones;', 'cells', sorted({z['grid']['cellMetres'] for z in zones}),
          '; 5-character compounds in', [z['key'] for z in zones if z['compoundLength'] == 5])


if __name__ == '__main__':
    main(*sys.argv[1:3])
