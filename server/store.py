"""The SQLite store: import of the published registry, its export in the same
format, and the queries of the API.

Every registry column is kept as the exact text published, so an export of an
imported registry reproduces each file byte for byte (uncompressed). Numeric
copies of the number and the entrance serve the indexes.
"""
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import os
import sqlite3
import threading
import unicodedata

from . import register as R

CODE_COLS = ['machine', 'home', 'written', 'zone', 'official_name', 'number', 'check', 'status', 'issued', 'issued_at',
             'entrance_lat', 'entrance_lng', 'entrance_kind', 'spot_code', 'official_address', 'class', 'use', 'kind',
             'structures', 'floor_area_m2', 'rule', 'estate']
AREA_COLS = ['zone', 'id', 'plate_name', 'official_name', 'zone_name', 'name_key', 'name_id', 'digits', 'blocks',
             'provisional_name', 'compounds', 'alert_zone', 'place_lat', 'place_lon', 'frame']
SCHEMA_VERSION = '1'
GRID = 1000  # integer grid of 0.001 degree cells, when SQLite has no R*Tree


class RegistryError(Exception):
    pass


def now_utc():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def rfc3339(t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def fold(text):
    """Case, accents, punctuation and spacing folded: how an official address is matched."""
    t = unicodedata.normalize('NFKD', text or '')
    t = ''.join(c for c in t if not unicodedata.combining(c)).lower()
    t = ''.join(c if c.isalnum() else ' ' for c in t)
    return ' '.join(t.split())


# ---------------------------------------------------------------- CSV in the published format

def _needs_quotes(field):
    if field == '':
        return False
    if field == '\\.':
        return True
    if any(c in field for c in ',"\r\n'):
        return True
    return field[0].isspace()


def csv_line(fields):
    """One CSV record exactly as the issuer writes it (RFC 4180, LF line ends,
    a field quoted only when it must be)."""
    out = []
    for f in fields:
        f = str(f)
        out.append('"' + f.replace('"', '""') + '"' if _needs_quotes(f) else f)
    return ','.join(out) + '\n'


class _Hashing(io.RawIOBase):
    """A readable stream that hashes what it hands on (the uncompressed bytes)."""

    def __init__(self, raw):
        self.raw, self.sha = raw, hashlib.sha256()

    def readable(self):
        return True

    def readinto(self, b):
        data = self.raw.read(len(b))
        n = len(data)
        b[:n] = data
        self.sha.update(data)
        return n


def _rows(path):
    """(hasher, csv reader) over a .csv.gz file."""
    h = _Hashing(gzip.open(path, 'rb'))
    text = io.TextIOWrapper(io.BufferedReader(h, 1 << 20), encoding='utf-8', newline='')
    return h, csv.reader(text)


# ---------------------------------------------------------------- schema

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS areas (
  ord INTEGER NOT NULL, key TEXT PRIMARY KEY, id INTEGER NOT NULL UNIQUE, zone TEXT NOT NULL,
  plate_name TEXT, official_name TEXT, zone_name TEXT, name_key TEXT, name_id INTEGER, digits TEXT, blocks TEXT,
  provisional_name TEXT, compounds TEXT, alert_zone TEXT, place_lat TEXT, place_lon TEXT, frame TEXT);
CREATE TABLE IF NOT EXISTS codes (
  id INTEGER PRIMARY KEY,
  machine TEXT NOT NULL UNIQUE, home TEXT NOT NULL, written TEXT, zone TEXT NOT NULL, official_name TEXT,
  number TEXT NOT NULL, "check" TEXT, status TEXT NOT NULL, issued TEXT, issued_at TEXT,
  entrance_lat TEXT, entrance_lng TEXT, entrance_kind TEXT, spot_code TEXT, official_address TEXT,
  class TEXT, use TEXT, kind TEXT, structures TEXT, floor_area_m2 TEXT, rule TEXT, estate TEXT,
  unit TEXT NOT NULL, name_id INTEGER NOT NULL, num INTEGER NOT NULL,
  lat REAL NOT NULL, lng REAL NOT NULL, anchor_lat REAL NOT NULL, anchor_lng REAL NOT NULL,
  address_key TEXT, outline TEXT, issued_by TEXT, changed_at TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS codes_name_number ON codes (name_id, num);
CREATE INDEX IF NOT EXISTS codes_home ON codes (home);
CREATE INDEX IF NOT EXISTS codes_address ON codes (address_key) WHERE address_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS codes_zone_number ON codes (zone, num);
CREATE INDEX IF NOT EXISTS codes_unit ON codes (unit, machine);
CREATE INDEX IF NOT EXISTS codes_issued_by ON codes (issued_by, issued_at) WHERE issued_by IS NOT NULL;
CREATE TABLE IF NOT EXISTS journal (seq INTEGER PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL,
  machine TEXT NOT NULL, detail TEXT NOT NULL);
"""


def has_rtree(con):
    try:
        con.execute('CREATE VIRTUAL TABLE IF NOT EXISTS temp.rtree_probe USING rtree(id, a, b, c, d)')
        con.execute('DROP TABLE temp.rtree_probe')
        return True
    except sqlite3.OperationalError:
        return False


def connect(path, readonly=False):
    if readonly:
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True, check_same_thread=False, timeout=30)
    else:
        con = sqlite3.connect(path, check_same_thread=False, timeout=30, isolation_level=None)
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA synchronous=NORMAL')
    con.execute('PRAGMA foreign_keys=ON')
    con.row_factory = sqlite3.Row
    return con


def _spatial_schema(con):
    if has_rtree(con):
        con.execute('CREATE VIRTUAL TABLE IF NOT EXISTS codes_rtree USING rtree(id, min_lat, max_lat, min_lng, max_lng)')
        return 'rtree'
    con.execute('CREATE TABLE IF NOT EXISTS codes_grid (cell INTEGER NOT NULL, id INTEGER NOT NULL, PRIMARY KEY (cell, id)) WITHOUT ROWID')
    return 'grid'


def grid_cell(lat, lng):
    return int((lat + 90) * GRID) * 1000000 + int((lng + 180) * GRID)


def put_spatial(con, kind, rid, lat, lng, delete=False):
    if kind == 'rtree':
        if delete:
            con.execute('DELETE FROM codes_rtree WHERE id = ?', (rid,))
        con.execute('INSERT INTO codes_rtree VALUES (?, ?, ?, ?, ?)', (rid, lat, lat, lng, lng))
    else:
        if delete:
            con.execute('DELETE FROM codes_grid WHERE id = ?', (rid,))
        con.execute('INSERT INTO codes_grid VALUES (?, ?)', (grid_cell(lat, lng), rid))


# ---------------------------------------------------------------- import

def read_manifest(registry):
    p = os.path.join(registry, 'MANIFEST.json')
    if not os.path.exists(p):
        raise RegistryError(f'{p} is missing: not a registry folder')
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def local_changes(db):
    """Codes issued or changed by this deployment (its journal), or 0 without a database."""
    if not os.path.exists(db):
        return 0
    con = connect(db, readonly=True)
    try:
        return con.execute('SELECT count(*) FROM journal').fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        con.close()


def import_registry(registry, db, replace=False, log=print):
    """Load every file of a registry folder into a new database, verify each
    file's SHA-256 and the totals against MANIFEST.json, then swap it in for
    ``db``. Refuses a mismatch, and refuses to drop codes this deployment
    issued or changed unless ``replace``. Returns the number of codes."""
    man = read_manifest(registry)
    if man.get('country') != R.COUNTRY:
        raise RegistryError(f'the registry is for {man.get("country")!r}, this server for {R.COUNTRY}')
    if os.path.exists(db) and not replace:
        n = local_changes(db)
        if n:
            raise RegistryError(f'{db} holds {n} change(s) made here (issued codes, statuses, entrances). '
                                'Export it first, or pass --replace to drop them.')
        cur = _meta(db)
        if cur.get('manifest') == json.dumps(man, sort_keys=True) and cur.get('complete') == 'yes':
            log(f'{db} already holds this registry ({cur.get("codes")} codes): nothing to do.')
            return int(cur.get('codes', 0))
    reg = R.Register()
    want = man.get('sha256', {})
    tmp = db + '.importing'
    for p in (tmp, tmp + '-wal', tmp + '-shm'):
        if os.path.exists(p):
            os.remove(p)
    os.makedirs(os.path.dirname(os.path.abspath(db)), exist_ok=True)
    con = connect(tmp)
    try:
        con.executescript(SCHEMA)
        kind = _spatial_schema(con)
        con.execute('BEGIN')
        # the area table
        h, rows = _rows(os.path.join(registry, 'areas.csv.gz'))
        if next(rows) != AREA_COLS:
            raise RegistryError('areas.csv: unexpected columns')
        n_areas = 0
        for i, r in enumerate(rows):
            d = dict(zip(AREA_COLS, r))
            a = reg.by_key.get(d['zone'])
            if a is None or a.id != int(d['id']) or a.name_id != int(d['name_id']) or a.name_key != d['name_key']:
                raise RegistryError(f'areas.csv: area {d["zone"]} disagrees with engine/data/register.json')
            con.execute('INSERT INTO areas VALUES (' + ','.join('?' * 17) + ')',
                        [i, d['zone'], int(d['id']), a.zone] + [d[c] for c in AREA_COLS[2:]])
            n_areas += 1
        if h.sha.hexdigest() != want.get('areas.csv'):
            raise RegistryError('areas.csv: SHA-256 does not match MANIFEST.json')
        area_of = {k: (a.zone, a.name_id) for k, a in reg.by_key.items()}
        # one file per département
        total, by_unit = 0, {}
        units = sorted(f[:-7] for f in os.listdir(registry) if f.endswith('.csv.gz') and f != 'areas.csv.gz')
        if set(units) != set(man.get('byUnit', {})):
            raise RegistryError(f'files {sorted(set(units) ^ set(man.get("byUnit", {})))} disagree with MANIFEST.json')
        ins = ('INSERT INTO codes (' + ','.join(f'"{c}"' for c in CODE_COLS) +
               ', unit, name_id, num, lat, lng, anchor_lat, anchor_lng, address_key) VALUES (' + ','.join('?' * 30) + ')')
        for unit in units:
            h, rows = _rows(os.path.join(registry, unit + '.csv.gz'))
            if next(rows) != CODE_COLS:
                raise RegistryError(f'{unit}.csv: unexpected columns')
            batch, n = [], 0
            for r in rows:
                zone, name_id = area_of.get(r[3], (None, None))
                if zone != unit:
                    raise RegistryError(f'{unit}.csv: {r[0]} is in area {r[3]}, not in this département')
                lat, lng = float(r[10]), float(r[11])
                batch.append(r + [unit, name_id, int(r[5]), lat, lng, lat, lng, fold(r[14]) or None])
                n += 1
                if len(batch) == 5000:
                    _insert_batch(con, ins, kind, batch)
                    batch = []
            _insert_batch(con, ins, kind, batch)
            if h.sha.hexdigest() != want.get(unit + '.csv'):
                raise RegistryError(f'{unit}.csv: SHA-256 does not match MANIFEST.json')
            if n != man['byUnit'][unit]:
                raise RegistryError(f'{unit}.csv: {n} codes, MANIFEST.json says {man["byUnit"][unit]}')
            by_unit[unit] = n
            total += n
            log(f'  {unit}: {n} codes')
        if total != man.get('codes'):
            raise RegistryError(f'{total} codes in the files, MANIFEST.json says {man.get("codes")}')
        meta = {'country': R.COUNTRY, 'schema': SCHEMA_VERSION, 'spatial': kind, 'manifest': json.dumps(man, sort_keys=True),
                'exported': man.get('exported', ''), 'codes': str(total), 'areas': str(n_areas),
                'imported_at': rfc3339(now_utc()), 'complete': 'yes'}
        con.executemany('INSERT OR REPLACE INTO meta VALUES (?, ?)', meta.items())
        con.execute('COMMIT')
        con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        con.execute('ANALYZE')
    except BaseException:
        # a refused or interrupted import leaves nothing behind
        con.close()
        for p in (tmp, tmp + '-wal', tmp + '-shm'):
            if os.path.exists(p):
                os.remove(p)
        raise
    con.close()
    for suffix in ('-wal', '-shm'):
        if os.path.exists(db + suffix):
            os.remove(db + suffix)
    os.replace(tmp, db)
    for suffix in ('-wal', '-shm'):
        if os.path.exists(tmp + suffix):
            os.remove(tmp + suffix)
    log(f'{total} codes in {len(units)} département{"s" if len(units) != 1 else ""}, {n_areas} areas: {db}')
    return total


def _insert_batch(con, ins, kind, batch):
    if not batch:
        return
    con.executemany(ins, batch)
    last = con.execute('SELECT last_insert_rowid()').fetchone()[0]
    first = last - len(batch) + 1
    if kind == 'rtree':
        con.executemany('INSERT INTO codes_rtree VALUES (?, ?, ?, ?, ?)',
                        [(first + i, r[25], r[25], r[26], r[26]) for i, r in enumerate(batch)])
    else:
        con.executemany('INSERT INTO codes_grid VALUES (?, ?)',
                        [(grid_cell(r[25], r[26]), first + i) for i, r in enumerate(batch)])


def _meta(db):
    try:
        con = connect(db, readonly=True)
        try:
            return {r[0]: r[1] for r in con.execute('SELECT key, value FROM meta')}
        finally:
            con.close()
    except sqlite3.Error:
        return {}


# ---------------------------------------------------------------- export

def export_registry(db, out, log=print):
    """Write the registry as published: areas.csv.gz, one <département>.csv.gz,
    MANIFEST.json (SHA-256 of each file uncompressed). Files are gzipped with no
    name and no time stamp (gzip -n)."""
    con = connect(db, readonly=True)
    os.makedirs(out, exist_ok=True)
    meta = {r[0]: r[1] for r in con.execute('SELECT key, value FROM meta')}
    sha, by_unit, total = {}, {}, 0

    def write(name, header, rows):
        h = hashlib.sha256()
        p = os.path.join(out, name + '.gz')
        with open(p, 'wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=9) as gz:
            buf = []
            for fields in [header] + rows if isinstance(rows, list) else _chain(header, rows):
                line = csv_line(fields).encode('utf-8')
                h.update(line)
                buf.append(line)
                if len(buf) >= 4096:
                    gz.write(b''.join(buf))
                    buf = []
            gz.write(b''.join(buf))
        sha[name] = h.hexdigest()

    area_rows = [[r['key'], str(r['id'])] + [r[c] for c in AREA_COLS[2:]] for r in con.execute('SELECT * FROM areas ORDER BY ord')]
    write('areas.csv', AREA_COLS, area_rows)
    units = sorted({r[0] for r in con.execute('SELECT DISTINCT zone FROM areas')})
    cols = ','.join(f'"{c}"' for c in CODE_COLS)
    for unit in units:
        n = con.execute('SELECT count(*) FROM codes WHERE unit = ?', (unit,)).fetchone()[0]
        if n == 0:
            continue
        rows = ([str(v) for v in r] for r in con.execute(f'SELECT {cols} FROM codes WHERE unit = ? ORDER BY name_id, num', (unit,)))
        write(unit + '.csv', CODE_COLS, rows)
        by_unit[unit] = n
        total += n
        log(f'  {unit}: {n} codes')
    last = con.execute('SELECT max(at) FROM journal').fetchone()[0]
    exported = max(filter(None, [meta.get('exported', ''), last])) if (meta.get('exported') or last) else rfc3339(now_utc())
    man = {'byUnit': by_unit, 'codes': total, 'country': R.COUNTRY, 'credit': R.CREDIT, 'engine': R.ENGINE,
           'exported': exported, 'licence': R.LICENCES['data'], 'sha256': dict(sorted(sha.items()))}
    with open(os.path.join(out, 'MANIFEST.json'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(man, sort_keys=True, indent=2, ensure_ascii=False) + '\n')
    con.close()
    log(f'{total} codes in {len(by_unit)} département{"s" if len(by_unit) != 1 else ""}: {out}')
    return total


def backup(db, out, log=print):
    """A consistent copy of the database (SQLite online backup), safe while serving."""
    if os.path.exists(out):
        raise RegistryError(f'{out} exists: choose a new file')
    src = connect(db, readonly=True)
    dst = sqlite3.connect(out)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    log(f'{db} copied to {out}')


def _chain(header, rows):
    yield header
    yield from rows


# ---------------------------------------------------------------- the open database

class Store:
    """Per-thread connections to one database; writes are serialised."""

    def __init__(self, path):
        if not os.path.exists(path):
            raise RegistryError(f'{path} does not exist: run `python3 -m server import` first')
        self.path = path
        self.local = threading.local()
        self.write_lock = threading.Lock()
        self.pool_lock = threading.Lock()
        self.pool, self.all = [], []
        meta = self.meta()
        if meta.get('complete') != 'yes' or meta.get('country') != R.COUNTRY:
            raise RegistryError(f'{path} is not a complete {R.COUNTRY} registry database')
        self.spatial = meta.get('spatial', 'grid')

    def con(self):
        """The connection of the current request (from the pool, until release())."""
        c = getattr(self.local, 'con', None)
        if c is None:
            with self.pool_lock:
                c = self.pool.pop() if self.pool else None
            if c is None:
                c = connect(self.path)
                with self.pool_lock:
                    self.all.append(c)
            self.local.con = c
        return c

    def release(self):
        c = getattr(self.local, 'con', None)
        if c is not None:
            self.local.con = None
            with self.pool_lock:
                self.pool.append(c)

    def close(self):
        with self.pool_lock:
            for c in self.all:
                c.close()
            self.all, self.pool = [], []

    def meta(self):
        c = connect(self.path, readonly=True)
        try:
            return {r[0]: r[1] for r in c.execute('SELECT key, value FROM meta')}
        finally:
            c.close()

    def blocks(self):
        return {r['key']: R.parse_blocks(r['blocks']) for r in self.con().execute('SELECT key, blocks FROM areas')}

    def code(self, machine):
        return self.con().execute('SELECT * FROM codes WHERE machine = ?', (machine,)).fetchone()

    def code_by_number(self, name_id, number):
        return self.con().execute('SELECT * FROM codes WHERE name_id = ? AND num = ?', (name_id, number)).fetchone()

    def codes_by_address(self, text, limit):
        key = fold(text)
        if not key:
            return 0, []
        c = self.con()
        n = c.execute('SELECT count(*) FROM codes WHERE address_key = ? AND status <> \'retired\'', (key,)).fetchone()[0]
        rows = c.execute('SELECT * FROM codes WHERE address_key = ? AND status <> \'retired\' ORDER BY machine LIMIT ?',
                         (key, limit)).fetchall()
        return n, rows

    NEAR_COLS = ('codes.id, machine, home, written, status, zone, entrance_lat, entrance_lng, entrance_kind, '
                 'official_address, lat, lng, outline')

    def near(self, lat, lng, metres, live_only=True, outlines_only=False):
        """Codes whose entrance lies within ``metres`` of the point, nearest first:
        [(distance, row)], each row with the columns of NEAR_COLS."""
        from . import geo
        a, b, c0, d = geo.box_around(lat, lng, metres)
        con = self.con()
        extra = ' AND codes.outline IS NOT NULL' if outlines_only else ''
        if self.spatial == 'rtree':
            rows = con.execute(f'SELECT {self.NEAR_COLS} FROM codes_rtree JOIN codes ON codes.id = codes_rtree.id '
                               'WHERE min_lat >= ? AND max_lat <= ? AND min_lng >= ? AND max_lng <= ?' + extra,
                               (a, b, c0, d)).fetchall()
        else:
            cells = [int((la + 90) * GRID) * 1000000 + int((ln + 180) * GRID)
                     for la in _steps(a, b) for ln in _steps(c0, d)]
            rows = []
            for i in range(0, len(cells), 500):
                part = cells[i:i + 500]
                rows += con.execute(f'SELECT {self.NEAR_COLS} FROM codes_grid JOIN codes ON codes.id = codes_grid.id WHERE cell IN (' +
                                    ','.join('?' * len(part)) + ')' + extra, part).fetchall()
        out = []
        for r in rows:
            if live_only and r['status'] == 'retired':
                continue
            dist = geo.ground_m(lat, lng, r['lat'], r['lng'])
            if dist <= metres:
                out.append((dist, r))
        out.sort(key=lambda x: (x[0], x[1]['machine']))
        return out

    def nearest(self, lat, lng, metres):
        """The live code whose entrance is nearest the point within ``metres``: (distance, row),
        else (None, None). Searches widen step by step, so a dense city costs little."""
        r = min(10.0, metres)
        while True:
            hits = self.near(lat, lng, r)
            if hits:
                return hits[0]
            if r >= metres:
                return None, None
            r = min(metres, r * 3)

    def area_numbers(self, area_key):
        """Every number of an area, retired ones included: [(key, anchor lat, anchor lng, number)]."""
        return [(r[0], r[1], r[2], r[3]) for r in self.con().execute(
            'SELECT machine, anchor_lat, anchor_lng, num FROM codes WHERE zone = ?', (area_key,))]

    def issued_by_since(self, who, since):
        return self.con().execute('SELECT count(*) FROM codes WHERE issued_by = ? AND issued_at >= ?', (who, since)).fetchone()[0]

    def counts(self):
        con = self.con()
        by_unit = {r[0]: r[1] for r in con.execute('SELECT unit, count(*) FROM codes GROUP BY unit')}
        by_status = {r[0]: r[1] for r in con.execute('SELECT status, count(*) FROM codes GROUP BY status')}
        by_issued = {r[0]: r[1] for r in con.execute('SELECT issued, count(*) FROM codes GROUP BY issued')}
        return by_unit, by_status, by_issued

    def area_counts(self, area_keys=None):
        con = self.con()
        if area_keys is None:
            q = con.execute('SELECT zone, count(*) FROM codes GROUP BY zone')
        else:
            q = con.execute('SELECT zone, count(*) FROM codes WHERE zone IN (' + ','.join('?' * len(area_keys)) + ') GROUP BY zone',
                            list(area_keys))
        return {r[0]: r[1] for r in q}

    def area_rows(self):
        return {r['key']: r for r in self.con().execute('SELECT * FROM areas')}

    def page(self, unit, after, limit):
        return self.con().execute('SELECT * FROM codes WHERE unit = ? AND machine > ? ORDER BY machine LIMIT ?',
                                  (unit, after, limit)).fetchall()

    def outlines_near(self, lat, lng, metres=150.0):
        """Codes issued here with an outline, near a point: [(row, ring)]."""
        return [(r, json.loads(r['outline'])) for _d, r in self.near(lat, lng, metres, outlines_only=True)]

    # writes (the caller holds write_lock)

    def add_code(self, fields, extra, new_blocks, who, area_key, blocks_after):
        con = self.con()
        con.execute('BEGIN IMMEDIATE')
        try:
            if new_blocks:
                con.execute('UPDATE areas SET blocks = ? WHERE key = ?', (R.blocks_text(blocks_after), area_key))
            cols = CODE_COLS + list(extra)
            cur = con.execute('INSERT INTO codes (' + ','.join(f'"{c}"' for c in cols) + ') VALUES (' + ','.join('?' * len(cols)) + ')',
                              [fields[c] for c in CODE_COLS] + list(extra.values()))
            put_spatial(con, self.spatial, cur.lastrowid, extra['lat'], extra['lng'])
            detail = {'blocks': [list(b) for b in new_blocks]} if new_blocks else {}
            con.execute('INSERT INTO journal (at, action, machine, detail) VALUES (?, ?, ?, ?)',
                        (fields['issued_at'], 'issue', fields['machine'], json.dumps(detail)))
            con.execute('COMMIT')
        except Exception:
            con.execute('ROLLBACK')
            raise

    def change_code(self, machine, sets, action, detail, at):
        con = self.con()
        con.execute('BEGIN IMMEDIATE')
        try:
            cols = list(sets)
            con.execute('UPDATE codes SET ' + ', '.join(f'"{c}" = ?' for c in cols) + ', changed_at = ? WHERE machine = ?',
                        [sets[c] for c in cols] + [at, machine])
            if 'lat' in sets:
                rid = con.execute('SELECT id FROM codes WHERE machine = ?', (machine,)).fetchone()[0]
                put_spatial(con, self.spatial, rid, sets['lat'], sets['lng'], delete=True)
            con.execute('INSERT INTO journal (at, action, machine, detail) VALUES (?, ?, ?, ?)',
                        (at, action, machine, json.dumps(detail)))
            con.execute('COMMIT')
        except Exception:
            con.execute('ROLLBACK')
            raise


def _steps(lo, hi):
    a, b = int((lo + 180) * GRID), int((hi + 180) * GRID)
    return [x / GRID - 180 + 0.5 / GRID for x in range(a, b + 1)]
