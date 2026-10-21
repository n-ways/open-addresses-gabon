# Tools: Gabon's registry

These tools rebuild the registry from its sources. Nobody needs them to use the codes, the engine or the server: the published `registry/`, `model/` and `engine/data/` are the result.

All inputs are read-only: the N-Ways data folder (environment variable `NWAYS_ROOT`, holding `data/`), the N-Ways database (`NWAYS_DB`, a PostgreSQL URL; tables `regions` and `places`) and the GeoNames dump `GA.txt` (https://download.geonames.org/export/dump/, CC BY 4.0). Run one heavy step at a time: DuckDB runs with `memory_limit='3GB'` and spills to the work folder; the grouping and the numbering read the footprints one code area at a time.

| Step | Script | Writes |
|---|---|---|
| 1 | osmium exports (below) | `admin`, `bar`, `place`, `hw` `.geojsonseq` in the work folder |
| 2 | `prepare-inputs.py <work>` | `units.geojson` (the 49 départements, OpenStreetMap), `streets.csv` (the named streets of Libreville), `enclosures.geojson`, `estates.geojson`, `gates.csv`, `places.csv`, `country.geojson` (the national border, OpenStreetMap admin_level 2: required, the step stops without it) |
| 2b | `build-border.py <work>` | `engine/data/border.json`: `country.geojson` simplified to 50 m (Douglas-Peucker, under 1 MB), the line every later step and the server check against |
| 3 | `build-areas.py <work> <GA.txt>` | `model/areas/register.json`: the 4,922 code areas, from OpenStreetMap places and GeoNames populated places |
| 4 | `extract-buildings.py <work>` | `buildings-raw.csv` (every footprint inside Gabon with its enclosure, estate, zone and nearest official street within 30 m; specks under 1 m² dropped), `buildings-pts.csv`, `enclosure-gates.csv` |
| 5 | `assign-areas.py <work>` | `area-of.csv` (each footprint's code area: the nearest named place of its zone), `area-boxes.json` (each area's frame) |
| 6 | `sort-buildings.py <work>` | `buildings.csv`, sorted by area |
| 7 | `issue_registry.py group <work>` | `compounds.jsonl.gz` (compounds and profiles; a compound whose point lies more than 300 m outside the border is dropped, counted as `abroad`; city rules in Libreville and Bendje (Port-Gentil), huts clustered elsewhere), `area-counts.json`, `group-stats.json` |
| 8 | `build-register.py <work> --freeze` | `area-compounds.py` and `name-ranges.py` on the real compounds: plate names, national ranges and blocks; `model/areas/name-ranges.json`, `engine/data/register.json`, `engine/data/units.json`, `model/stats/register.json` |
| 9 | `issue_registry.py number <work> <work>/lotes.jsonl.gz` | the lotes, area by area (it stops on any compound more than 300 m outside the border), with the reference's numbers and the official street |
| 10 | the N-Ways issuer, from `<work>/lotes.jsonl.gz` | the codes, after checking every number against the reference's; the registry (every compound of every département), gzipped into `registry/`. `python3 -m server export` writes the same format (server/README.md) |
| 11 | `vectors.py`, `paper-stats.py <work> <work>/lotes.jsonl.gz` | `engine/reference/vectors.json`, `model/stats/building-stats.json` |
| 12 | `paper-figures.py` (reads only the published `registry/` and `model/`) | `docs/figures/*.dat`, the data of the paper's figures; `sh docs/paper/build.sh` then compiles the figures and the PDFs |

**The border decides.** A Gabon code is only ever given to a building whose entrance lies inside Gabon's national border (OpenStreetMap's admin_level 2 boundary, `country.geojson`) or within 300 m of it. Zone outlines from other sources (geoBoundaries, GADM and the like) may spill over the border into a neighbouring country; they never decide. Three guards keep a re-run from coding a building across it:

1. `extract-buildings.py` keeps only footprints whose centre is inside the border (stricter than 300 m);
2. `issue_registry.py group` drops any compound whose point lies more than 300 m outside it, and `number` stops on one;
3. the issuer (the N-Ways issuer, and `server/` with `engine/data/border.json`) refuses any code more than 300 m outside it.

The shipped line is within 50 m of the true one, so the check against it (`engine/reference/ga_border.py`) refuses a point more than 245 m outside the shipped line (300 m less 50 m, less 5 m for the local plane): nothing more than 300 m outside the true border passes, nothing inside it is refused. `python3 engine/reference/ga_border.py check LAT LNG` checks one point.

**After first issue** the register is frozen: never run `build-register.py --freeze` again. An area is renamed only through `model/areas/renames.json` (created with the first rename) and `rename-areas.py`, which appends new name ids, leaves every other name alone and prints each moved block (old start, new start) for the database.

`stage.py`, `analyze.py` and `areas.py` computed the zone and building statistics that sized the model (`model/stats/country-profile.json`); `build-zones.py` built `model/zones.json` and `model/units/zones.geojson`. They are kept so those figures can be reproduced.

### osmium exports

```
P=data/osm/gabon-latest.osm.pbf
osmium tags-filter -o b.osm.pbf $P r/boundary=administrative
osmium export -a type,id -f geojsonseq --geometry-types=polygon -o admin.geojsonseq b.osm.pbf
osmium tags-filter -o bar.osm.pbf $P w/barrier=wall,fence,hedge,retaining_wall n/barrier=gate,entrance,lift_gate,sliding_gate,swing_gate n/entrance
osmium export -a type,id -f geojsonseq -o bar.geojsonseq bar.osm.pbf
osmium tags-filter -o place.osm.pbf $P n/place w/place r/place
osmium export -a type,id -f geojsonseq -o place.geojsonseq place.osm.pbf
osmium tags-filter -o hw.osm.pbf $P w/highway
osmium export -a type,id -f geojsonseq -o hw.geojsonseq hw.osm.pbf
```
