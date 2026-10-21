# N-Ways address engine for Gabon — specification / Spécification du moteur N-Ways Gabon

One code for every compound in Gabon, frozen in `engine/data/register.json` at first issue and published in `registry/`.
Reference implementation: [`reference/ga_engine.py`](reference/ga_engine.py) (Python standard library only). Tests: [`reference/test_ga.py`](reference/test_ga.py); conformance vectors from the frozen register: [`reference/vectors.json`](reference/vectors.json) (`tools/vectors.py`).

"MUST", "SHOULD", "MAY" as in RFC 2119. A ready-made server that serves the registry and issues codes by these rules is in [`../server/`](../server/README.md).

## 1. Objects

| Object | What it is | Identifier |
|---|---|---|
| Zone | one of the 49 départements (OpenStreetMap boundaries, `model/units/zones.geojson`) | 3-character key, the province's ISO number then two letters (`1LV`, `8PG`, `9OY`), and a frozen index 0–48 (`model/zones.json`) |
| Code area | a named place of a zone: quarter, village, hamlet, locality (OpenStreetMap and GeoNames names, `tools/build-areas.py`); a home takes the nearest one of its zone | area index `001`–`999` within its zone |
| Plate name | the short name of a code area used in the code (≤ 12 characters, ≤ 2 words, no digit, §2.5); the official name is kept beside it | area |
| Name range | the national number range of one normalised plate name, cut into one frozen block per area (§2.4) | name key + frozen name id (5 digits) |
| Compound | concession / parcelle / compound, walled or not, with a primary gate | area + number |
| Structure | one footprint inside a compound | compound + `.n` |
| Entrance | a gate or door of a compound; `/1` is the primary gate | compound + `/n` |
| Spot | any point, 10 m cell of the zone frame | zone + `E…` `N…` |

## 2. Forms

### 2.1 Machine form

```
GA-<zone>-<area>-<number>-<check>
zone   : the zone key, 3 letters and a letter or digit (model/zones.json)
area   : the area index in its zone, 3 digits
number : 3, 4 or 5 digits, first digit 1-9; length fixed per name
check  : Damm check digit over nameId(5 digits) + zoneIndex(3 digits) + area + number
regex  : ^GA-([1-9][A-Z]{2})-(\d{3})-([1-9]\d{2,4})-(\d)$
```

Parsers MUST accept the form without the check digit (then report it unchecked), MUST treat a wrong check digit as invalid, and MUST treat a code whose number lies in none of that area's blocks (§2.4) as invalid.

### 2.2 Remembered form

- `<plate name> <number grouped>`, e.g. `Etetak 23 67`.
- Implementations MUST NOT produce a remembered form whose plate name breaks the plate limit (§2.5), except a provisional name the commune may still shorten.
- Grouping: 4 digits `AB CD`; 5 digits `AB CDE`; 3 digits `ABC`.
- No letters to learn. No check digit is ever shown to people or asked of them: a digit that carries no meaning for the speaker is the first to be dropped or garbled. A decoder accepts one after a hyphen from systems that send it and verifies it.

Resolving a remembered form uses **no context**: not the user's position, not the zone of the phone, not a town said after a comma. Implementations MUST NOT complete a code from context.

`<name> <number>` → name key (§2.4) → the plate name's range, or, if the key is an alias (an official name, §2.5), the plate name it maps to; a number of the wrong length MUST be refused → the block that holds the number → (zone, area) → machine form. A number in no block (spare or free space) MUST be refused as not issued. One remembered form maps to exactly one machine form in the whole country. Reference: `resolve_remembered`.

### 2.3 Spoken form

In French, digits in groups from the left as phone numbers are read: 12 01 → "douze, zéro un"; 12 181 → "douze, cent quatre-vingt-un".

### 2.4 National name ranges

**Name key** (`name_key`): NFKD, combining marks removed, upper case; `ST`/`ST.` and `STE` as whole words expanded to `SAINT`/`SAINTE`; leading `Q`, `QUARTIER`, `QUARTER`, `HAMEAU`, `VILLAGE DE`, `VILLAGE` followed by a space, hyphen or dot removed; leading `LES `, `LE `, `LA `, `THE `, `L'` removed; every character outside A–Z, 0–9 removed; then, in this order, `TCH→C`, `CH→C`, `DJ→J`, `GH→G`, `PH→F`, `CK→K`, `OU→U`, `W→U`, `GU→G` before I or E; runs of one letter collapsed to one (digits are never collapsed). So Nzeng-Ayong = Nzeng Ayong, Mont-Bouët = Mont Bouet, Mbogha = Mboga, Kotto = Koto.

**Generic labels** (`is_generic`: exactly *village*, *quarter*, *campement*, *camp*, *site*, *ferme*, *farm*, *chantier*, *zone*) are not names and MUST NOT receive a block.

**Blocks.** For every plate-name key, the areas carrying it (at first issue, ordered by zone then index) each get a block of `max(20, ceil(2 × compounds / 10) × 10)` numbers, laid end to end from `10^(d−1)`. `d` is the smallest of 3, 4, 5 with `Σ blocks ≤ floor(0.9 × 9 × 10^(d−1))` (`NAME_SPARE = 0.1`). No number has more than 5 digits. Areas with no compound yet get no block until their first compound. The name id is the 1-based rank of the key in the sorted list at first issue, then append-only. Published in `model/areas/name-ranges.json`; built by `tools/name-ranges.py`.

**Too large.** An area whose own block exceeds `0.9 × 90,000` MUST be split by named quarters before issue. If the blocks of one name together exceed 5 digits, the name keeps its bare form for the blocks that fit in register order and every other area takes the qualified name `<name>-<zone town>`, decided once and listed (`qualified` in `model/stats/name-stats.json`).

**Frozen.** Blocks are frozen at issue and never renumbered. A new area with an existing name, or a full block, takes the next block from `spareFrom` upward (`spare_block`). After first issue an area is renamed only through `model/areas/renames.json` (created with the first rename) and `tools/rename-areas.py` (new name ids appended, every other name untouched, the old numbers retired); `tools/build-register.py --freeze` is for first issue only.

### 2.5 Plate names

Every code area has an **official name** (shown in small print, never required) and a **plate name** (in the code). A plate name MUST have at most 12 characters (NFC; every letter, space, hyphen and apostrophe counts one), at most 2 words (not counting linking words: French `de du des d la le les l et sur en au aux à`, English `of the and on at`) and no digit. Plate names are French (`model/zones.json` `language`). Reference: `plate_names.fits`.

Derivation (`plate_names.derive`, Gabon lists in `tools/name-ranges.py`, applied to the Latin-script words of the official name): documented short form with a source; else clean (brackets, after a slash, generic words `Q`, `Quartier`, `Quarter`, `Lieu-dit`, `Village de`, `Cité`, `Lotissement`, `Zone`, `Secteur`, `Hameau`); if it fits, done; else `Saint` → `St`; else the most distinctive run of whole words that fits, never a word cut, never only weak words (Nouveau, Village, Chefferie, Carrefour, Mission, Institut, Sports...). The area is flagged `needsCouncilChoice` (≤ 3 `plateCandidates`, first one provisional) when there is no clear best candidate, the short form drops a qualifier or a number, it equals a big city elsewhere, another place of the same zone has it, or a hyphenated name is too long. **The zone's chief town instead** (provisionally): when the short form would hold a digit, be a bare generic word, be a derived form of under 3 letters, or be a big city's name elsewhere. Codes are issued under the provisional name, so that no compound waits for a naming decision; the commune may choose once, and the old name stays an alias.

Spelling (`tools/name-ranges.py`): spelling variants of one official name (the same words up to accents, case and punctuation, word breaks kept) take one plate: the one that fits, then the one with the most accented letters, then the one more compounds live under. Words in capitals are written as names unless they are acronyms of companies or bodies (SETRAG, SOMIMA). A documented spelling with a source wins over a map's (`Mont Bouet` → `Mont-Bouët`).

Aliases: an official name whose key differs from its plate name's key decodes to that plate name when it maps to one plate name only; an alias claimed by two plate names, or equal to another plate name, is dropped and listed (`droppedAliases`).

## 3. Check digit: Damm

The Damm table (order-10 weakly totally anti-symmetric quasigroup) is in `ga_engine.DAMM`. `check = fold(DAMM, 0, digits)`. The digits start with the frozen 5-digit name id, then the zone's frozen 3-digit index, so the check binds name, zone, area and number. It detects every single-digit error and every transposition of two adjacent different digits. It lives in the machine form only.

## 4. Zones and frames

- Zone lookup: point-in-polygon (even–odd rule) over `model/units/zones.geojson`; near a boundary the registry decides, not the polygon. A point in no outline is in Gabon when §5 gives it a spot zone (a sliver between départements, the shoreline, an island): it is found by point and issued like any other, its area by §6.6. A point to which §5 gives no zone is outside Gabon.
- Frame (one per zone, frozen in `model/units/frames.json`): `lon0 = floor(minLon × 100) / 100`, `lat0 = floor(minLat × 100) / 100`, `latc = round((minLat + maxLat) / 2, 2)`, `kx = 111320 × cos(latc)` m per degree of longitude, `ky = 110574` m per degree of latitude; digits per axis = 4 if the frame spans less than 99,990 m on that axis, else 5.

## 5. Spot codes

```
encode(lat, lon): E = floor((lon − lon0) × kx / 10), N = floor((lat − lat0) × ky / 10)
                  → "GA-<zone> E<E padded> N<N padded>"
decode:           lon = lon0 + (E + 0.5) × 10 / kx, lat = lat0 + (N + 0.5) × 10 / ky   (cell centre)
```

The zone of a point for the spot grid is the zone whose outline holds it (§4). The outlines are generalised, so a few points in Gabon lie in no outline: in slivers between départements, on the shoreline and on islands. Such a point takes its zone as follows, so that every issued compound has a spot code:

1. Candidates are the zones whose outline lies within 20 km of the point (`SPOT_OUTLINE_M`), the farthest issued compound in no outline being 18.4 km from one. A point farther from every outline is outside Gabon.
2. Among the candidates whose frame holds the point (0 ≤ E < 10^dx and 0 ≤ N < 10^dy), the zone with the nearest outline: the least distance from the point to an edge of any ring of the zone's outline, with longitude differences multiplied by cos(latitude of the point) (`ga_engine.edge_d2`). Ties go to the lower zone key.
3. If no candidate's frame holds the point, the candidate with the nearest outline among those whose frame the point lies at most 100 cells (1,000 m) beyond on each axis (E and N each between −100 and 10^d + 99), ties to the lower key; the point takes that frame's nearest cell (E and N clamped to 0 … 10^d − 1). No issued compound needs this step; it keeps a point just beyond a frame from being refused.
4. Otherwise the point MUST be refused.

Frames never move and never gain digits, because either would change spot codes already published. Decoding needs no lookup: a spot code names its zone, and its cell centre is decoded in that zone's frame. Example: Quartier Louis, Libreville (0.4085002 N, 9.4314043 E) → `GA-1LV E0794 N0757`; Moka, Komo-Mondah, a compound on an island 18.4 km from the nearest outline (0.8104524 N, 9.3792151 E) → `GA-1KM E0881 N6971`.

## 6. Official addresses first, then the registry

### 6.0 Official addresses

Where the government or a council gives an address, it is shown first, exactly as written, and every compound keeps its N-Ways code beside it:

- Libreville: a door number of the commune's plan (street and number, as on the plate), once shared by the commune, mapped in OpenStreetMap from the plate or confirmed by residents, is shown first. Until then, the named street within 30 m of the compound comes first (`Avenue Joseph Deemin, Libreville`, `coverage = official-street`).
- La Poste: a postcode, once one is published, sits beside every address of its zone (a reserved field in `model/zones.json`). A BP is never an address.
- Official changes always win; N-Ways reports suspected errors to the holder and never edits official records.

### 6.1 Inputs

OpenStreetMap buildings (ODbL) and the Google Open Buildings / Microsoft footprints that no OpenStreetMap building overlaps (via Overture Maps; CC BY 4.0 / ODbL); OSM walls, fences, hedges, gates and entrances; N-Ways gated compounds and gates; N-Ways places.

**The border decides.** A Gabon code is only ever given to a building whose entrance lies inside Gabon's national border, OpenStreetMap's admin_level 2 boundary, or within 300 m of it (`BORDER_M`: the line's own accuracy, gates on the line). Zone outlines from other sources (§4, geoBoundaries, GADM and the like) may spill over the border into a neighbouring country; they never decide. A footprint whose centre is outside the border is dropped before grouping, and a compound whose point lies more than 300 m outside it gets no code. The border ships in `engine/data/border.json`, simplified to 50 m (`toleranceM`); measured against that line on the local plane, a point is refused when it lies more than 300 − 50 − 5 = 245 m outside it, so no point more than 300 m outside the true border is ever coded and no point inside it is refused (`reference/ga_border.py`).

### 6.2 Group structures into compounds (before any numbering)

`ga_engine.group_footprints`, one code area at a time, footprints in stable-id order, true outline gaps:

1. **enclosure** (0.85): structures whose centre lies in the same smallest closed barrier polygon of ≤ 6,000 m².
2. **annex** (0.60): a structure < 25 m² joins the nearest structure ≥ 25 m² within 8 m.
3. **hut cluster** (0.50; not in Libreville and Bendje, `1LV` and `8PG`): huts < 40 m² that belong to no house, with gaps ≤ 3 m, at most 25 per compound: a cluster never joins two houses.
4. **single** (0.40).

### 6.3 Code areas

Each footprint is assigned to the nearest named place of its zone (local metres, ties to the lower index; `tools/assign-areas.py`). Area indices are alphabetical at first issue, then append-only. The area's frame is the box of its footprints' centres widened by 0.0005° on every side, frozen.

### 6.4 Numbers

```
range    = the area's block [lo, hi] in its name's national range (§2.4)
main     = first two thirds of the block; tail reserve = last third
order    = compounds sorted by Hilbert index (order 16) of their ordering point in the area's frame, ties by id
step     = max(1, floor(|main| / floor(N × 1.5)))
number_i = lo + i × step
```

### 6.5 New compound (provisional number)

Let `a` and `b` be the numbers of the new point's neighbours on the area's curve (every issued compound counts, retired ones included, ordered by curve position then key; `a = lo − 1` when none precedes it, `b` = the first number of the tail reserve when none follows) and `m = floor((a + b) / 2)`.

1. The free number `x` with `a < x < b`, below the tail reserve, nearest `m`: `m`, then `m − 1`, `m + 1`, `m − 2`, …
2. Else the lowest free number of the tail reserve.
3. Else the lowest free number of the area's later blocks.
4. Else a new block from the name's spare (`spare_block`): it starts above `spareFrom` and above every block of the name, and holds `max(20, ceil(2 × (N + 1) / 10) × 10)` numbers, `N` the area's issued compounds. An area with no block yet takes a block of 20 the same way. When the name's range is used up, the commune chooses a qualifier first.

A number is never given twice: retired numbers stay used.

### 6.6 Issuing a code for a new compound

One issuer per country gives codes (a second issuer would see the same free number and give it to another home). A request carries a point, and optionally the building outline or the code of the compound it is another door of.

- **In Gabon.** Refused when the point is outside Gabon (§4): in no outline, and given no spot zone by §5; and refused when it lies more than 300 m outside the national border (§6.1, "The border decides"), even when a zone outline or a spot zone reaches it. A moved entrance follows the same border rule.
- **Already coded.** Refused when a live compound lies within 3 m of the point (its entrance, or a footprint holding the point), or when the outline covers more than half of an existing structure.
- **Outline.** Between 6 m² and 20,000 m².
- **Area.** Another door takes its compound's area and lies within 80 m of its entrance. Otherwise: the area of the nearest live code within 250 m (a new house joins its neighbours); else the code area of the point (§6.3); else the numbered area whose place point is nearest.
- **Result.** The number of §6.5, the forms of §2, `status = provisional`, `issued = on-demand`.

## 7. Stability

A number is never reused or moved. Demolished: retired. Split: the part with the larger floor area keeps the code. Merge: the oldest code survives, the other stays an alias. Renames change only the alias table or follow §2.4 "Frozen".

## 8. Profiles

Every structure carries a use class with its confidence and source, footprint, perimeter, floors (OpenStreetMap `building:levels`, else `height` / 3; the Google/Microsoft height is a rendering filler and never gives floors) and a status. A home never carries a name.

## 9. Confirmation

Arrivals at the gate, residents' answers ("these buildings are one home", "this is the gate"), businesses claiming their shop and partners' cross-references confirm a grouping, a gate or a provisional code without anyone queuing it for review.

## 10. Privacy and safety

Published registry rows carry no person data: a code, its area, its entrance point, its spot code and its building profile (use, kind, structures, floor area), never a name, a household or a phone. The registry publishes every compound of every zone. The `alert_zone` column of `areas.csv` records whether travel advice names a zone (none does: the UK FCDO advises against travel to no part of Gabon), as context for safety guidance; it never withholds a row.

## 11. Conformance

An implementation conforms when it reproduces every vector in `reference/vectors.json` (name keys, machine, remembered and written forms, decodings with and without check digits, refusals, spot codes (also of points in no outline: every issued compound among them, slivers, the sea, the frames' nearest cells and refusals), the Hilbert curve and the numbering of a real area with new homes).
