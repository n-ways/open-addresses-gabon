# N-Ways Addressing for Gabon

**Status: in service since 21 October 2026.** Every compound in Gabon has an N-Ways code: 665,089 of them, all published in [`registry/`](registry/), provisional until residents confirm them. Where the commune gives an address (Libreville's named streets today, its door numbers once known), that address is the official one and is shown first, exactly as written, with the N-Ways code beside it.

A home's code is **the name of a quarter or village people already say plus a number of three to five digits**:

| Code | Machine form | What it is |
|---|---|---|
| `Louis 12 01` | `GA-1LV-070-1201-1` | a compound in Libreville, on Avenue Joseph Deemin (shown first) |
| `Mont-Bouët 19 57` | `GA-1LV-076-1957-3` | by the Marché de Mont-Bouët |
| `Port-Gentil 12 181` | `GA-8PG-042-12181-2` | five digits, said as a pair and a hundred: by Saint-Louis cathedral |
| `Mandji 10 20`, `Mandji 39 50` | | two of 18 places of one name, in different départements: one national range, a block each |
| `GA-1LV E0794 N0757` | | any point: its spot code, a 10 m cell of its département's grid (a point in no outline takes the nearest département within 20 km, [SPEC §5](engine/SPEC.md#5-spot-codes)) |

The code is unique in the whole country on its own: every area with the same plate name shares one national range of numbers, cut into frozen blocks of twice its compounds, so "Name number" never needs a town after it. No number has more than five digits. People never see or type a check digit: a Damm check over the name's national index, the département, the area and the number lives in the machine form, for systems. The name is a **plate name** of at most 12 characters and 2 words, with no digit; the official name still finds it. 252 areas carry a provisional short name their commune may change once; their codes are issued, and the number never changes.

This repository holds everything needed to read, check, serve and issue these codes: the specification, the reference engine, the complete registry, a ready-made server with its API, the tools that built the data, and the research paper that sets out and evaluates the model.

## What is where

| Path | Contents |
|---|---|
| [docs/paper.md](docs/paper.md), [paper.fr.md](docs/paper.fr.md) | the research paper in English and French: existing systems, data, the model with every formula and a worked example on a real code, implementation, evaluation, the designs rejected, and the benefits for citizens, logistics, emergency services and government; typeset as [PDF (en)](docs/n-ways-addressing-gabon-en.pdf) and [PDF (fr)](docs/n-ways-addressing-gabon-fr.pdf) |
| [docs/paper/](docs/paper/), [docs/figures/](docs/figures/) | the paper's LaTeX template, style, build script and references (`references.bib`); the figure sources (TikZ/pgfplots) and the data they plot, computed from the registry by `tools/paper-figures.py` |
| [docs/existing-systems.md](docs/existing-systems.md) | verification: La Poste and the BP, Libreville's street names and door numbers, land, data protection; verdict and sources |
| [docs/model.md](docs/model.md) | the design notes behind every choice |
| [engine/SPEC.md](engine/SPEC.md) | the engine specification (normative) |
| [engine/reference/ga_engine.py](engine/reference/ga_engine.py), [plate_names.py](engine/reference/plate_names.py), [ga_border.py](engine/reference/ga_border.py), [test_ga.py](engine/reference/test_ga.py), [vectors.json](engine/reference/vectors.json) | the reference engine (standard library only), its tests and the conformance vectors every port must reproduce |
| [engine/data/register.json](engine/data/register.json), [units.json](engine/data/units.json), [border.json](engine/data/border.json) | what a decoder ships: départements with their spot frames, every area with its plate and official names, name index, blocks and frame; the aliases; the outlines; the national border (OpenStreetMap, simplified to 50 m) that decides where a code may be given |
| [registry/](registry/) | every issued code: the frozen area table `areas.csv.gz` (every area, its blocks and its count of compounds), one `<département>.csv.gz` per département with all its codes, and `MANIFEST.json` (counts, SHA-256 of each file uncompressed) |
| [server/](server/README.md) | the ready-made server: imports the registry into SQLite, serves the JSON API ([openapi.yaml](server/openapi.yaml), [docs/api.md](docs/api.md)), issues codes where designated, exports the registry back; Docker files and tests |
| [model/](model/) | `areas/` (the code areas, the national name ranges), `units/` (département outlines, spot frames), `zones.json` (the 49 départements), `regions.json` (the 9 provinces), `stats/` (`register.json`, `building-stats.json`, `name-stats.json`, `country-profile.json`: the figures of the paper) |
| [tools/](tools/) | the scripts that built the inputs, the areas, the compounds, the names and the registry |
| [GOVERNANCE.md](GOVERNANCE.md), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) | who decides what, the one-issuer rule, how to propose a change, how to report a problem |
| [SOURCES.md](SOURCES.md), [LICENSING.md](LICENSING.md), [NOTICE](NOTICE), [CITATION.cff](CITATION.cff) | sources, licences, how to credit and cite |

## Run the reference engine

```sh
cd engine/reference
python3 test_ga.py                                   # tests
python3 ga_engine.py resolve Louis 12 01             # remembered form: one area in the whole country
python3 ga_engine.py resolve Mandji 39 50
python3 ga_engine.py verify GA-1LV-070-1201-1        # validate a machine code
python3 ga_engine.py spot 0.4085002 9.4314043        # spot code: GA-1LV E0794 N0757
python3 ga_engine.py unspot "GA-1LV E0794 N0757"
```

Python 3.9 or newer, no packages (see [requirements.txt](requirements.txt)).

## Run the server

```sh
cd server && docker compose up -d          # imports the registry on first start, then serves
curl -s 'http://localhost:8080/v1/find?q=Louis%2012%2001'
```

Or without Docker, from the repository root:

```sh
python3 -m server import --registry registry --db data/addresses.sqlite
python3 -m server serve --db data/addresses.sqlite --port 8080
python3 -m unittest discover -s server/tests -t .     # tests
```

Every endpoint, with real requests and responses, is in [docs/api.md](docs/api.md). A deployment is read-only unless the State or N-WAYS LIMITED has designated it as Gabon's issuer: two issuers would hand out the same number twice ([server/README.md](server/README.md), "One issuer").

## Build the paper

```sh
python3 tools/paper-figures.py   # the figures' data, from registry/ and model/
sh docs/paper/build.sh           # pandoc, tectonic (LaTeX) and pdftocairo: the figures, then the PDFs in docs/
```

## How the registry was made

```sh
python3 tools/prepare-inputs.py <work>              # enclosures, estates, gates, places, départements, Libreville's streets
python3 tools/build-areas.py <work> <GA.txt>        # the code areas, from OpenStreetMap and GeoNames
python3 tools/extract-buildings.py <work>           # every footprint inside Gabon (DuckDB), with its département and street
python3 tools/assign-areas.py <work>                # each footprint's code area and every area's frame
python3 tools/sort-buildings.py <work>              # sorted by area
python3 tools/issue_registry.py group <work>        # compounds and profiles, one area at a time
python3 tools/area-compounds.py <work>              # compounds per area
python3 tools/name-ranges.py                        # plate names and national name ranges
python3 tools/build-register.py <work> --freeze     # national ranges and blocks on the real compounds
python3 tools/issue_registry.py number <work> <work>/lotes.jsonl.gz
python3 tools/vectors.py                            # engine/reference/vectors.json
python3 tools/paper-stats.py <work> <work>/lotes.jsonl.gz
python3 tools/paper-figures.py                      # docs/figures/*.dat, from the published registry
```

The N-Ways issuer then issues the codes, checking every number against the reference's, and exports `registry/` (the same format as `python3 -m server export`). Once issued, the register is frozen: a new run adds codes for new compounds and never renumbers an issued one. [tools/README.md](tools/README.md) lists every step and its inputs.

## Licence and credit

Code (engine, server, tools): Apache License 2.0, with [NOTICE](NOTICE). Data (registry, model, engine data): ODbL 1.0. Documents: CC BY 4.0. Credit every use: **"N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng)"**, with a link to this repository ([LICENSING.md](LICENSING.md)). Derived from OpenStreetMap (© OpenStreetMap contributors, ODbL), GeoNames (CC BY 4.0), Google Open Buildings (CC BY 4.0) and Microsoft building footprints (ODbL).
