"""N-Ways Addressing for Gabon: the registry server.

  python3 -m server import --registry registry --db data/addresses.sqlite [--replace]
  python3 -m server serve  --db data/addresses.sqlite --port 8080
  python3 -m server export --db data/addresses.sqlite --out <folder>
  python3 -m server backup --db data/addresses.sqlite --out <file>   (a consistent copy while serving)
  python3 -m server start  (import the bundled registry when the database is missing, then serve)

Configuration (environment; flags win): ADDRESSES_DB, REGISTRY_DIR, HOST, PORT,
ISSUE_KEYS (comma-separated bearer keys; none = read-only), ISSUE_PER_DAY,
CORS_ORIGINS (comma-separated origins, or *).
"""
import argparse
import os
import signal
import sys
import threading

from . import store as S
from .register import ROOT


def _env_list(name):
    return [x.strip() for x in os.environ.get(name, '').split(',') if x.strip()]


def _serve(db, host, port):
    from .api import make_server
    from .service import Service
    keys = _env_list('ISSUE_KEYS')
    per_day = int(os.environ.get('ISSUE_PER_DAY', '5'))
    svc = Service(S.Store(db), keys, per_day)
    srv = make_server(svc, host, port, _env_list('CORS_ORIGINS'))
    mode = f'issuing ({len(keys)} key(s), {per_day} codes per key per day)' if keys else 'read-only'
    print(f'N-Ways Addressing for Gabon: {db} on http://{host}:{port}/v1, {mode}', file=sys.stderr, flush=True)

    def stop(*_):
        threading.Thread(target=srv.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    srv.serve_forever()
    srv.server_close()


def main(argv=None):
    p = argparse.ArgumentParser(prog='python3 -m server', description='N-Ways Addressing for Gabon: registry server')
    sub = p.add_subparsers(dest='cmd', required=True)
    db_default = os.environ.get('ADDRESSES_DB', os.path.join('data', 'addresses.sqlite'))
    reg_default = os.environ.get('REGISTRY_DIR', os.path.join(ROOT, 'registry'))
    i = sub.add_parser('import', help='load a registry folder into the database')
    i.add_argument('--registry', default=reg_default)
    i.add_argument('--db', default=db_default)
    i.add_argument('--replace', action='store_true', help='drop codes issued or changed by this deployment')
    s = sub.add_parser('serve', help='serve the API')
    s.add_argument('--db', default=db_default)
    s.add_argument('--host', default=os.environ.get('HOST', '127.0.0.1'))
    s.add_argument('--port', type=int, default=int(os.environ.get('PORT', '8080')))
    e = sub.add_parser('export', help='write the registry in the published format')
    e.add_argument('--db', default=db_default)
    e.add_argument('--out', required=True)
    b = sub.add_parser('backup', help='copy the database consistently, even while it serves')
    b.add_argument('--db', default=db_default)
    b.add_argument('--out', required=True)
    st = sub.add_parser('start', help='import the registry if the database is missing, then serve')
    st.add_argument('--db', default=db_default)
    st.add_argument('--registry', default=reg_default)
    st.add_argument('--host', default=os.environ.get('HOST', '0.0.0.0'))
    st.add_argument('--port', type=int, default=int(os.environ.get('PORT', '8080')))
    a = p.parse_args(argv)
    try:
        if a.cmd == 'import':
            S.import_registry(a.registry, a.db, replace=a.replace)
        elif a.cmd == 'export':
            S.export_registry(a.db, a.out)
        elif a.cmd == 'backup':
            S.backup(a.db, a.out)
        elif a.cmd == 'serve':
            _serve(a.db, a.host, a.port)
        elif a.cmd == 'start':
            if not os.path.exists(a.db) or S._meta(a.db).get('complete') != 'yes':
                print(f'First start: importing {a.registry} into {a.db}', file=sys.stderr, flush=True)
                S.import_registry(a.registry, a.db, log=lambda m: print(m, file=sys.stderr, flush=True))
            _serve(a.db, a.host, a.port)
    except S.RegistryError as err:
        print(f'error: {err}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
