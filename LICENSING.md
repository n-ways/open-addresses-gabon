# Licensing

N-Ways Addressing for Gabon is open. Build on it, and credit N-Ways.

| Part | Licence | File |
|---|---|---|
| Code: the engine, the server and the tools (`engine/reference/`, its test vectors, `server/`, `tools/`) | Apache License 2.0 | [LICENSE](LICENSE), [NOTICE](NOTICE) |
| Data: the registry, the areas, the zone outlines and the model (`registry/`, `model/`, `engine/data/`, and the test registry in `server/testdata/`) | Open Database License (ODbL) 1.0 | [LICENSE-DATA](LICENSE-DATA) |
| Documents: the model, the research paper and its PDFs, figures and references, and the verification of existing systems (`docs/`), and this repository's other Markdown files | Creative Commons Attribution 4.0 (CC BY 4.0) | [LICENSE-DOCS](LICENSE-DOCS) |
| The paper's build: its LaTeX style, build script and figure sources (`docs/paper/*.tex`, `build.sh`, `figures.lua`, `colons.lua`, `docs/figures/*.tex`) | Apache License 2.0 | [LICENSE](LICENSE) |
| The figures' data (`docs/figures/*.dat`), computed from the registry | Open Database License (ODbL) 1.0 | [LICENSE-DATA](LICENSE-DATA) |

Two files of the paper's build are third-party and keep their own licences: `docs/paper/ieee.csl`, the IEEE citation style of the Citation Style Language project (CC BY-SA 3.0, credited in the file), and `docs/paper/template.tex`, adapted from pandoc's LaTeX template (© John MacFarlane, BSD 3-clause, at the option pandoc offers).

Licensor: **N-WAYS LIMITED** (nways.ng). Source: https://github.com/n-ways/open-addresses-gabon

## How to credit N-Ways

Copy the line that fits. Link it to https://github.com/n-ways/open-addresses-gabon where you can.

**An app, a website or an API that shows, decodes or issues these addresses** (a deployment of `server/` included):

> Codes by N-Ways Addressing · © N-WAYS LIMITED (nways.ng)

Put it next to the address, or on the screen that shows it, and in your about or licences screen. If you ship or change the engine, also keep [NOTICE](NOTICE) (Apache 2.0, section 4(d)).

**A map, a dataset or a database built from the data:**

> © N-WAYS LIMITED, N-Ways Addressing; contains OpenStreetMap data © OpenStreetMap contributors (ODbL) and the other sources in SOURCES.md

A database you make from it and share is shared under ODbL 1.0 too (share-alike). A map image or a printed plate made from it is a "produced work": it carries the line above, and needs no share-alike.

**A paper, an article, a slide or a translation that uses the documents:**

> N-Ways Addressing for Gabon, © N-WAYS LIMITED (nways.ng), CC BY 4.0. https://github.com/n-ways/open-addresses-gabon

Say what you changed, if you changed anything.

## Sources inside the data

The data is built from open sources (full list in [SOURCES.md](SOURCES.md)). Their own terms travel with it, and the data credit above names them:

| Source | Licence | What you owe it |
|---|---|---|
| OpenStreetMap (buildings, places, gates and enclosures derived from it) | ODbL 1.0 | "© OpenStreetMap contributors"; share-alike, which is why the data is ODbL |
| Microsoft building footprints, via Overture Maps | ODbL 1.0 | credit Microsoft and the Overture Maps Foundation |
| Google Open Buildings, via Overture Maps | CC BY 4.0 | credit Google and the Overture Maps Foundation; compatible with redistribution inside an ODbL database |
| OpenStreetMap: the 49 départements, Libreville's named streets and door numbers, and the place nodes the code areas are named after | ODbL 1.0 | "© OpenStreetMap contributors" |
| GeoNames populated places (GA), the other seeds of the code areas | CC BY 4.0 | "contains GeoNames data (geonames.org), CC BY 4.0" |
| N-Ways places (used only to classify buildings: OSM, Overture, Foursquare OS Places, All The Places) | per source (ODbL, CDLA-Permissive-2.0, Apache-2.0, CC0) | only categories are used, no place records are redistributed |

**Postcodes.** Gabon has no postcode in use; the UPU's 2002 sheet shows a province number before the town but no list was ever published. Each zone keeps a reserved field for a postcode, and no postal data is in this repository.

**Official addresses.** Where Libreville's commune has named a street, a compound on it shows the street first, and a door number of the commune's plan, once known for a gate, replaces it (engine/SPEC.md §6.0). The State's data keeps its own terms and is not redistributed here. Both licences above let the State relicense or republish the registry if it adopts it.

**Everything is published.** The open registry lists every compound of every département, with its code, entrance point and building profile. A deployment of the server serves exactly these rows.

**Personal data.** The registry holds places, never people (docs/paper.md, Privacy).

## Trademarks

"N-Ways" and the N-Ways logo are trade marks of N-WAYS LIMITED. The licences above cover the code, data and documents, not the marks: you may say your product uses N-Ways Addressing, but not that it is N-Ways or is endorsed by N-Ways.
