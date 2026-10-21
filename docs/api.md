# The registry API

Every endpoint of the server in [`server/`](../server/README.md), with a real request and the real response, errors included. The responses below were produced by the server running on the complete published registry (665,089 codes); the issue and change examples ran on a test copy, so the codes they create are not in the published registry. The machine-readable contract is [server/openapi.yaml](../server/openapi.yaml) (OpenAPI 3.1).

Conventions:

- Every response is JSON (`application/json; charset=utf-8`) with stable field names.
- Every error has the shape `{"error": {"code": "...", "message": "..."}}` and the matching HTTP status; `code` is stable, `message` is a sentence for people. A refused issue for a building that already has a code also carries `existing`, its card.
- Coordinates are WGS 84 degrees, `lat` then `lng`; outlines are lists of `[lng, lat]` points.
- A machine form is refused, never corrected, when its check digit is wrong. People's forms (`Louis 12 01`) carry no check digit; a system may send one after a hyphen (`Louis 12 01-1`) and it is verified.
- Reading needs no key. `POST /v1/codes` and `PATCH /v1/codes/{machine}` need `Authorization: Bearer <key>` and exist only on the designated issuer's deployment; elsewhere they answer `403 read_only`.
- Long lists are cut in the examples below, marked `... N more`.

| Endpoint | What it answers |
|---|---|
| [`GET /v1/health`](#get-v1health) | liveness, codes served, registry date |
| [`GET /v1/info`](#get-v1info) | the country, zones, counts, licences, credit line, engine |
| [`GET /v1/codes/{machine}`](#get-v1codesmachine) | the full card of a code |
| [`GET /v1/find?q=`](#get-v1findq) | a code from a remembered form, machine form, official address or spot code |
| [`GET /v1/at?lat=&lng=`](#get-v1atlatlng) | the code of the compound at a point |
| [`GET /v1/near?lat=&lng=&radius=`](#get-v1nearlatlngradius) | the codes within a radius |
| [`GET /v1/verify?code=`](#get-v1verifycode) | whether a machine code is valid and issued |
| [`GET /v1/spot?lat=&lng=`](#get-v1spotlatlng), [`GET /v1/spot/decode?code=`](#get-v1spotdecodecode) | spot codes |
| [`GET /v1/zones`](#get-v1zones), [`GET /v1/zones/{key}`](#get-v1zoneskey), [`GET /v1/zones/{key}/codes`](#get-v1zoneskeycodesafterlimit) | the 49 départements, one with its areas, its codes page by page |
| [`GET /v1/areas/{id}`](#get-v1areasid), [`GET /v1/areas?name=`](#get-v1areasname) | an area; the areas of a name |
| [`POST /v1/codes`](#post-v1codes) | issue a code (issuer only) |
| [`PATCH /v1/codes/{machine}`](#patch-v1codesmachine) | confirm, retire, move the entrance (issuer only) |

## GET /v1/health

Liveness and the registry served.

```sh
curl -s 'http://localhost:8080/v1/health'
```

Response `200`:

```json
{
  "status": "ok",
  "country": "GA",
  "codes": 665089,
  "registryExported": "2026-10-21T07:46:20Z",
  "issuing": true
}
```

## GET /v1/info

The country, its zones and counts, licences, credit line and engine.

```sh
curl -s 'http://localhost:8080/v1/info'
```

Response `200`:

```json
{
  "country": "GA",
  "name": "Gabon",
  "codes": 665089,
  "byStatus": {
    "provisional": 665089
  },
  "byIssue": {
    "bulk": 665089
  },
  "zones": [
    {
      "key": "1KG",
      "name": "Komo",
      "region": "GA-1",
      "codes": 8527,
      "areas": 205
    },
    {
      "key": "1KM",
      "name": "Komo-Mondah",
      "region": "GA-1",
      "codes": 123489,
      "areas": 109
    },
    {
      "key": "1KO",
      "name": "Komo-Ocèan",
      "region": "GA-1",
      "codes": 1452,
      "areas": 51
    },
    "... 46 more"
  ],
  "areas": 4922,
  "areasWithCodes": 2932,
  "names": 3737,
  "registryExported": "2026-10-21T07:46:20Z",
  "importedAt": "2026-10-21T13:57:15Z",
  "engine": "internal/addressing/ga (SPEC v1.0)",
  "spec": "engine/SPEC.md",
  "licences": {
    "data": "ODbL 1.0 (LICENSE-DATA)",
    "code": "Apache-2.0 (LICENSE)",
    "documents": "CC BY 4.0 (LICENSE-DOCS)"
  },
  "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)",
  "creditUrl": "https://github.com/n-ways/open-addresses-gabon",
  "issuing": true,
  "issuePerDay": 50,
  "example": {
    "remembered": "Louis 12 01",
    "machine": "GA-1LV-070-1201-1",
    "spot": "GA-1LV E0794 N0757"
  }
}
```

## GET /v1/codes/{machine}

The full card of an issued code: every registry column (`record`), named, with the spot code, Plus Code, area and zone names, and the remembered, written and spoken forms.

```sh
curl -s 'http://localhost:8080/v1/codes/GA-1LV-070-1201-1'
```

Response `200`:

```json
{
  "country": "GA",
  "machine": "GA-1LV-070-1201-1",
  "home": "Louis 1201",
  "written": "Louis 12 01",
  "spoken": "Louis, 12 01",
  "number": 1201,
  "check": 1,
  "status": "provisional",
  "issued": "bulk",
  "issuedAt": "2026-10-21T07:32:20Z",
  "area": {
    "key": "1LV-070",
    "id": 435,
    "plateName": "Louis",
    "officialName": "Louis",
    "provisionalName": false,
    "zone": "1LV",
    "zoneName": "Libreville"
  },
  "zone": {
    "key": "1LV",
    "name": "Libreville",
    "region": "GA-1",
    "index": 3
  },
  "officialAddress": "Avenue Joseph Deemin, Libreville",
  "entrance": {
    "lat": 0.4085002,
    "lng": 9.4314043,
    "kind": "centre"
  },
  "spotCode": "GA-1LV E0794 N0757",
  "plusCode": "6FGFCC5J+CH2",
  "profile": {
    "class": "residential",
    "use": "residential",
    "kind": "building",
    "structures": 1,
    "floorAreaM2": 122.2,
    "rule": "single",
    "estate": null
  },
  "record": {
    "machine": "GA-1LV-070-1201-1",
    "home": "Louis 1201",
    "written": "Louis 12 01",
    "zone": "1LV-070",
    "official_name": "Louis",
    "number": "1201",
    "check": "1",
    "status": "provisional",
    "issued": "bulk",
    "issued_at": "2026-10-21T07:32:20Z",
    "entrance_lat": "0.4085002",
    "entrance_lng": "9.4314043",
    "entrance_kind": "centre",
    "spot_code": "GA-1LV E0794 N0757",
    "official_address": "Avenue Joseph Deemin, Libreville",
    "class": "residential",
    "use": "residential",
    "kind": "building",
    "structures": "1",
    "floor_area_m2": "122.2",
    "rule": "single",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
}
```

A wrong check digit is refused, never corrected.

```sh
curl -s 'http://localhost:8080/v1/codes/GA-1LV-070-1201-7'
```

Response `422`:

```json
{
  "error": {
    "code": "check_digit",
    "message": "The check digit does not match: a digit is wrong or two are swapped."
  }
}
```

The machine form without its check digit is not a card key (use `/v1/find`).

```sh
curl -s 'http://localhost:8080/v1/codes/GA-1LV-070-1201'
```

Response `400`:

```json
{
  "error": {
    "code": "bad_code",
    "message": "A machine code ends with its check digit; use /v1/find to look up a code without it."
  }
}
```

A valid code that no compound has.

```sh
curl -s 'http://localhost:8080/v1/codes/GA-1LV-070-2690-5'
```

Response `404`:

```json
{
  "error": {
    "code": "not_issued",
    "message": "GA-1LV-070-2690-5 is a valid code but no compound has it."
  }
}
```

## GET /v1/find?q=

A remembered form, typed any way: case, accents, spacing, no space at all.

```sh
curl -s 'http://localhost:8080/v1/find?q=louis1201'
```

Response `200`:

```json
{
  "query": "louis1201",
  "kind": "remembered",
  "matches": [
    {
      "country": "GA",
      "machine": "GA-1LV-070-1201-1",
      "home": "Louis 1201",
      "written": "Louis 12 01",
      "spoken": "Louis, 12 01",
      "number": 1201,
      "check": 1,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-21T07:32:20Z",
      "area": {
        "key": "1LV-070",
        "id": 435,
        "plateName": "Louis",
        "officialName": "Louis",
        "provisionalName": false,
        "zone": "1LV",
        "zoneName": "Libreville"
      },
      "zone": {
        "key": "1LV",
        "name": "Libreville",
        "region": "GA-1",
        "index": 3
      },
      "officialAddress": "Avenue Joseph Deemin, Libreville",
      "entrance": {
        "lat": 0.4085002,
        "lng": 9.4314043,
        "kind": "centre"
      },
      "spotCode": "GA-1LV E0794 N0757",
      "plusCode": "6FGFCC5J+CH2",
      "profile": {
        "class": "residential",
        "use": "residential",
        "kind": "building",
        "structures": 1,
        "floorAreaM2": 122.2,
        "rule": "single",
        "estate": null
      },
      "record": {
        "machine": "GA-1LV-070-1201-1",
        "home": "Louis 1201",
        "written": "Louis 12 01",
        "zone": "1LV-070",
        "official_name": "Louis",
        "number": "1201",
        "check": "1",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-21T07:32:20Z",
        "entrance_lat": "0.4085002",
        "entrance_lng": "9.4314043",
        "entrance_kind": "centre",
        "spot_code": "GA-1LV E0794 N0757",
        "official_address": "Avenue Joseph Deemin, Libreville",
        "class": "residential",
        "use": "residential",
        "kind": "building",
        "structures": "1",
        "floor_area_m2": "122.2",
        "rule": "single",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
    }
  ],
  "total": 1
}
```

Five digits, said as a pair and a hundred.

```sh
curl -s 'http://localhost:8080/v1/find?q=Port-Gentil%2012%20181'
```

Response `200`:

```json
{
  "query": "Port-Gentil 12 181",
  "kind": "remembered",
  "matches": [
    {
      "country": "GA",
      "machine": "GA-8PG-042-12181-2",
      "home": "Port-Gentil 12181",
      "written": "Port-Gentil 12 181",
      "spoken": "Port-Gentil, 12 181",
      "number": 12181,
      "check": 2,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-21T07:32:46Z",
      "area": {
        "key": "8PG-042",
        "id": 3900,
        "plateName": "Port-Gentil",
        "officialName": "Grand Village",
        "provisionalName": true,
        "zone": "8PG",
        "zoneName": "Bendje"
      },
      "zone": {
        "key": "8PG",
        "name": "Bendje",
        "region": "GA-8",
        "index": 43
      },
      "officialAddress": null,
      "entrance": {
        "lat": -0.7228848,
        "lng": 8.7862647,
        "kind": "centre"
      },
      "spotCode": "GA-8PG E01071 N07265",
      "plusCode": "6FFC7QGP+RGR",
      "profile": {
        "class": "religious",
        "use": "religious",
        "kind": "building",
        "structures": 1,
        "floorAreaM2": 519.7,
        "rule": "single",
        "estate": null
      },
      "record": {
        "machine": "GA-8PG-042-12181-2",
        "home": "Port-Gentil 12181",
        "written": "Port-Gentil 12 181",
        "zone": "8PG-042",
        "official_name": "Grand Village",
        "number": "12181",
        "check": "2",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-21T07:32:46Z",
        "entrance_lat": "-0.7228848",
        "entrance_lng": "8.7862647",
        "entrance_kind": "centre",
        "spot_code": "GA-8PG E01071 N07265",
        "official_address": "",
        "class": "religious",
        "use": "religious",
        "kind": "building",
        "structures": "1",
        "floor_area_m2": "519.7",
        "rule": "single",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
    }
  ],
  "total": 1
}
```

An official address returns every compound that carries it (`total`), `limit` at a time.

```sh
curl -s 'http://localhost:8080/v1/find?q=avenue%20joseph%20deemin%2C%20libreville&limit=1'
```

Response `200`:

```json
{
  "query": "avenue joseph deemin, libreville",
  "kind": "officialAddress",
  "matches": [
    {
      "country": "GA",
      "machine": "GA-1LV-029-135-6",
      "home": "Rois 135",
      "written": "Rois 135",
      "spoken": "Rois, 135",
      "number": 135,
      "check": 6,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-21T07:32:18Z",
      "area": {
        "key": "1LV-029",
        "id": 394,
        "plateName": "Rois",
        "officialName": "Baie des Rois",
        "provisionalName": false,
        "zone": "1LV",
        "zoneName": "Libreville"
      },
      "zone": {
        "key": "1LV",
        "name": "Libreville",
        "region": "GA-1",
        "index": 3
      },
      "officialAddress": "Avenue Joseph Deemin, Libreville",
      "entrance": {
        "lat": 0.4071128,
        "lng": 9.4315681,
        "kind": "centre"
      },
      "spotCode": "GA-1LV E0796 N0742",
      "plusCode": "6FGFCC4J+RJW",
      "profile": {
        "class": "commercial",
        "use": "commercial",
        "kind": "building",
        "structures": 1,
        "floorAreaM2": 472.4,
        "rule": "single",
        "estate": null
      },
      "record": {
        "machine": "GA-1LV-029-135-6",
        "home": "Rois 135",
        "written": "Rois 135",
        "zone": "1LV-029",
        "official_name": "Baie des Rois",
        "number": "135",
        "check": "6",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-21T07:32:18Z",
        "entrance_lat": "0.4071128",
        "entrance_lng": "9.4315681",
        "entrance_kind": "centre",
        "spot_code": "GA-1LV E0796 N0742",
        "official_address": "Avenue Joseph Deemin, Libreville",
        "class": "commercial",
        "use": "commercial",
        "kind": "building",
        "structures": "1",
        "floor_area_m2": "472.4",
        "rule": "single",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
    }
  ],
  "total": 98
}
```

A spot code finds the compound within 15 m of its cell centre.

```sh
curl -s 'http://localhost:8080/v1/find?q=GA-1LV%20E0794%20N0757'
```

Response `200`:

```json
{
  "query": "GA-1LV E0794 N0757",
  "kind": "spot",
  "matches": [
    {
      "country": "GA",
      "machine": "GA-1LV-070-1201-1",
      "home": "Louis 1201",
      "written": "Louis 12 01",
      "spoken": "Louis, 12 01",
      "number": 1201,
      "check": 1,
      "status": "provisional",
      "issued": "bulk",
      "issuedAt": "2026-10-21T07:32:20Z",
      "area": {
        "key": "1LV-070",
        "id": 435,
        "plateName": "Louis",
        "officialName": "Louis",
        "provisionalName": false,
        "zone": "1LV",
        "zoneName": "Libreville"
      },
      "zone": {
        "key": "1LV",
        "name": "Libreville",
        "region": "GA-1",
        "index": 3
      },
      "officialAddress": "Avenue Joseph Deemin, Libreville",
      "entrance": {
        "lat": 0.4085002,
        "lng": 9.4314043,
        "kind": "centre"
      },
      "spotCode": "GA-1LV E0794 N0757",
      "plusCode": "6FGFCC5J+CH2",
      "profile": {
        "class": "residential",
        "use": "residential",
        "kind": "building",
        "structures": 1,
        "floorAreaM2": 122.2,
        "rule": "single",
        "estate": null
      },
      "record": {
        "machine": "GA-1LV-070-1201-1",
        "home": "Louis 1201",
        "written": "Louis 12 01",
        "zone": "1LV-070",
        "official_name": "Louis",
        "number": "1201",
        "check": "1",
        "status": "provisional",
        "issued": "bulk",
        "issued_at": "2026-10-21T07:32:20Z",
        "entrance_lat": "0.4085002",
        "entrance_lng": "9.4314043",
        "entrance_kind": "centre",
        "spot_code": "GA-1LV E0794 N0757",
        "official_address": "Avenue Joseph Deemin, Libreville",
        "class": "residential",
        "use": "residential",
        "kind": "building",
        "structures": "1",
        "floor_area_m2": "122.2",
        "rule": "single",
        "estate": ""
      },
      "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
    }
  ],
  "total": 1
}
```

A number of the wrong length for its name.

```sh
curl -s 'http://localhost:8080/v1/find?q=Louis%20120'
```

Response `404`:

```json
{
  "error": {
    "code": "wrong_length",
    "message": "Numbers of Louis have 4 digits."
  }
}
```

A number in no issued compound.

```sh
curl -s 'http://localhost:8080/v1/find?q=Louis%2026%2090'
```

Response `404`:

```json
{
  "error": {
    "code": "not_issued",
    "message": "No compound has Louis 26 90 yet (the number is in the block of Louis, Libreville)."
  }
}
```

A name no area has.

```sh
curl -s 'http://localhost:8080/v1/find?q=Atlantide%2012%2001'
```

Response `404`:

```json
{
  "error": {
    "code": "unknown_name",
    "message": "No area of Gabon is called “Atlantide”."
  }
}
```

Nothing to look up.

```sh
curl -s 'http://localhost:8080/v1/find?q='
```

Response `400`:

```json
{
  "error": {
    "code": "missing_q",
    "message": "The query parameter q is required."
  }
}
```

## GET /v1/at?lat=&lng=

The compound at a point: the nearest entrance within 12 m. A point is in Gabon when a département outline holds it, or, in a gap between outlines (a sliver between départements, the shoreline, an island), when it has a spot code ([SPEC §5](../engine/SPEC.md#5-spot-codes)); its area then follows the usual rule.

```sh
curl -s 'http://localhost:8080/v1/at?lat=0.40851&lng=9.43142'
```

Response `200`:

```json
{
  "status": "found",
  "code": {
    "country": "GA",
    "machine": "GA-1LV-070-1201-1",
    "home": "Louis 1201",
    "written": "Louis 12 01",
    "spoken": "Louis, 12 01",
    "number": 1201,
    "check": 1,
    "status": "provisional",
    "issued": "bulk",
    "issuedAt": "2026-10-21T07:32:20Z",
    "area": {
      "key": "1LV-070",
      "id": 435,
      "plateName": "Louis",
      "officialName": "Louis",
      "provisionalName": false,
      "zone": "1LV",
      "zoneName": "Libreville"
    },
    "zone": {
      "key": "1LV",
      "name": "Libreville",
      "region": "GA-1",
      "index": 3
    },
    "officialAddress": "Avenue Joseph Deemin, Libreville",
    "entrance": {
      "lat": 0.4085002,
      "lng": 9.4314043,
      "kind": "centre"
    },
    "spotCode": "GA-1LV E0794 N0757",
    "plusCode": "6FGFCC5J+CH2",
    "profile": {
      "class": "residential",
      "use": "residential",
      "kind": "building",
      "structures": 1,
      "floorAreaM2": 122.2,
      "rule": "single",
      "estate": null
    },
    "record": {
      "machine": "GA-1LV-070-1201-1",
      "home": "Louis 1201",
      "written": "Louis 12 01",
      "zone": "1LV-070",
      "official_name": "Louis",
      "number": "1201",
      "check": "1",
      "status": "provisional",
      "issued": "bulk",
      "issued_at": "2026-10-21T07:32:20Z",
      "entrance_lat": "0.4085002",
      "entrance_lng": "9.4314043",
      "entrance_kind": "centre",
      "spot_code": "GA-1LV E0794 N0757",
      "official_address": "Avenue Joseph Deemin, Libreville",
      "class": "residential",
      "use": "residential",
      "kind": "building",
      "structures": "1",
      "floor_area_m2": "122.2",
      "rule": "single",
      "estate": ""
    },
    "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
  },
  "distanceM": 2,
  "area": {
    "key": "1LV-070",
    "id": 435,
    "plateName": "Louis",
    "officialName": "Louis",
    "provisionalName": false,
    "zone": "1LV",
    "zoneName": "Libreville"
  }
}
```

No compound: the area a new home there would take, and the nearest code.

```sh
curl -s 'http://localhost:8080/v1/at?lat=0.41802&lng=9.43226'
```

Response `200`:

```json
{
  "status": "none",
  "canIssue": true,
  "area": {
    "key": "1LV-035",
    "id": 400,
    "plateName": "Batterie",
    "officialName": "Batterie 4",
    "provisionalName": true,
    "zone": "1LV",
    "zoneName": "Libreville"
  },
  "nearest": {
    "machine": "GA-1LV-035-1753-8",
    "home": "Batterie 1753",
    "written": "Batterie 17 53",
    "status": "provisional",
    "area": "1LV-035",
    "entrance": {
      "lat": 0.4179793,
      "lng": 9.4325531
    },
    "officialAddress": "Rue Ogombomono, Libreville",
    "distanceM": 32.9
  }
}
```

Outside Gabon: in no outline, and too far from every outline for a spot code.

```sh
curl -s 'http://localhost:8080/v1/at?lat=4.05&lng=9.70'
```

Response `404`:

```json
{
  "error": {
    "code": "outside",
    "message": "The point is outside Gabon."
  }
}
```

A coordinate that is not a number.

```sh
curl -s 'http://localhost:8080/v1/at?lat=north&lng=9.43'
```

Response `400`:

```json
{
  "error": {
    "code": "bad_lat",
    "message": "lat is a number."
  }
}
```

## GET /v1/near?lat=&lng=&radius=

Codes within a radius (at most 500 m), nearest first, at most 100. A point outside Gabon (as for `/v1/at`) is `404 outside`.

```sh
curl -s 'http://localhost:8080/v1/near?lat=0.4085&lng=9.4314&radius=25&limit=3'
```

Response `200`:

```json
{
  "point": {
    "lat": 0.4085,
    "lng": 9.4314
  },
  "radiusM": 25.0,
  "total": 6,
  "codes": [
    {
      "machine": "GA-1LV-070-1201-1",
      "home": "Louis 1201",
      "written": "Louis 12 01",
      "status": "provisional",
      "area": "1LV-070",
      "entrance": {
        "lat": 0.4085002,
        "lng": 9.4314043
      },
      "officialAddress": "Avenue Joseph Deemin, Libreville",
      "distanceM": 0.5
    },
    {
      "machine": "GA-1LV-070-1200-6",
      "home": "Louis 1200",
      "written": "Louis 12 00",
      "status": "provisional",
      "area": "1LV-070",
      "entrance": {
        "lat": 0.4084777,
        "lng": 9.4314806
      },
      "officialAddress": "Avenue Joseph Deemin, Libreville",
      "distanceM": 9.3
    },
    {
      "machine": "GA-1LV-070-1202-2",
      "home": "Louis 1202",
      "written": "Louis 12 02",
      "status": "provisional",
      "area": "1LV-070",
      "entrance": {
        "lat": 0.4086074,
        "lng": 9.4314007
      },
      "officialAddress": "Avenue Joseph Deemin, Libreville",
      "distanceM": 11.9
    }
  ]
}
```

Radius over 500 m.

```sh
curl -s 'http://localhost:8080/v1/near?lat=0.4085&lng=9.4314&radius=600'
```

Response `400`:

```json
{
  "error": {
    "code": "bad_radius",
    "message": "radius is in metres, more than 0 and at most 500."
  }
}
```

## GET /v1/verify?code=

A valid, issued code.

```sh
curl -s 'http://localhost:8080/v1/verify?code=GA-1LV-070-1201-1'
```

Response `200`:

```json
{
  "code": "GA-1LV-070-1201-1",
  "syntax": true,
  "checkDigit": "ok",
  "inBlocks": true,
  "valid": true,
  "issued": true,
  "area": "1LV-070",
  "status": "provisional",
  "machine": "GA-1LV-070-1201-1",
  "home": "Louis 1201"
}
```

Two digits swapped: the check digit catches it.

```sh
curl -s 'http://localhost:8080/v1/verify?code=GA-1LV-070-2101-1'
```

Response `200`:

```json
{
  "code": "GA-1LV-070-2101-1",
  "syntax": true,
  "checkDigit": "wrong",
  "inBlocks": true,
  "valid": false,
  "issued": false,
  "area": "1LV-070",
  "reason": "the check digit does not match: a digit is wrong or two are swapped"
}
```

No check digit: it cannot be validated.

```sh
curl -s 'http://localhost:8080/v1/verify?code=GA-1LV-070-1201'
```

Response `200`:

```json
{
  "code": "GA-1LV-070-1201",
  "syntax": true,
  "checkDigit": "absent",
  "inBlocks": true,
  "valid": false,
  "issued": true,
  "area": "1LV-070",
  "reason": "no check digit: the code cannot be validated",
  "status": "provisional",
  "machine": "GA-1LV-070-1201-1",
  "home": "Louis 1201"
}
```

No code given.

```sh
curl -s 'http://localhost:8080/v1/verify'
```

Response `400`:

```json
{
  "error": {
    "code": "missing_code",
    "message": "The query parameter code is required."
  }
}
```

## GET /v1/spot?lat=&lng=

The spot code of a point: its 10 m cell in the frame of the département whose outline holds it. A point in no outline (a sliver between départements, the shoreline, an island) takes the département with the nearest outline within 20 km whose frame holds it, ties to the lower key, or else the nearest cell of a frame at most 1,000 m away ([SPEC §5](../engine/SPEC.md#5-spot-codes)). A point farther away is outside Gabon.

```sh
curl -s 'http://localhost:8080/v1/spot?lat=0.4085002&lng=9.4314043'
```

Response `200`:

```json
{
  "spot": "GA-1LV E0794 N0757",
  "zone": {
    "key": "1LV",
    "name": "Libreville",
    "region": "GA-1",
    "index": 3
  },
  "cellM": 10,
  "centre": {
    "lat": 0.4085062,
    "lng": 9.431373
  }
}
```

A compound on an island 18.4 km from the nearest outline (Moka, Komo-Mondah).

```sh
curl -s 'http://localhost:8080/v1/spot?lat=0.8104524&lng=9.3792151'
```

Response `200`:

```json
{
  "spot": "GA-1KM E0881 N6971",
  "zone": {
    "key": "1KM",
    "name": "Komo-Mondah",
    "region": "GA-1",
    "index": 1
  },
  "cellM": 10,
  "centre": {
    "lat": 0.8104828,
    "lng": 9.3791883
  }
}
```

Outside Gabon (Douala, Cameroon).

```sh
curl -s 'http://localhost:8080/v1/spot?lat=4.05&lng=9.70'
```

Response `404`:

```json
{
  "error": {
    "code": "outside",
    "message": "The point is outside Gabon."
  }
}
```

## GET /v1/spot/decode?code=

The centre of a spot cell, and the compound there.

```sh
curl -s 'http://localhost:8080/v1/spot/decode?code=GA-1LV%20E0794%20N0757'
```

Response `200`:

```json
{
  "spot": "GA-1LV E0794 N0757",
  "zone": {
    "key": "1LV",
    "name": "Libreville",
    "region": "GA-1",
    "index": 3
  },
  "centre": {
    "lat": 0.4085062,
    "lng": 9.431373
  },
  "cellM": 10,
  "code": {
    "machine": "GA-1LV-070-1201-1",
    "home": "Louis 1201",
    "written": "Louis 12 01",
    "status": "provisional",
    "area": "1LV-070",
    "entrance": {
      "lat": 0.4085002,
      "lng": 9.4314043
    },
    "officialAddress": "Avenue Joseph Deemin, Libreville",
    "distanceM": 3.5
  }
}
```

Wrong number of digits for the zone frame.

```sh
curl -s 'http://localhost:8080/v1/spot/decode?code=GA-1LV%20E794%20N0757'
```

Response `400`:

```json
{
  "error": {
    "code": "bad_spot",
    "message": "A spot code is GA-<zone> E<east> N<north>, e.g. GA-1LV E0794 N0757."
  }
}
```

## GET /v1/zones

The 49 départements.

```sh
curl -s 'http://localhost:8080/v1/zones'
```

Response `200`:

```json
{
  "zones": [
    {
      "key": "1KG",
      "index": 0,
      "name": "Komo",
      "region": "GA-1",
      "codes": 8527,
      "areas": 205
    },
    {
      "key": "1KM",
      "index": 1,
      "name": "Komo-Mondah",
      "region": "GA-1",
      "codes": 123489,
      "areas": 109
    },
    {
      "key": "1KO",
      "index": 2,
      "name": "Komo-Ocèan",
      "region": "GA-1",
      "codes": 1452,
      "areas": 51
    },
    "... 46 more"
  ],
  "total": 49
}
```

## GET /v1/zones/{key}

A département with its areas.

```sh
curl -s 'http://localhost:8080/v1/zones/2BB'
```

Response `200`:

```json
{
  "key": "2BB",
  "name": "Bayi Brikolo",
  "region": "GA-2",
  "index": 6,
  "frame": {
    "lon0": 13.81,
    "lat0": -0.83,
    "latc": -0.59,
    "digitsE": 4,
    "digitsN": 4
  },
  "codes": 944,
  "areas": [
    {
      "key": "2BB-001",
      "id": 604,
      "plateName": "Aboto",
      "officialName": "Aboto",
      "provisionalName": false,
      "zone": "2BB",
      "zoneName": "Bayi Brikolo",
      "codes": 9,
      "blocks": [
        [
          100,
          119
        ]
      ]
    },
    {
      "key": "2BB-002",
      "id": 605,
      "plateName": "Aboumi",
      "officialName": "Aboumi",
      "provisionalName": false,
      "zone": "2BB",
      "zoneName": "Bayi Brikolo",
      "codes": 674,
      "blocks": [
        [
          1000,
          2349
        ]
      ]
    },
    {
      "key": "2BB-003",
      "id": 606,
      "plateName": "Ambinda",
      "officialName": "Ambinda",
      "provisionalName": false,
      "zone": "2BB",
      "zoneName": "Bayi Brikolo",
      "codes": 5,
      "blocks": [
        [
          100,
          119
        ]
      ]
    },
    {
      "key": "2BB-004",
      "id": 607,
      "plateName": "Lekadouba",
      "officialName": "Lekadouba",
      "provisionalName": false,
      "zone": "2BB",
      "zoneName": "Bayi Brikolo",
      "codes": 2,
      "blocks": [
        [
          100,
          119
        ]
      ]
    },
    {
      "key": "2BB-005",
      "id": 608,
      "plateName": "Obéli",
      "officialName": "Obéli",
      "provisionalName": false,
      "zone": "2BB",
      "zoneName": "Bayi Brikolo",
      "codes": 96,
      "blocks": [
        [
          100,
          299
        ]
      ]
    },
    {
      "key": "2BB-006",
      "id": 609,
      "plateName": "Olongo II",
      "officialName": "Olongo II",
      "provisionalName": false,
      "zone": "2BB",
      "zoneName": "Bayi Brikolo",
      "codes": 0,
      "blocks": []
    },
    {
      "key": "2BB-007",
      "id": 610,
      "plateName": "Omboye",
      "officialName": "Omboye Frontière",
      "provisionalName": false,
      "zone": "2BB",
      "zoneName": "Bayi Brikolo",
      "codes": 158,
      "blocks": [
        [
          100,
          419
        ]
      ]
    },
    {
      "key": "2BB-008",
      "id": 611,
      "plateName": "Oyabi",
      "officialName": "Oyabi",
      "provisionalName": false,
      "zone": "2BB",
      "zoneName": "Bayi Brikolo",
      "codes": 0,
      "blocks": []
    }
  ]
}
```

An unknown key.

```sh
curl -s 'http://localhost:8080/v1/zones/9XX'
```

Response `404`:

```json
{
  "error": {
    "code": "unknown_zone",
    "message": "There is no zone “9XX”; see /v1/zones."
  }
}
```

## GET /v1/zones/{key}/codes?after=&limit=

One page of a département's codes, in machine order; `next` is the cursor for `after`.

```sh
curl -s 'http://localhost:8080/v1/zones/1LV/codes?limit=2'
```

Response `200`:

```json
{
  "zone": "1LV",
  "codes": [
    {
      "machine": "GA-1LV-001-1000-0",
      "home": "Acaé 1000",
      "written": "Acaé 10 00",
      "status": "provisional",
      "area": "1LV-001",
      "entrance": {
        "lat": 0.3426974,
        "lng": 9.4730837
      }
    },
    {
      "machine": "GA-1LV-001-1001-3",
      "home": "Acaé 1001",
      "written": "Acaé 10 01",
      "status": "provisional",
      "area": "1LV-001",
      "entrance": {
        "lat": 0.3428021,
        "lng": 9.4730869
      }
    }
  ],
  "count": 2,
  "next": "GA-1LV-001-1001-3"
}
```

The next page.

```sh
curl -s 'http://localhost:8080/v1/zones/1LV/codes?limit=2&after=GA-1LV-001-1001-3'
```

Response `200`:

```json
{
  "zone": "1LV",
  "codes": [
    {
      "machine": "GA-1LV-001-1002-1",
      "home": "Acaé 1002",
      "written": "Acaé 10 02",
      "status": "provisional",
      "area": "1LV-001",
      "entrance": {
        "lat": 0.3428133,
        "lng": 9.4730065
      }
    },
    {
      "machine": "GA-1LV-001-1003-7",
      "home": "Acaé 1003",
      "written": "Acaé 10 03",
      "status": "provisional",
      "area": "1LV-001",
      "entrance": {
        "lat": 0.3429475,
        "lng": 9.4729481
      }
    }
  ],
  "count": 2,
  "next": "GA-1LV-001-1003-7"
}
```

## GET /v1/areas/{id}

An area by key (or by numeric id), with its blocks, counts and its name's national range.

```sh
curl -s 'http://localhost:8080/v1/areas/1LV-070'
```

Response `200`:

```json
{
  "key": "1LV-070",
  "id": 435,
  "plateName": "Louis",
  "officialName": "Louis",
  "provisionalName": false,
  "zone": "1LV",
  "zoneName": "Libreville",
  "index": "070",
  "nameKey": "LUIS",
  "nameId": 1801,
  "digits": 4,
  "blocks": [
    [
      1000,
      2699
    ]
  ],
  "codes": 848,
  "compoundsAtFirstIssue": 848,
  "place": {
    "lat": 0.410597,
    "lng": 9.432828
  },
  "frame": [
    9.429597,
    0.406494,
    9.43769,
    0.414309
  ],
  "alertZone": false,
  "nameRange": {
    "range": [
      1000,
      9999
    ],
    "spareFrom": 2700,
    "areas": [
      "1LV-070"
    ]
  }
}
```

An unknown area.

```sh
curl -s 'http://localhost:8080/v1/areas/1LV-999'
```

Response `404`:

```json
{
  "error": {
    "code": "unknown_area",
    "message": "There is no area “1LV-999”."
  }
}
```

## GET /v1/areas?name=

Every area of a name, plate or official, accents and case ignored.

```sh
curl -s 'http://localhost:8080/v1/areas?name=mandji'
```

Response `200`:

```json
{
  "name": "mandji",
  "total": 18,
  "areas": [
    {
      "key": "3LB-102",
      "id": 1156,
      "plateName": "Mandji",
      "officialName": "Mandji",
      "provisionalName": false,
      "zone": "3LB",
      "zoneName": "Ogooue Et Lacs",
      "codes": 24,
      "blocks": [
        [
          1000,
          1049
        ]
      ]
    },
    {
      "key": "4FG-058",
      "id": 1460,
      "plateName": "Mandji",
      "officialName": "Mandji",
      "provisionalName": false,
      "zone": "4FG",
      "zoneName": "Tsamba Magotsi",
      "codes": 0,
      "blocks": []
    },
    {
      "key": "4FG-059",
      "id": 1461,
      "plateName": "Mandji",
      "officialName": "Mandji",
      "provisionalName": false,
      "zone": "4FG",
      "zoneName": "Tsamba Magotsi",
      "codes": 31,
      "blocks": [
        [
          1050,
          1119
        ]
      ]
    },
    "... 15 more"
  ]
}
```

An official name finds its area under its plate name.

```sh
curl -s 'http://localhost:8080/v1/areas?name=Baie%20des%20Rois'
```

Response `200`:

```json
{
  "name": "Baie des Rois",
  "total": 1,
  "areas": [
    {
      "key": "1LV-029",
      "id": 394,
      "plateName": "Rois",
      "officialName": "Baie des Rois",
      "provisionalName": false,
      "zone": "1LV",
      "zoneName": "Libreville",
      "codes": 251,
      "blocks": [
        [
          100,
          609
        ]
      ]
    }
  ]
}
```

A name no area has.

```sh
curl -s 'http://localhost:8080/v1/areas?name=Atlantide'
```

Response `404`:

```json
{
  "error": {
    "code": "unknown_name",
    "message": "No area of Gabon is called “Atlantide”."
  }
}
```

## POST /v1/codes

Issuing deployments only (see [server/README.md](../server/README.md), "One issuer"). A point is in Gabon when a département outline holds it, or, in a gap between outlines (a sliver between départements, the shoreline, an island), when it has a spot code ([SPEC §5](../engine/SPEC.md#5-spot-codes)); its area then follows the usual rule. A point outside Gabon is `422 outside`, and so is a point more than 300 m outside Gabon's national border (OpenStreetMap admin_level 2, `engine/data/border.json`) even when a zone outline or a spot zone reaches it: the border decides ([SPEC §6.1](../engine/SPEC.md#61-inputs)). The examples below ran on a test copy of the registry; the codes they show are not part of the published registry.


A new home, with its outline (`[lng, lat]` points).

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 0.4153, "lng": 9.4363, "outline": [[9.43625, 0.41525], [9.43635, 0.41525], [9.43635, 0.41535], [9.43625, 0.41535]]}' 'http://localhost:8080/v1/codes'
```

Response `201`:

```json
{
  "country": "GA",
  "machine": "GA-1LV-095-4300-4",
  "home": "Plaine Orety 4300",
  "written": "Plaine Orety 43 00",
  "spoken": "Plaine Orety, 43 00",
  "number": 4300,
  "check": 4,
  "status": "provisional",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T13:57:17Z",
  "area": {
    "key": "1LV-095",
    "id": 460,
    "plateName": "Plaine Orety",
    "officialName": "Plaine Orety",
    "provisionalName": false,
    "zone": "1LV",
    "zoneName": "Libreville"
  },
  "zone": {
    "key": "1LV",
    "name": "Libreville",
    "region": "GA-1",
    "index": 3
  },
  "officialAddress": null,
  "entrance": {
    "lat": 0.4153,
    "lng": 9.4363,
    "kind": "centre"
  },
  "spotCode": "GA-1LV E0849 N0832",
  "plusCode": "6FGFCC8P+4GF",
  "profile": {
    "class": "residential",
    "use": "residential",
    "kind": "building",
    "structures": 1,
    "floorAreaM2": 123.1,
    "rule": null,
    "estate": null
  },
  "record": {
    "machine": "GA-1LV-095-4300-4",
    "home": "Plaine Orety 4300",
    "written": "Plaine Orety 43 00",
    "zone": "1LV-095",
    "official_name": "Plaine Orety",
    "number": "4300",
    "check": "4",
    "status": "provisional",
    "issued": "on-demand",
    "issued_at": "2026-10-21T13:57:17Z",
    "entrance_lat": "0.4153000",
    "entrance_lng": "9.4363000",
    "entrance_kind": "centre",
    "spot_code": "GA-1LV E0849 N0832",
    "official_address": "",
    "class": "residential",
    "use": "residential",
    "kind": "building",
    "structures": "1",
    "floor_area_m2": "123.1",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
}
```

Another door of a compound (`of`), within 80 m of its entrance.

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 0.41555, "lng": 9.4363, "of": "GA-1LV-095-4300-4"}' 'http://localhost:8080/v1/codes'
```

Response `201`:

```json
{
  "country": "GA",
  "machine": "GA-1LV-095-4301-2",
  "home": "Plaine Orety 4301",
  "written": "Plaine Orety 43 01",
  "spoken": "Plaine Orety, 43 01",
  "number": 4301,
  "check": 2,
  "status": "provisional",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T13:57:17Z",
  "area": {
    "key": "1LV-095",
    "id": 460,
    "plateName": "Plaine Orety",
    "officialName": "Plaine Orety",
    "provisionalName": false,
    "zone": "1LV",
    "zoneName": "Libreville"
  },
  "zone": {
    "key": "1LV",
    "name": "Libreville",
    "region": "GA-1",
    "index": 3
  },
  "officialAddress": null,
  "entrance": {
    "lat": 0.41555,
    "lng": 9.4363,
    "kind": "door"
  },
  "spotCode": "GA-1LV E0849 N0835",
  "plusCode": "6FGFCC8P+6GF",
  "profile": {
    "class": "",
    "use": "residential",
    "kind": "door",
    "structures": 0,
    "floorAreaM2": 0.0,
    "rule": null,
    "estate": null
  },
  "record": {
    "machine": "GA-1LV-095-4301-2",
    "home": "Plaine Orety 4301",
    "written": "Plaine Orety 43 01",
    "zone": "1LV-095",
    "official_name": "Plaine Orety",
    "number": "4301",
    "check": "2",
    "status": "provisional",
    "issued": "on-demand",
    "issued_at": "2026-10-21T13:57:17Z",
    "entrance_lat": "0.4155500",
    "entrance_lng": "9.4363000",
    "entrance_kind": "door",
    "spot_code": "GA-1LV E0849 N0835",
    "official_address": "",
    "class": "",
    "use": "residential",
    "kind": "door",
    "structures": "0",
    "floor_area_m2": "0.0",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
}
```

The building already has a code.

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 0.4085002, "lng": 9.4314043}' 'http://localhost:8080/v1/codes'
```

Response `409`:

```json
{
  "error": {
    "code": "exists",
    "message": "This building already has its code: Louis 1201."
  },
  "existing": {
    "country": "GA",
    "machine": "GA-1LV-070-1201-1",
    "home": "Louis 1201",
    "written": "Louis 12 01",
    "spoken": "Louis, 12 01",
    "number": 1201,
    "check": 1,
    "status": "provisional",
    "issued": "bulk",
    "issuedAt": "2026-10-21T07:32:20Z",
    "area": {
      "key": "1LV-070",
      "id": 435,
      "plateName": "Louis",
      "officialName": "Louis",
      "provisionalName": false,
      "zone": "1LV",
      "zoneName": "Libreville"
    },
    "zone": {
      "key": "1LV",
      "name": "Libreville",
      "region": "GA-1",
      "index": 3
    },
    "officialAddress": "Avenue Joseph Deemin, Libreville",
    "entrance": {
      "lat": 0.4085002,
      "lng": 9.4314043,
      "kind": "centre"
    },
    "spotCode": "GA-1LV E0794 N0757",
    "plusCode": "6FGFCC5J+CH2",
    "profile": {
      "class": "residential",
      "use": "residential",
      "kind": "building",
      "structures": 1,
      "floorAreaM2": 122.2,
      "rule": "single",
      "estate": null
    },
    "record": {
      "machine": "GA-1LV-070-1201-1",
      "home": "Louis 1201",
      "written": "Louis 12 01",
      "zone": "1LV-070",
      "official_name": "Louis",
      "number": "1201",
      "check": "1",
      "status": "provisional",
      "issued": "bulk",
      "issued_at": "2026-10-21T07:32:20Z",
      "entrance_lat": "0.4085002",
      "entrance_lng": "9.4314043",
      "entrance_kind": "centre",
      "spot_code": "GA-1LV E0794 N0757",
      "official_address": "Avenue Joseph Deemin, Libreville",
      "class": "residential",
      "use": "residential",
      "kind": "building",
      "structures": "1",
      "floor_area_m2": "122.2",
      "rule": "single",
      "estate": ""
    },
    "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
  }
}
```

An outline too small for a home.

```sh
curl -s -X POST -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"lat": 0.416, "lng": 9.437, "outline": [[9.437, 0.416], [9.43701, 0.416], [9.43701, 0.41601]]}' 'http://localhost:8080/v1/codes'
```

Response `422`:

```json
{
  "error": {
    "code": "bad_outline",
    "message": "That outline is 1 m², but a home's is between 6 m² and 2 ha."
  }
}
```

No key, or a key that is not one of the deployment's.

```sh
curl -s -X POST -H 'Content-Type: application/json' -d '{"lat": 0.416, "lng": 9.437}' 'http://localhost:8080/v1/codes'
```

Response `401`:

```json
{
  "error": {
    "code": "unauthorised",
    "message": "Send the issuing key as \"Authorization: Bearer <key>\"."
  }
}
```

## PATCH /v1/codes/{machine}

Confirm a code.

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"status": "confirmed"}' 'http://localhost:8080/v1/codes/GA-1LV-095-4300-4'
```

Response `200`:

```json
{
  "country": "GA",
  "machine": "GA-1LV-095-4300-4",
  "home": "Plaine Orety 4300",
  "written": "Plaine Orety 43 00",
  "spoken": "Plaine Orety, 43 00",
  "number": 4300,
  "check": 4,
  "status": "confirmed",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T13:57:17Z",
  "area": {
    "key": "1LV-095",
    "id": 460,
    "plateName": "Plaine Orety",
    "officialName": "Plaine Orety",
    "provisionalName": false,
    "zone": "1LV",
    "zoneName": "Libreville"
  },
  "zone": {
    "key": "1LV",
    "name": "Libreville",
    "region": "GA-1",
    "index": 3
  },
  "officialAddress": null,
  "entrance": {
    "lat": 0.4153,
    "lng": 9.4363,
    "kind": "centre"
  },
  "spotCode": "GA-1LV E0849 N0832",
  "plusCode": "6FGFCC8P+4GF",
  "profile": {
    "class": "residential",
    "use": "residential",
    "kind": "building",
    "structures": 1,
    "floorAreaM2": 123.1,
    "rule": null,
    "estate": null
  },
  "record": {
    "machine": "GA-1LV-095-4300-4",
    "home": "Plaine Orety 4300",
    "written": "Plaine Orety 43 00",
    "zone": "1LV-095",
    "official_name": "Plaine Orety",
    "number": "4300",
    "check": "4",
    "status": "confirmed",
    "issued": "on-demand",
    "issued_at": "2026-10-21T13:57:17Z",
    "entrance_lat": "0.4153000",
    "entrance_lng": "9.4363000",
    "entrance_kind": "centre",
    "spot_code": "GA-1LV E0849 N0832",
    "official_address": "",
    "class": "residential",
    "use": "residential",
    "kind": "building",
    "structures": "1",
    "floor_area_m2": "123.1",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
}
```

Move the entrance to the gate (at most 80 m).

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"entrance": {"lat": 0.4152, "lng": 9.4363, "kind": "gate"}}' 'http://localhost:8080/v1/codes/GA-1LV-095-4300-4'
```

Response `200`:

```json
{
  "country": "GA",
  "machine": "GA-1LV-095-4300-4",
  "home": "Plaine Orety 4300",
  "written": "Plaine Orety 43 00",
  "spoken": "Plaine Orety, 43 00",
  "number": 4300,
  "check": 4,
  "status": "confirmed",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T13:57:17Z",
  "area": {
    "key": "1LV-095",
    "id": 460,
    "plateName": "Plaine Orety",
    "officialName": "Plaine Orety",
    "provisionalName": false,
    "zone": "1LV",
    "zoneName": "Libreville"
  },
  "zone": {
    "key": "1LV",
    "name": "Libreville",
    "region": "GA-1",
    "index": 3
  },
  "officialAddress": null,
  "entrance": {
    "lat": 0.4152,
    "lng": 9.4363,
    "kind": "gate"
  },
  "spotCode": "GA-1LV E0849 N0831",
  "plusCode": "6FGFCC8P+3GM",
  "profile": {
    "class": "residential",
    "use": "residential",
    "kind": "building",
    "structures": 1,
    "floorAreaM2": 123.1,
    "rule": null,
    "estate": null
  },
  "record": {
    "machine": "GA-1LV-095-4300-4",
    "home": "Plaine Orety 4300",
    "written": "Plaine Orety 43 00",
    "zone": "1LV-095",
    "official_name": "Plaine Orety",
    "number": "4300",
    "check": "4",
    "status": "confirmed",
    "issued": "on-demand",
    "issued_at": "2026-10-21T13:57:17Z",
    "entrance_lat": "0.4152000",
    "entrance_lng": "9.4363000",
    "entrance_kind": "gate",
    "spot_code": "GA-1LV E0849 N0831",
    "official_address": "",
    "class": "residential",
    "use": "residential",
    "kind": "building",
    "structures": "1",
    "floor_area_m2": "123.1",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
}
```

Too far.

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"entrance": {"lat": 0.417, "lng": 9.4363}}' 'http://localhost:8080/v1/codes/GA-1LV-095-4300-4'
```

Response `422`:

```json
{
  "error": {
    "code": "too_far",
    "message": "The new entrance is 200 m from the old one; it may move at most 80 m."
  }
}
```

A wrong check digit is refused here too; the change is never applied to a neighbouring code.

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"status": "confirmed"}' 'http://localhost:8080/v1/codes/GA-1LV-070-1201-7'
```

Response `422`:

```json
{
  "error": {
    "code": "check_digit",
    "message": "The check digit does not match: a digit is wrong or two are swapped."
  }
}
```

Retire it. A retired code never comes back, and its number is never given again.

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"status": "retired"}' 'http://localhost:8080/v1/codes/GA-1LV-095-4300-4'
```

Response `200`:

```json
{
  "country": "GA",
  "machine": "GA-1LV-095-4300-4",
  "home": "Plaine Orety 4300",
  "written": "Plaine Orety 43 00",
  "spoken": "Plaine Orety, 43 00",
  "number": 4300,
  "check": 4,
  "status": "retired",
  "issued": "on-demand",
  "issuedAt": "2026-10-21T13:57:17Z",
  "area": {
    "key": "1LV-095",
    "id": 460,
    "plateName": "Plaine Orety",
    "officialName": "Plaine Orety",
    "provisionalName": false,
    "zone": "1LV",
    "zoneName": "Libreville"
  },
  "zone": {
    "key": "1LV",
    "name": "Libreville",
    "region": "GA-1",
    "index": 3
  },
  "officialAddress": null,
  "entrance": {
    "lat": 0.4152,
    "lng": 9.4363,
    "kind": "gate"
  },
  "spotCode": "GA-1LV E0849 N0831",
  "plusCode": "6FGFCC8P+3GM",
  "profile": {
    "class": "residential",
    "use": "residential",
    "kind": "building",
    "structures": 1,
    "floorAreaM2": 123.1,
    "rule": null,
    "estate": null
  },
  "record": {
    "machine": "GA-1LV-095-4300-4",
    "home": "Plaine Orety 4300",
    "written": "Plaine Orety 43 00",
    "zone": "1LV-095",
    "official_name": "Plaine Orety",
    "number": "4300",
    "check": "4",
    "status": "retired",
    "issued": "on-demand",
    "issued_at": "2026-10-21T13:57:17Z",
    "entrance_lat": "0.4152000",
    "entrance_lng": "9.4363000",
    "entrance_kind": "gate",
    "spot_code": "GA-1LV E0849 N0831",
    "official_address": "",
    "class": "residential",
    "use": "residential",
    "kind": "building",
    "structures": "1",
    "floor_area_m2": "123.1",
    "rule": "",
    "estate": ""
  },
  "credit": "N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"
}
```

A retired code never changes again.

```sh
curl -s -X PATCH -H "Authorization: Bearer $ISSUE_KEY" -H 'Content-Type: application/json' -d '{"status": "confirmed"}' 'http://localhost:8080/v1/codes/GA-1LV-095-4300-4'
```

Response `409`:

```json
{
  "error": {
    "code": "retired",
    "message": "Plaine Orety 4300 is retired; a retired code never comes back and its number is never reused."
  }
}
```

## Errors common to every endpoint

A path that is not an endpoint.

```sh
curl -s 'http://localhost:8080/v1/codez'
```

Response `404`:

```json
{
  "error": {
    "code": "not_found",
    "message": "There is no endpoint /v1/codez; see /v1/info and docs/api.md."
  }
}
```

A method the endpoint does not take.

```sh
curl -s -X DELETE 'http://localhost:8080/v1/zones'
```

Response `405`:

```json
{
  "error": {
    "code": "method_not_allowed",
    "message": "DELETE is not allowed here; use GET."
  }
}
```
