# Governance / Gouvernance — N-Ways Addresses, Gabon

Codes were issued on 21 October 2026 and the repository is public. This file sets out who decides what, the rules every change follows, and how stewardship can pass to a Gabonese body.

## What these codes are

- They are **N-Ways addresses**, not official addresses or postcodes. The repo never calls them "official", "national" or "postal" codes unless a Gabonese authority adopts them in writing.
- **A code is an address, not a land title.** It is no evidence of ownership, occupation or boundaries. Only a titre foncier, with ANUTTC's survey plan, is that.
- Every compound has a code. Where an official address exists, it is shown first, exactly as written, and the code sits beside it:
  - Libreville's street plates and door numbers;
  - a postcode, if one is ever published.

  A P.O. box (BP) is a mailbox, not an address: it is kept as text only.

## Roles today

| Role | Who | Decides |
|---|---|---|
| Maintainer | N-Ways (engineering) | Engine, file formats, releases |
| Data steward | N-Ways (maps) | Zones, area names, the registry, corrections |
| Privacy lead | N-Ways (data protection) | What is public; requests to make a home private; APDP filings |
| Licensor | N-WAYS LIMITED (board) | Partnerships, designation of an issuer, hand-over (licences: Apache 2.0, ODbL 1.0, CC BY 4.0, LICENSING.md) |
| Issuer | N-WAYS LIMITED, until the State designates another body | The only source of new codes (see below) |

## Rules for changes

1. **Issued codes never change.** A pull request that moves, renumbers or reuses an issued code is rejected.
   - Merged compounds become aliases.
   - A split keeps the old code on one part and gives new numbers from the gap.
   - Demolished compounds are retired.
2. **Zones and their indices are append-only.** If the State redraws a département, existing codes keep their zone. Only the place name shown beside the code changes.
3. **Area names** come from what people already say. They change only when the community asks, and the old name stays as an alias.
   The plate name in the code has at most 12 characters and 2 words, no digit. Where the rule could not choose one (`needsCouncilChoice`), codes are issued under a provisional name, so that no compound waits for a naming decision; the commune may choose once, and the old name stays an alias. After issue an area is renamed only through `model/areas/renames.json` and `tools/rename-areas.py` (`engine/SPEC.md` §2.4).
4. **Corrections settle by consensus**, as N-Ways map corrections do: confirmations from arrivals, deliveries and residents.
   - Nothing waits in a manual review queue.
   - Disputes between neighbours over a gate or outline freeze that compound's outline until it is resolved. The code itself stays.
5. **Openness.** The open registry publishes every compound of every département, with no person data (engine/SPEC.md §10). Travel advice (the UK FCDO advises against travel to no part of Gabon) informs the safety guidance that accompanies the codes; it does not decide what is published.
6. **One issuer.** Numbers come from shared national ranges, so two issuers would give the same number to two homes. Only the designated issuer gives new codes; every other deployment of the server (`server/`) runs read-only. A change of issuer happens on a set day: the outgoing issuer stops, exports its registry, and the incoming issuer imports it and starts from there.

## Institutions concerned

| Partner | Why |
|---|---|
| **La Poste SA** | National postal operator; P.O. boxes. Store any postcode, never compete. |
| **Ministère de l'Économie numérique** and **ARCEP** | Ministry and regulator for posts and telecommunications |
| **Commune de Libreville**, then Owendo, Akanda, Port-Gentil, Franceville and the other communes | Street naming and door numbering (Libreville's programme since 2012), area names, plates |
| **INC** (Institut National de Cartographie) | National mapping agency, base maps |
| **ANUTTC** | Cadastre and titres fonciers (for plot outlines; codes ≠ titles) |
| **APDPVP** (Loi 001/2011, amended by Loi 025/2023) | Data protection; declarations and transfers abroad |
| **Direction générale de la statistique** | Census (RGPL 2026, 3,322 enumeration areas); locality names |
| **ANINF** | The State's digital agency |
| Emergency services, couriers, banks, utilities | Users of the codes |

## Hand-over

The repository is built so that it can move to a Gabonese body (La Poste, INC or a commune) without forking the engine:
- the zone list, area names, registry and rules are all in this repository;
- the server in `server/` serves the registry and issues codes by the same rules, so the body can run it on its own infrastructure on the day it takes over (server/README.md, "One issuer");
- the maintainers' list and these rules transfer with it.

Proposals and corrections follow [CONTRIBUTING.md](CONTRIBUTING.md); problems with security or personal data go to [SECURITY.md](SECURITY.md).

N-Ways would then keep a mirror, and the N-Ways app would follow the national body's decisions.
