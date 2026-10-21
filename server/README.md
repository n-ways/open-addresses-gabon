# The registry server

A ready-made HTTP service for Gabon's N-Ways addresses. It serves every code of the published registry ([`registry/`](../registry/)) through a JSON API, and, where it is designated as the country's issuer, gives new compounds their codes by the same rules as the N-Ways issuer. A ministry, a post office, a municipality or a developer can run it without touching the code: a deployment answers exactly what the published registry says, code for code.

- Python 3.9 or newer, standard library only (SQLite, `http.server`); nothing to install.
- The parsing, check digits, spot codes, name keys and the Hilbert curve are those of the reference engine ([`engine/reference/ga_engine.py`](../engine/reference/ga_engine.py)); the server does not reimplement them.
- Every endpoint, with a real request and its real response: [docs/api.md](../docs/api.md). The contract: [openapi.yaml](openapi.yaml) (OpenAPI 3.1).

## Deploy

### With Docker (one command)

```sh
cd server
docker compose up -d
curl -s http://localhost:8080/v1/health
```

On its first start the container imports the registry bundled in the image into the `addresses-data` volume (665,089 codes, about 10 seconds and 310 MB), checking every file against `MANIFEST.json`, then serves `http://localhost:8080/v1`. Later starts serve the volume at once. The image is `python:3.12-slim`, runs as an unprivileged user and has a health check on `/v1/health`.

Settings go in the environment or in a `.env` file beside `docker-compose.yml`:

```sh
PORT=8080              # port on the host
ISSUE_KEYS=            # empty: read-only (see "One issuer" below)
ISSUE_PER_DAY=5
CORS_ORIGINS=*
```

### With Python

```sh
python3 -m server import --registry registry --db data/addresses.sqlite
python3 -m server serve --db data/addresses.sqlite --port 8080
```

Run both from the repository root. `serve` listens on 127.0.0.1 unless `--host` (or `HOST`) says otherwise. `python3 -m server start` does both: it imports the registry when the database is missing, then serves on 0.0.0.0.

To keep it running, use the system's service manager. A systemd unit, for example:

```ini
[Unit]
Description=N-Ways Addressing for Gabon
After=network.target

[Service]
User=addresses
WorkingDirectory=/srv/open-addresses-gabon
Environment=ADDRESSES_DB=/var/lib/addresses/addresses.sqlite PORT=8080
ExecStart=/usr/bin/python3 -m server start --host 127.0.0.1
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Behind a reverse proxy with TLS

The server speaks plain HTTP; put it behind a proxy that holds the certificate. With Caddy, which obtains and renews the certificate itself:

```
adresses.example.ga {
    reverse_proxy 127.0.0.1:8080
}
```

With nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name adresses.example.ga;
    ssl_certificate     /etc/letsencrypt/live/adresses.example.ga/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/adresses.example.ga/privkey.pem;
    client_max_body_size 64k;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

Keep the server's own port closed to the outside (bind it to 127.0.0.1, or publish the container port on 127.0.0.1 only: `"127.0.0.1:8080:8080"`). Issuing keys travel in the `Authorization` header and must only ever cross TLS.

## Configure

| Variable | Default | Meaning |
|---|---|---|
| `ADDRESSES_DB` | `data/addresses.sqlite` (`/data/addresses.sqlite` in Docker) | the database file |
| `REGISTRY_DIR` | `registry/` of this repository | the registry that `import` and `start` load |
| `HOST`, `PORT` | `127.0.0.1` (`0.0.0.0` for `start`), `8080` | where to listen |
| `ISSUE_KEYS` | empty | comma-separated bearer keys allowed to issue and change codes; empty means read-only |
| `ISSUE_PER_DAY` | `5` | codes each key may issue in any 24 hours (the N-Ways app allows 5 per phone; a registry office will want more) |
| `CORS_ORIGINS` | empty (Docker: `*`) | origins allowed to call the API from a browser, comma-separated, or `*` |

Make each key long and random (`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`), give each office or system its own, and remove a key from the list to revoke it. The database records, for every code issued here, which key issued it (as a hash, never the key).

## Back up

The database is one SQLite file in WAL mode. Copy it consistently, even while the server runs:

```sh
python3 -m server backup --db data/addresses.sqlite --out backups/addresses-$(date +%F).sqlite
docker compose exec addresses python3 -m server backup --out /data/backup.sqlite   # in Docker
```

A read-only deployment holds nothing that the published registry does not, so its backup is the registry itself. An issuing deployment must back up every day: its database is then the only record of the codes it issued. Export them in the published format too, so the copy can be read without this software:

```sh
python3 -m server export --db data/addresses.sqlite --out exports/$(date +%F)
```

`export` writes `areas.csv.gz`, one `<département>.csv.gz` and `MANIFEST.json`, with the same columns, order and checksums as the published registry. An export of a freshly imported registry is byte for byte the published one (uncompressed); the tests check this.

## Update to a newer registry

When N-Ways publishes a newer registry, pull this repository (or rebuild the image) and import again:

```sh
git pull
python3 -m server import --registry registry --db data/addresses.sqlite   # then restart the server
# Docker:
docker compose build && docker compose run --rm addresses python3 -m server import && docker compose up -d
```

The import builds a new database beside the old one, checks every file's SHA-256 and every count against `MANIFEST.json`, and only then replaces the old file: a failed or interrupted import leaves the old database in service. Run on the same registry again, it does nothing. It refuses to replace a database that holds codes issued or changed by this deployment: export those first. `--replace` drops them, and is only for a deployment that has handed its codes back to the issuer.

## One issuer

**A code must come from one issuer only.** Numbers are handed out in order from blocks of a national range per name (engine/SPEC.md 2.4 and 6.5): two deployments issuing from the same registry would each see the same free number for the next compound of an area and give it to two different homes. Nothing in either database would show the clash until the two registries met.

So a deployment issues only when the State of Gabon or N-WAYS LIMITED has designated it as the issuer, in writing. Every other deployment runs read-only (no `ISSUE_KEYS`): it answers look-ups and refuses `POST` and `PATCH` with `403 read_only`. Today the issuer is N-WAYS LIMITED, through the N-Ways app and API; when the State designates an office, N-Ways stops issuing for Gabon on the day that office starts, from the registry as it stands that day (`export` of the N-Ways registry, `import` into the office's server). See [GOVERNANCE.md](../GOVERNANCE.md).

## How issue works

`POST /v1/codes` with `{"lat", "lng"}`, and optionally the building's `outline` (`[lng, lat]` points) or `of` (the machine code of the compound this is another door of). The rules are those of the N-Ways issuer, and the tests check them against it case by case ([testdata/parity.json](testdata/parity.json)). A point is in Gabon when a département outline holds it, or, in a gap between outlines (a sliver between départements, the shoreline, an island), when it has a spot code ([SPEC §5](../engine/SPEC.md#5-spot-codes)); any other point is refused (`422 outside`), and `/v1/at` and `/v1/near` answer `404 outside` for it. The border decides: a point more than 300 m outside Gabon's national border (OpenStreetMap admin_level 2, shipped simplified in `engine/data/border.json`) is refused with `422 outside` even when a zone outline or a spot zone reaches it, and an entrance is never moved there ([SPEC §6.1](../engine/SPEC.md#61-inputs)).

1. **Already coded.** A new code is refused (`409 exists`, with the existing card) when a live compound's entrance lies within 3 m of the point, when the point lies inside an outline issued here, or when the outline covers a compound's centre or overlaps an outline issued here.
2. **Outline.** Between 6 m² and 2 ha (`422 bad_outline`).
3. **Area.** The area of the nearest issued code within 250 m, so a new house joins its neighbours; else the code area of the point (the nearest named place of its département); else the nearest area that gives numbers. Another door takes its compound's area, and must be within 80 m of its entrance (`422 too_far`).
4. **Number.** Between the new compound's two neighbours on the area's Hilbert curve, the free number nearest their midpoint, below the tail reserve (the last third of the area's first block); else the lowest free number of the tail reserve; else of the area's later blocks; else a new block of `max(20, 2 × compounds rounded up to ten)` numbers from the name's national spare, above every block already given. A number is never reused, retired ones included.
5. **Forms.** The machine form with its Damm check digit, the remembered form (plate name and number), its written grouping; `status: provisional`, `issued: on-demand`.
6. **Limit.** `ISSUE_PER_DAY` codes per key in any 24 hours (`429 limit`).

New blocks are stored in the area table and appear in `export`. `PATCH /v1/codes/{machine}` confirms a code (`provisional` → `confirmed`), retires it (for good: a retired code never comes back and its number is never given again), or moves its entrance to the real gate or door, at most 80 m away.

**What the published data does not carry.** The registry publishes each compound's entrance point, not its building outlines. So `GET /v1/at` finds the compound whose entrance is within 12 m of the point; the N-Ways service, which also holds the outlines, finds a compound from anywhere inside its buildings. A point inside a large building more than 12 m from its entrance answers `none`, with the nearest code beside it. Outlines posted to this server are kept and used.

## Test

```sh
python3 -m unittest discover -s server/tests -t .
```

The tests run on a small real registry, the département of Ogooué-Létili (`2OL`, 685 codes, [testdata/registry/](testdata/registry/)): the import and export round trip, refusal of a tampered or incomplete registry, every endpoint's answers and errors, issue parity with the N-Ways issuer (numbers, forms, extension blocks, the duplicate checks), outlines, doors, status changes, keys and limits.
