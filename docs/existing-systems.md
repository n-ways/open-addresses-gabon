# Gabon: existing postal and address systems

Checked 17–18 October 2026. "Fetched" means the page was opened and read on that date; "search only" means it was seen in search results and not opened.

## Verdict

- **Postcodes: no, not in use.** The UPU addressing sheet for Gabon (dated July 2002) shows a two-digit number before the town and a delivery-office number after it ("05 TCHIBANGA 01"). It calls this line "postcode and delivery office". No list of these codes has been published, and no current source shows them in use. In practice mail goes to post-office boxes (BP).
- **Street addresses: partial, Libreville only, unfinished.** Libreville's commune started naming streets and numbering doors in 2012–2014. The work was relaunched in July 2021 and was still incomplete in May 2024. No other town has a programme we could find, and there is no national register or law on addressing.
- **Consequence for N-Ways.**
  - Gabon has no national address code, so N-Ways Gabon codes fill the gaps.
  - Where Libreville's street plates and door numbers exist, **they are the address**: N-Ways shows them first, exactly as written, with the compound's code beside them (see Precedence below).
  - A BP stays a BP: a mailbox, not a place.

## Postal operator and P.O. boxes

| Finding | Source | Status |
|---|---|---|
| Home delivery example: "Mademoiselle Alice NGANGA / CRP – MOULENGUI-BINDZA / 05 TCHIBANGA 01 / GABON". The line is labelled "postcode and delivery office" ("code postal et bureau de distribution"). | UPU, *Gabon* addressing sheet (07/2002), https://www.upu.int/UPU/media/upu/PostalEntitiesFiles/addressingUnit/gabEn.pdf and …/gabFr.pdf | Fetched |
| P.O. box example: "BP 13210 / 01 LIBREVILLE–GROS-BOUQUET 03". The contact is the Direction de la Poste, BP 20000 Libreville. | same | Fetched |
| The OPT was dissolved in 2001 and Gabon Poste SA took over (Law 006/2001). Gabon Poste was liquidated in 2006 and La Poste SA took over its activities. | https://en.wikipedia.org/wiki/La_Poste_(Gabon) | Fetched |
| La Poste S.A and ANPI-Gabon (the investment agency) signed an agreement so companies can get a P.O. box online. A box serves as a company's legal domicile. | Gabonreview, 13 Aug 2020, https://www.gabonreview.com/boite-postale-en-ligne-lanpi-gabon-et-la-poste-s-a-signent-une-convention/ | Fetched |
| No postcode data exists for Gabon; the format is "N/A". | datahub.io (postal-codes-ga), Smarty format list | Search only |
| La Poste SA's own website (laposte.ga) did not resolve. | — | Not reachable |

**How to read the UPU format.** In the UPU examples, "01" comes before Libreville (Estuaire) and "05" before Tchibanga (Nyanga). These are the numbers ISO 3166-2 gives Gabon's provinces (GA-1 Estuaire … GA-9 Woleu-Ntem). The number after the town ("03", "01") identifies the delivery office. The UPU sheet does not say the prefix is the province number; that is our inference. **The N-Ways Gabon code keeps this province number as the first digit of every zone key**, so a postal clerk reading "1LV" sees Estuaire, as on a 2002 envelope.

## Street addressing

| Finding | Source | Status |
|---|---|---|
| On 8 July 2021 interim mayor Eugène Mba relaunched phase 2 of Libreville's addressing project. The project began in 2014 under Rose Christiane Ossouka Raponda and then stopped for about seven years. Funding: 480 million FCFA from the AIMF and the EU. Of 6,000 street plates made, 3,900 were still to be put up; of 60,000 door numbers needed, 55,000 were still to be placed. | Gabonmediatime, 9 Jul 2021, https://gabonmediatime.com/gabon-linterimaire-eugene-mba-relance-le-chantier-dadressage-de-la-capitale/ | Fetched |
| The same relaunch, reported in the press. | Gabonactu, 8 Jul 2021, https://gabonactu.com/blog/2021/07/08/eugene-mba-relance-le-projet-dadressage-de-la-commune-de-libreville/ | Fetched |
| Libreville is still "la capitale aux rues sans nom". The project started in 2012, aimed to name 3,650 roads, and "ne semble pas être entré dans les mœurs". People give directions such as "derrière la prison, à gauche … la boutique du Malien". | Le360 Afrique, 28 May 2024, https://afrique.le360.ma/societe/jhabite-derriere-la-prison-a-gauche-de-la-boutique-libreville-la-capitale-aux-rues-sans-nom_PPVZORV7HJGXHEVXSKXYDVWEWI/ | Fetched |
| The Libreville council adopted a deliberation on naming and numbering its streets in August 2015. | L'Union archives, no. 11912, 26 Aug 2015 | Search only |
| Decree 864 of 23 Oct 2013 set the boundaries of Libreville's arrondissements. | press reports | Search only |
| Libreville numbering scheme described in a thesis: roads parallel to the coast get odd numbers, perpendicular roads even numbers; recommends metric door numbers (distance from the start of the street). | memoireonline.com (10/17/10148) | Search only |
| Nothing found for Port-Gentil, Franceville, Owendo or Akanda; no 2025–2026 addressing news; no ANINF (the national digital agency) or other digital address app. | — | Searches done 18 Oct 2026 |

**Precedence.** Where the government already has an address, N-Ways uses the government's data and never offers a competing address.

- **Doors with a plate.** Wherever a door has a municipal street plate and door number, that address is primary. It is stored and shown **exactly as written**, first on the card; the compound keeps its N-Ways code beside it, since every compound has a code.
- **Where the data comes from:**
  - the Commune de Libreville's technical services, which may hold a register. We have not seen one, and its format and terms are unknown and to be requested;
  - OpenStreetMap `addr:street` + `addr:housenumber` traced from the plates. In the 2026 extract, the Libreville–Owendo–Akanda area has 3,945 doors with both on 623 streets, 911 of them tagged `source=survey`, under ODbL;
  - plate photos taken by N-Ways users at the gate.
- **Coverage** is tracked street by street (`engine/SPEC.md` §6.0).
- **Doors numbered later.** If a door is numbered after an N-Ways code was given, the municipal address becomes primary and the N-Ways code stays beside it, unchanged.
- **P.O. boxes.** A BP is not an address.

## Open data and OpenStreetMap

N-Ways research found no open address register (17 Oct 2026). In the OSM extract of 17 Oct 2026, the Libreville–Owendo–Akanda box (9.38–9.56°E, 0.28–0.62°N) holds 4,049 objects with `addr:housenumber` and 5,654 with `addr:street`; 3,945 have both, on 623 distinct streets, and 911 of those carry `source=survey`. These door addresses are the ones shown first on the codes of their compounds. The earlier N-Ways count for the whole country, made with Overpass, found that OpenStreetMap had 3,803 objects with `addr:housenumber`, 5,118 with `addr:street` and 303 with `addr:postcode`. The postcode values look like P.O. box numbers ("12035", "315"), not postcodes. Query: `area["ISO3166-1"="GA"][admin_level=2]->.a;nwr["addr:housenumber"](area.a);out count;`. The two counts were made with different tools on different dates, so they are not directly comparable: the osmium export may count a building's way and its entrance node separately.

## Administrative structure (used by the model)

- **9 provinces** (ISO 3166-2 GA-1 to GA-9; the UK PCGN writes GA-01 to GA-09). The PCGN *Toponymic Factfile* (Sep 2023, https://www.ecoi.net/en/file/local/2136418/Gabon_Toponymic_Factfile.pdf, fetched) says there are "9 provinces … subdivided into 50 departments".
- OpenStreetMap had **49** département polygons on 18 Oct 2026. Libreville appears as a département-level unit. The fiftieth département in the PCGN count is still to be identified: it may be Akanda or Owendo, which became separate units after 2013, or a split not yet mapped (**unverified**).
- No territorial reform had been enacted by October 2026; press commentary calls redrawing the map a pending challenge of the Fifth Republic (search only).

## Population

- 2013 census (RGPL): 1,811,079 people; Libreville 703,940; Estuaire 895,619, about 49.5% (secondary sources; official report at https://instatgabon.org/uploads/folder_1/RESULTATS-GLOBAUX-RGPL2013-OK_DECEMBRE-2015-1.pdf, search only).
- 2026 census: 3,518,621 inhabitants, a total the Constitutional Court approved on 27 August 2026 (Gabonmediatime, 27 Aug 2026, https://gabonmediatime.com/recensement-2026-le-gabon-compte-desormais-35-millions-dhabitants/, fetched), with Estuaire holding "près de 60 %" (Gabonmediatime, 16 Sep 2026, https://gabonmediatime.com/gabon-la-population-a-augmente-de-943-entre-2013-et-2026/, fetched). The census was organised in 3,322 enumeration areas (Gabonreview, 2 Sep 2026, fetched). The official tables by province had not been published by October 2026.

## Data protection

- **Law:** Loi n° 001/2011 of 25 September 2011 on personal data protection, amended by **Loi n° 025/2023 of 12 July 2023** (promulgated by Décret n° 166/PR of the same day). Text at https://www.afapdp.org/wp-content/uploads/2023/12/Gabon-Loi-025-2023-du-12-juillet-2023-portant-modification-de-la-loi-001-2011-du-25-septembre-relative-a-la-protection-des-donnees-a-caractere-personnel.pdf (fetched).
- **Authority:** the Autorité pour la protection des données personnelles et de la vie privée (**APDPVP**), an independent administrative authority that replaced the CNPDCP in 2023: https://www.apdpvp.ga/ (fetched). It is in Haut de Gué-Gué, Libreville.
- **Duties:** processing needs a prior declaration. Transfers out of Gabon are restricted, and N-Ways' servers are outside Gabon (N-Ways country research, after DLA Piper's *Data Protection Laws of the World*). Gabon ratified the AU Malabo Convention on 17 Oct 2024.

## Land and cadastre (for importing plot outlines)

- **ANUTTC** (Agence nationale de l'urbanisme, des travaux topographiques et du cadastre), https://www.anuttc.ga (fetched). Its services include splitting and merging titres fonciers, re-marking boundaries ("rebornage") and correcting boundaries. It offers no public geoportal or open parcel data.
- **Projection:** EPSG:5523, *WGS 84 / Gabon TM 2011* (Transverse Mercator, origin 0°N 11.5°E), is scoped by EPSG for "cadastre, engineering survey, and topographic mapping": https://epsg.io/5523 and https://epsg.io/5522 (fetched). Older plans may use M'Poraloko 1951 / UTM 32S (**unverified**).
- **Unverified:** where titres fonciers are registered (believed to be the Conservation de la propriété fonciere), whether an order of géomètres-experts exists and on what legal basis, and how much of the country the cadastre covers.

## Mapping agency

The INC (Institut National de Cartographie, created 1983) is the reference producer of base maps (search only; no website reachable).

## Open algorithm alternatives

Open Location Code (Plus Codes, Apache-2.0, https://github.com/google/open-location-code) works offline and costs nothing. N-Ways' spot codes can be converted to and from a Plus Code, but the remembered Gabon home code is designed to be easier to say and recall (see `model.md`).

## Short place names people already use

The plate name (the short name in the home code, `model.md` §2) takes a documented form people already use where one exists:

- **Mont-Bouët** for the quarter mapped as "Mont Bouet": the market and quarter as the press and the city write it (Gabonreview and Gabonmediatime on the Marché de Mont-Bouët). This form is applied.
- **Oloumi** for the Zone Industrielle d'Oloumi in Libreville: the press calls the area and its market simply "Oloumi" (Gabonreview, https://www.gabonreview.com/oloumi-les-commercants-boudent-linterieur-du-marche-la-mairie-sevit/; Gabonmediatime, https://gabonmediatime.com/libreville-le-gen-oligui-nguema-inaugure-le-marche-national-doloumi/; search only). Another area of Libreville already carries the plate name Oloumi, so the industrial zone's plate is "Industrielle"; a later rename follows `engine/SPEC.md` §2.4.
- **Lastourville** for Lastoursville: the town's other established spelling, also the airport's name (https://en.wikipedia.org/wiki/Lastoursville, https://en.wikipedia.org/wiki/Lastourville_Airport; search only). The plate keeps the spelling of the map, Lastoursville, as a provisional name the commune may confirm or change.

Other names that need a choice carry a provisional plate name, listed with their candidates in `model/areas/name-ranges.json` (`needsCouncilChoice`); their codes are issued and their numbers never change.
