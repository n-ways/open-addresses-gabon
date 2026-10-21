# Sources

Access dates are 17–18 October 2026. **Fetched** means the page was opened and read. **Search only** means it was seen in search results but not opened. **N-Ways research** means it was taken from N-Ways' country research notes of 17 October 2026 and not opened again.

## Postal system

| Source | URL | Status |
|---|---|---|
| UPU, Gabon addressing sheet (EN), 07/2002 | https://www.upu.int/UPU/media/upu/PostalEntitiesFiles/addressingUnit/gabEn.pdf | Fetched |
| UPU, Gabon addressing sheet (FR), 07/2002 | https://www.upu.int/UPU/media/upu/PostalEntitiesFiles/addressingUnit/gabFr.pdf | Fetched |
| La Poste (Gabon), history OPT → Gabon Poste → La Poste SA | https://en.wikipedia.org/wiki/La_Poste_(Gabon) | Fetched |
| Gabonreview, online P.O. boxes, La Poste S.A × ANPI-Gabon, 13 Aug 2020 | https://www.gabonreview.com/boite-postale-en-ligne-lanpi-gabon-et-la-poste-s-a-signent-une-convention/ | Fetched |
| datahub.io, postal codes GA: no data | https://datahub.io/logistics/postal-codes-ga | Search only |
| La Poste SA website | laposte.ga | Did not resolve |
| Postal and telecoms regulator | https://www.arcep.ga/ | HTTP 403 on 18 Oct 2026 (site exists; name and remit unverified) |

## Addressing

| Source | URL | Status |
|---|---|---|
| Gabonmediatime, Libreville addressing relaunched, 9 Jul 2021 | https://gabonmediatime.com/gabon-linterimaire-eugene-mba-relance-le-chantier-dadressage-de-la-capitale/ | Fetched |
| Gabonactu, same relaunch, 8 Jul 2021 | https://gabonactu.com/blog/2021/07/08/eugene-mba-relance-le-projet-dadressage-de-la-commune-de-libreville/ | N-Ways research |
| Le360 Afrique, "Libreville, la capitale aux rues sans nom", 28 May 2024 | https://afrique.le360.ma/societe/jhabite-derriere-la-prison-a-gauche-de-la-boutique-libreville-la-capitale-aux-rues-sans-nom_PPVZORV7HJGXHEVXSKXYDVWEWI/ | Fetched |
| L'Union archives no. 11912, council deliberation on street naming, 26 Aug 2015 | lunion-archives.org | Search only |
| Thesis on Libreville street numbering | https://www.memoireonline.com/10/17/10148/ | Search only |

## Administration, population

| Source | URL | Status |
|---|---|---|
| UK PCGN, Gabon Toponymic Factfile (Sep 2023): 9 provinces, 50 departments | https://www.ecoi.net/en/file/local/2136418/Gabon_Toponymic_Factfile.pdf | Fetched |
| ISO 3166-2:GA | https://en.wikipedia.org/wiki/ISO_3166-2:GA | Search only |
| RGPL 2013 results (official) | https://instatgabon.org/uploads/folder_1/RESULTATS-GLOBAUX-RGPL2013-OK_DECEMBRE-2015-1.pdf | Search only |
| Gabonmediatime, RGPL 2026: 3,518,621 inhabitants, Estuaire about 60%, 16 Sep 2026 | https://gabonmediatime.com/gabon-la-population-a-augmente-de-943-entre-2013-et-2026/ | Fetched |

## Data protection

| Source | URL | Status |
|---|---|---|
| Loi n° 025/2023 of 12 Jul 2023 amending Loi n° 001/2011 (text) | https://www.afapdp.org/wp-content/uploads/2023/12/Gabon-Loi-025-2023-du-12-juillet-2023-portant-modification-de-la-loi-001-2011-du-25-septembre-relative-a-la-protection-des-donnees-a-caractere-personnel.pdf | Fetched |
| APDPVP website | https://www.apdpvp.ga/ | Fetched |
| DLA Piper, data protection in Gabon | https://www.dlapiperdataprotection.com/?t=law&c=GA | N-Ways research |

## Land, cadastre, geodesy

| Source | URL | Status |
|---|---|---|
| ANUTTC: services (titles, rebornage, boundaries) | https://www.anuttc.ga | Fetched |
| EPSG:5523, WGS 84 / Gabon TM 2011 (cadastre scope) | https://epsg.io/5523 | Fetched |
| EPSG:5522, Gabon TM 2011 projection | https://epsg.io/5522 | Fetched |
| M'Poraloko 1951 / UTM 32S on older plans | — | Unverified |
| INC (Institut National de Cartographie), created 1983 | geospatial country profile | Search only |

## Data used for the statistics

| Data | Path (in the N-Ways data folder, `NWAYS_ROOT`) | Licence |
|---|---|---|
| OpenStreetMap buildings, admin boundaries, barriers, places (extract of 17 Oct 2026) | `data/osm/gabon-latest.osm.pbf`, `data/detail/countries/gabon/` | ODbL 1.0 |
| Google Open Buildings and Microsoft footprints OSM lacks (with ML height `h`), via Overture Maps | `data/detail/ml/GA.parquet` | CC BY 4.0 / ODbL |
| N-Ways places (OSM, Overture, Foursquare, healthsites, AllThePlaces) | N-Ways database `places` | per `data/places/LICENCES.json` |
| N-Ways routing compounds and gates | `data/valhalla/compounds.geojsonseq`, `gates.geojsonseq` | derived from OSM (ODbL) |
| GeoNames populated places | `data/places/geonames/GA.txt` | CC BY 4.0 |
| N-Ways regions | N-Ways database `regions` | from OSM (ODbL) |

## Methods

| Source | URL |
|---|---|
| Open Location Code (Plus Codes), Apache-2.0 | https://github.com/google/open-location-code |
| H. M. Damm, *Totally anti-symmetric quasigroups for all orders n ≠ 2, 6*, Discrete Mathematics 307(6) (2007), 715–729 | https://doi.org/10.1016/j.disc.2006.05.033 |
| Hilbert curve ordering (standard algorithm, as used in spatial indexing) | — |

## Plate names (documented short forms)

Short forms people already use, and whether the plate name takes them (`tools/name-ranges.py → KNOWN`; `docs/existing-systems.md`).

| Official name | Short form | Source | URL | Status | Used on the plate |
|---|---|---|---|---|---|
| Mont Bouet (Libreville) | Mont-Bouët | Gabonreview and Gabonmediatime on the Marché de Mont-Bouët | https://www.gabonreview.com, https://gabonmediatime.com | Search only | yes |
| Zone Industrielle d'Oloumi (Libreville) | Oloumi | Gabonreview, "Oloumi : les commerçants boudent l'intérieur du marché, la mairie sévit" | https://www.gabonreview.com/oloumi-les-commercants-boudent-linterieur-du-marche-la-mairie-sevit/ | Search only | no: another Libreville area is Oloumi; the plate is Industrielle |
| Zone Industrielle d'Oloumi (Libreville) | Oloumi | Gabonmediatime, inauguration of the "marché national d'Oloumi" in the zone, 31 Jan 2025 | https://gabonmediatime.com/libreville-le-gen-oligui-nguema-inaugure-le-marche-national-doloumi/ | Search only | as above |
| Lastoursville | Lastourville | Wikipedia, "Lastoursville" (also spelled Lastourville) | https://en.wikipedia.org/wiki/Lastoursville | Search only | no: the map's spelling stays, as a provisional name |
| Lastoursville | Lastourville | Wikipedia, "Lastourville Airport" (IATA LTL) | https://en.wikipedia.org/wiki/Lastourville_Airport | Search only | as above |

No documented short form was found for "Cité de la Démocratie" (press uses the full name, e.g. https://www.gabonreview.com/infrastructures-la-tour-de-libreville-et-la-cite-de-la-democratie-au-coeur-de-la-vision-presidentielle/, search only); the plate rule gives it "Démocratie" by dropping the generic word "Cité".

## Cited in the paper

The paper's full reference list, with authors, dates, DOIs and addresses, is [`docs/paper/references.bib`](docs/paper/references.bib). Every entry was checked against its source on 21 October 2026 (DOIs against Crossref). The sources that carry figures used in the paper:

| Source | What the paper takes from it | URL | Status |
|---|---|---|---|
| M. Mondjo Mouega, Gabonmediatime, 27 Aug 2026 | census total 3,518,621, approved by the Constitutional Court on 27 Aug 2026 | https://gabonmediatime.com/recensement-2026-le-gabon-compte-desormais-35-millions-dhabitants/ | Fetched |
| D.-C. Dzonteu, Gabonreview, 2 Sep 2026 | 3,322 enumeration areas; geolocation used in the fieldwork | https://www.gabonreview.com/35-millions-dhabitants-en-2026-au-gabon-pres-dun-habitant-sur-trois-est-de-nationalite-etrangere/ | Fetched |
| Government of Canada, travel advice for Gabon | police 177, medical assistance 1300 | https://voyage.gc.ca/destinations/gabon | Fetched |
| Selectra, Gabon, updated 21 Jul 2026 | fire 18 from a landline, 112 from a mobile | https://selectra.info/telecom/international/voyage-gabon | Fetched |
| L. R. Alomo, *L'Union* no. 13710, 30 Aug 2021, p. 12 | dialling 1300 returned an invalid-number message; crews said they could not reach informal quarters | https://www.lunion-archives.org/web.11/dmdocuments/N13710-30-08-2021-012.pdf | Fetched |
| UK FCDO, travel advice for Gabon, updated 10 Dec 2025 | no part of Gabon advised against (still current on 21 Oct 2026) | https://www.gov.uk/foreign-travel-advice/gabon | Fetched |
| C. Farvacque-Vitkovic et al., *Street Addressing and the Management of Cities*, World Bank (2005), table 3.1 | US$5.7 per addressed doorway, US$0.6 per inhabitant; 52 cities in 15 countries | https://documents1.worldbank.org/curated/en/573071468142795481/pdf/329230Street0Addressing01not0external1.pdf | Fetched |
| UPU, *Addressing the World – An Address for Everyone* (2012) | the address as part of national infrastructure and identity | https://www.upu.int/UPU/media/upu/publications/whitePaperAddressingTheWorldEn.pdf | Fetched |
| S. Odeloye and D. Onajobi, NextBillion, 15 May 2023 | first-attempt delivery success as low as 60 % in Africa; US$2.70 per last-mile attempt | https://nextbillion.net/innovations-last-mile-delivery-automation-revolutionize-industry-africa | Fetched |
| M. P. Larsen et al., *Annals of Emergency Medicine* 22(11) (1993), 1652–1658, doi:10.1016/S0196-0644(05)81302-2 | survival 67 % less 2.3, 1.1 and 2.1 points per minute to CPR, defibrillation and advanced care | https://pubmed.ncbi.nlm.nih.gov/8214853 | Abstract checked |
| M. Hunt, RANGE: Undergraduate Research Journal, University of Utah (2023) | locating patients in Kigali depends on local knowledge and several calls | https://uen.pressbooks.pub/2023range/chapter/challenges-locating-the-scene-of-emergency-a-qualitative-study-of-the-ems-system-in-rwanda/ | Summary checked |
| S. J. Bokpe, Graphic Online, 19 Oct 2017 | a national digital address system in the region: 5 m squares, codes such as GA-543-0125 | https://www.graphic.com.gh/news/general-news/how-the-national-digital-property-address-system-works.html | Fetched |
| G. A. Miller (1956), doi:10.1037/h0043158; N. Cowan (2001), doi:10.1017/S0140525X01003922 | limits of short-term memory, behind the five-digit limit | | Crossref |
| H. M. Damm (2004), doi:10.17192/z2004.0516, and (2007), doi:10.1016/j.disc.2006.05.033; J. Verhoeff (1969) | the check digit and what it detects | | Crossref |
| D. Hilbert (1891), doi:10.1007/BF01199431; B. Moon et al. (2001), doi:10.1109/69.908985 | the curve and its locality | | Crossref |
| OpenStreetMap (ODbL), GeoNames (CC BY 4.0), Google Open Buildings (CC BY 4.0, Sirko et al. 2021), Microsoft footprints (ODbL), via Overture Maps | the data | | Data used |
