"""HTTP layer: routes, JSON, errors, CORS and the access log."""
import json
import re
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from .service import ApiError

MAX_BODY = 64 * 1024
NEAR_MAX_M = 500.0
NEAR_MAX_N = 100
PAGE_MAX = 1000

ROUTES = []


def route(method, pattern):
    rx = re.compile('^' + re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern) + '$')

    def wrap(fn):
        ROUTES.append((method, rx, fn))
        return fn
    return wrap


def _q(query, name, required=True):
    v = query.get(name, [None])[0]
    if v is None or v.strip() == '':
        if required:
            raise ApiError(400, 'missing_' + name, f'The query parameter {name} is required.')
        return None
    return v


def _float(query, name, required=True, default=None):
    v = _q(query, name, required)
    if v is None:
        return default
    try:
        x = float(v)
    except ValueError:
        raise ApiError(400, 'bad_' + name, f'{name} is a number.')
    if x != x or x in (float('inf'), float('-inf')):
        raise ApiError(400, 'bad_' + name, f'{name} is a number.')
    return x


def _point(query):
    lat, lng = _float(query, 'lat'), _float(query, 'lng')
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ApiError(400, 'bad_point', 'lat is between -90 and 90, lng between -180 and 180.')
    return lat, lng


def _int(query, name, default, lo, hi):
    v = _q(query, name, False)
    if v is None:
        return default
    if not v.isdigit() or not lo <= int(v) <= hi:
        raise ApiError(400, 'bad_' + name, f'{name} is a whole number from {lo} to {hi}.')
    return int(v)


@route('GET', '/v1/health')
def health(svc, h, q, body):
    return 200, svc.health()


@route('GET', '/v1/info')
def info(svc, h, q, body):
    return 200, svc.info()


@route('GET', '/v1/codes/{machine}')
def get_code(svc, h, q, body, machine):
    return 200, svc.get(machine)


@route('GET', '/v1/find')
def find(svc, h, q, body):
    return 200, svc.find(_q(q, 'q'), _int(q, 'limit', 20, 1, 100))


@route('GET', '/v1/at')
def at(svc, h, q, body):
    return 200, svc.at(*_point(q))


@route('GET', '/v1/near')
def near(svc, h, q, body):
    lat, lng = _point(q)
    radius = _float(q, 'radius', False, 100.0)
    if not 0 < radius <= NEAR_MAX_M:
        raise ApiError(400, 'bad_radius', f'radius is in metres, more than 0 and at most {NEAR_MAX_M:.0f}.')
    return 200, svc.near(lat, lng, radius, _int(q, 'limit', NEAR_MAX_N, 1, NEAR_MAX_N))


@route('GET', '/v1/verify')
def verify(svc, h, q, body):
    return 200, svc.verify(_q(q, 'code'))


@route('GET', '/v1/spot')
def spot(svc, h, q, body):
    return 200, svc.spot(*_point(q))


@route('GET', '/v1/spot/decode')
def spot_decode(svc, h, q, body):
    return 200, svc.spot_decode(_q(q, 'code'))


@route('GET', '/v1/zones')
def zones(svc, h, q, body):
    return 200, svc.zones()


@route('GET', '/v1/zones/{key}')
def zone(svc, h, q, body, key):
    return 200, svc.zone(key)


@route('GET', '/v1/zones/{key}/codes')
def zone_codes(svc, h, q, body, key):
    return 200, svc.page(key, _q(q, 'after', False), _int(q, 'limit', 100, 1, PAGE_MAX))


@route('GET', '/v1/areas/{ident}')
def area(svc, h, q, body, ident):
    return 200, svc.area(ident)


@route('GET', '/v1/areas')
def areas(svc, h, q, body):
    return 200, svc.areas_named(_q(q, 'name'))


@route('POST', '/v1/codes')
def issue(svc, h, q, body):
    who = svc.key_id(h.headers.get('Authorization'))
    return 201, svc.issue(body, who)


@route('PATCH', '/v1/codes/{machine}')
def change(svc, h, q, body, machine):
    who = svc.key_id(h.headers.get('Authorization'))
    return 200, svc.change(machine, body, who)


class Handler(BaseHTTPRequestHandler):
    server_version = 'N-Ways-Addresses/1.0'
    sys_version = ''
    protocol_version = 'HTTP/1.1'
    svc = None
    cors = ()

    def log_message(self, fmt, *args):
        pass

    def _send(self, status, obj, started):
        data = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self._cors_headers()
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)
        ms = (time.monotonic() - started) * 1000
        sys.stderr.write(f'{self.log_date_time_string()} {self.client_address[0]} {self.command} {self.path} {status} {ms:.0f}ms\n')

    def _cors_headers(self):
        origin = self.headers.get('Origin')
        if not origin or not self.cors:
            return
        if '*' in self.cors:
            self.send_header('Access-Control-Allow-Origin', '*')
        elif origin in self.cors:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        else:
            return
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.send_header('Access-Control-Max-Age', '600')

    def _handle(self):
        started = time.monotonic()
        try:
            parts = urlsplit(self.path)
            path = parts.path.rstrip('/') or '/'
            query = parse_qs(parts.query, keep_blank_values=True)
            allowed = []
            for method, rx, fn in ROUTES:
                m = rx.match(path)
                if not m:
                    continue
                allowed.append(method)
                if method == self.command or (self.command == 'HEAD' and method == 'GET'):
                    body = None
                    if method in ('POST', 'PATCH'):
                        # Refuse a read-only deployment or a bad key before reading the body.
                        self.svc.key_id(self.headers.get('Authorization'))
                        body = self._body()
                    status, obj = fn(self.svc, self, query, body, **{k: unquote(v) for k, v in m.groupdict().items()})
                    return self._send(status, obj, started)
            if allowed:
                raise ApiError(405, 'method_not_allowed', f'{self.command} is not allowed here; use {", ".join(sorted(set(allowed)))}.')
            raise ApiError(404, 'not_found', f'There is no endpoint {path}; see /v1/info and docs/api.md.')
        except ApiError as e:
            if self.command in ('POST', 'PATCH', 'PUT', 'DELETE'):
                # The body may be unread; a kept-alive connection would read it as the next request.
                self.close_connection = True
            err = {'error': {'code': e.code, 'message': e.message}}
            err.update(e.extra)
            self._send(e.status, err, started)
        except Exception:
            traceback.print_exc()
            self._send(500, {'error': {'code': 'internal', 'message': 'Something went wrong on this server.'}}, started)
        finally:
            self.svc.st.release()

    def _body(self):
        if 'json' not in (self.headers.get('Content-Type') or ''):
            raise ApiError(415, 'unsupported_media_type', 'Send the body as application/json.')
        try:
            n = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            raise ApiError(413, 'too_large', 'The body is at most 64 KB.')
        raw = self.rfile.read(n)
        try:
            return json.loads(raw.decode('utf-8') or 'null')
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(400, 'bad_json', 'The body is not valid JSON.')

    def do_GET(self):
        self._handle()

    def do_HEAD(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_PATCH(self):
        self._handle()

    def do_PUT(self):
        self._handle()

    def do_DELETE(self):
        self._handle()

    def do_OPTIONS(self):
        started = time.monotonic()
        self.send_response(204)
        self._cors_headers()
        self.send_header('Content-Length', '0')
        self.end_headers()
        sys.stderr.write(f'{self.log_date_time_string()} {self.client_address[0]} OPTIONS {self.path} 204 '
                         f'{(time.monotonic() - started) * 1000:.0f}ms\n')


def make_server(svc, host, port, cors=()):
    handler = type('BoundHandler', (Handler,), {'svc': svc, 'cors': tuple(cors)})
    srv = ThreadingHTTPServer((host, port), handler)
    srv.daemon_threads = True
    return srv
