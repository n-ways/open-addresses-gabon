# The N-Ways model for Gabon: design notes

Design notes: why each choice fits Gabon. The rules themselves are in [engine/SPEC.md](../engine/SPEC.md) (normative) and, with every formula worked through on real codes, in the paper ([paper.md](paper.md), [paper.fr.md](paper.fr.md)), which also measures the result. The designs considered and set aside are in the paper's section on rejected designs.

## 0. The rule above all: official addresses first

Where the State or a commune gives an address, N-Ways shows it first, exactly as written: the State's address is the address, and a second scheme must never compete with it. Every compound also has its N-Ways code, which never changes. Today that means the doors of Libreville that carry a plate and number of the commune's plan, once known (OpenStreetMap holds 3,945 of them in Libreville, Owendo and Akanda). Before that, the named street within 30 m of the compound is shown first (37,622 compounds); a door number replaces it once known. A postcode fills a reserved field the day one is published.

## 1. Easy to remember, effortless to get

- **What people already say** is a quarter or village name and a landmark, and phone numbers in pairs. So a code is a **plate name and a number of three to five digits**, said in pairs: Louis 12 01.
- **No context needed.** Every area with the same plate name shares one national range, cut into frozen blocks of twice its compounds; "name number" is unique in Gabon with no town after it (18 Mandjis, 11 Alénés, one range each).
- **At most five digits**, because short-term memory holds about four chunks (Cowan, 2001): four or five digits read in two groups after a known name fit, a sixth adds a third group. Every name's blocks fit 81,000 numbers with a tenth spare; the largest area, Le Transfo in Port-Gentil, uses 26,070.
- **No check digit for people**: a digit that means nothing to the person saying it is the first to be dropped or garbled, so the Damm check lives in the machine form (`GA-1LV-070-1201-1`), for systems that copy codes and can verify them.
- **Getting it** is one tap in the app ("Get my code"), at home or by tapping the compound on the map.

## 2. Plate names

At most 12 characters and 2 words, no digit, in French. Gabon's names often join two village names ("Moussa-Moukougou") or pair a landmark word with the place's name ("Mongo Milando"), so a list of ordinary French words keeps the proper name (Milando) and never the landmark word. One spelling per name: accents kept (Akébé-Ville), capitals written as names (Mimboti) except companies' acronyms (SETRAG), documented spellings first (Mont-Bouët). Where nothing fits, the area carries its département's chief town until the commune chooses (252 areas). The full official name is always an alias.

## 3. Zones: the 49 départements

The département is stable and is the machine form's zone and the frame of the spot grid. Its key starts with the province's ISO number, the number the UPU's 2002 sheet puts before the town (1LV, 8PG, 9OY). Provinces are looked up from a compound's position and are never part of a code.

## 4. Spot codes: a 10 m numeric grid

Any point has a spot code on a 10 m grid over its département's frozen frame: `GA-1LV E0794 N0757`, digits only, four per axis (five in départements wider than 99.99 km), decoding to within 7.1 m.

The département outlines are generalised, so 80 issued compounds lie in no outline: in slivers between départements, on the shoreline and on islands up to 18.4 km offshore. A point in no outline takes, among the départements whose outline lies within 20 km, the one with the nearest outline whose frame holds the point (ties to the lower key); if no such frame holds it, the nearest cell of a frame at most 1,000 m away. Every issued compound therefore has a spot code. Frames never move, because moving one would change spot codes already published; a point farther from Gabon is refused.

## 5. Compounds, not footprints

A code belongs to a compound and leads to its gate. Footprints are grouped before numbering: a mapped wall, fence or hedge makes one compound; an annex under 25 m² joins the nearest house within 8 m; outside Libreville and Bendje (Port-Gentil), huts under 40 m² at most 3 m apart form one compound of up to 25. Nothing else is merged: merging two codes later costs nothing, splitting a wrong merge gives a household a new code. Residents' answers in the app ("one home", "the gate is here") do the rest.

## 6. Building profile

Every structure carries a use class with its confidence and source (OpenStreetMap type, tags, N-Ways places inside, size, else residential by default), its size, floors where known, and a status. Homes never carry names.

## 7. Numbering

Inside an area, compounds are numbered along a Hilbert curve over the area's frozen frame, so neighbours have neighbouring numbers, with gaps for new homes and a tail reserve of a third of the block. Measured on 350,235 pairs of consecutive numbers, the Hilbert order puts them 35.4 m apart on average, against 46.6 m for a Morton curve and 56.3 m for a banded raster. Blocks never move, shrink or renumber; a full block takes an extension block of its name.

## 8. Safety

The open registry publishes every compound of every département: its code, entrance point and building profile, and nothing about the people who live there. Travel advice (the UK FCDO advises against travel to no part of Gabon) informs the safety guidance given with the codes, not what is published.

## 9. Stability and hand-over

There is one issuer at a time (N-WAYS LIMITED, or a body the State designates; see server/README.md), because two issuers would give one number to two homes; codes are never reused; a commune may rename an area once (the old name stays an alias). The repository can be handed to the State or a body it names under its open licences.
