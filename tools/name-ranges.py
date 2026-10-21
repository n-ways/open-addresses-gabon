#!/usr/bin/env python3
"""Plate names and national name ranges for Gabon.

  python3 tools/name-ranges.py        (light: reads model/stats/area-compounds.csv)

Two rules govern the names:
  * a remembered code must be unique in the whole country on its own, without the town said after
    it or the phone's position;
  * the name in the code (the PLATE name) is short: at most 12 characters and 2 words, no digit
    (engine/reference/plate_names.py). The official name is kept for small print and still decodes.

Writes
  model/areas/name-ranges.json   one entry per normalised plate name: frozen id, digits, blocks, aliases
  model/areas/register.json      adds plateName / plateRule (and the council fields) to every area
  model/stats/name-stats.json    the counts quoted in docs/model.md and the papers

Plate names (SPEC 2.5):
  * derived from the official name by plate_names.derive, in French (every zone of Gabon;
    model/zones.json "language");
  * weak words (Nouveau, Village, Chefferie, Mission, Centre...) are never a plate name
    alone, and a short form that drops one goes to the commune (needsCouncilChoice);
  * a short form must not be a big city's name elsewhere;
  * where the short form would hold a digit, be a bare generic word ("Quartier", "Carrefour"), a
    derived form of under 3 letters or a big city's name, the area carries its département's chief
    town until the commune chooses;
  * a short form equal to the name of another place of the same zone goes to the commune;
  * a flagged area keeps a provisional plate name (first candidate) and is issued: no compound waits
    for a naming decision.

Name ranges (SPEC 2.4):
  * every area whose PLATE name has the same key (ga_engine.name_key) draws its numbers from ONE
    national range for that name, cut into blocks, one per area, in register order (zone, index);
  * block size = compounds x 2 rounded up to a multiple of 10, at least 20;
  * digits of the name (3, 4 or 5, same for all its areas) = the smallest d whose range holds all
    blocks with the top tenth left spare; no number has more than 5 digits;
  * a name whose areas together do not fit 5 digits keeps the bare name for the blocks that fit in
    register order and gives the others the zone as qualifier, decided once and listed;
  * an official name whose key differs from its plate key is an alias of that plate name when it maps
    to one plate name only.
"""
import collections, unicodedata, csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'engine', 'reference'))
import ga_engine as e  # noqa: E402
import plate_names as P  # noqa: E402

SPARE = e.NAME_SPARE
areas = list(csv.DictReader(open(os.path.join(REPO, 'model', 'stats', 'area-compounds.csv'), encoding='utf-8')))
zmeta = {z['key']: z for z in json.load(open(os.path.join(REPO, 'model', 'zones.json'), encoding='utf-8'))['zones']}
generic = [a for a in areas if e.is_generic(a['officialName'])]
named = [a for a in areas if not e.is_generic(a['officialName'])]
for a in named:
    a['compounds'] = int(a['compounds'])
    a['lang'] = zmeta[a['zone']]['language']

GENERIC_EXTRA = {'fr': ['q', 'lieu-dit', 'quartier', 'carrefour'], 'en': ['quarter', 'qtr', 'junction']}
WEAK_EXTRA = ['nouveau', 'nouvelle', 'nouvel', 'mini', 'village', 'site', 'camp', 'new', 'old', 'chefferie', 'centre', 'center', 'gare',
              'marché', 'market', 'mission', 'plantation', 'quarter', 'layout']
# Ordinary French and English words in Gabon's place names: the landmark or description beside the
# place's own name ("Carrefour Laboratoire X", "Mission Catholique X", "Vallée de la Mort").
# They score as weak words, so a short form keeps the proper name (X), and a plate made only of them
# ("Mort", "Président", "Catholique") is never taken: the zone's name until the commune chooses.
# Parts of names in Gabon's own languages (Nkol, Nzeng, Akok, Mbeng) are names, not in this list.
COMMON = {'chefferie', 'cheferie', 'centre', 'place', 'point', 'rond', 'rondpoint', 'rond-point', 'pont', 'rue', 'puit', 'puits',
          'cite', 'mission', 'lycee', 'college', 'administratif', 'palais', 'entree', 'station', 'vallee', 'marche', 'lotissement',
          'chantier', 'chantiers', 'catholique', 'protestant', 'protestante', 'chapelle', 'barriere', 'sante', 'eglise', 'sous',
          'bois', 'port', 'sans', 'club', 'paix', 'gare', 'palace', 'montee', 'foire', 'laboratoire', 'mort', 'morts', 'president',
          'publique', 'public', 'ecole', 'cimetiere', 'poteau', 'depot', 'dernier', 'derniere', 'antenne', 'pedagogique',
          'scientifique', 'paroisse', 'terrain', 'prix', 'foyer', 'degre', 'troisieme', 'deuxieme', 'premier', 'premiere', 'sapeur',
          'chateau', 'hotel', 'aeroport', 'air', 'armee', 'defile', 'feu', 'singes', 'etrangers', 'laverie', 'science', 'express',
          'cadeau', 'terminus', 'beach', 'histoire', 'nobles', 'avicole', 'complexe', 'universite', 'forage', 'moulin', 'prison',
          'minier', 'famille', 'gentil', 'commercial', 'commerciale', 'ville', 'base', 'vie', 'cadres', 'lac', 'bar', 'service',
          'mobile', 'block', 'garden', 'gardens', 'tunnel', 'residence', 'cheminots', 'manguiers', 'fontaine', 'bonne', 'allees',
          'promise', 'terre', 'combattant', 'derriere', 'devant', 'poudriere', 'stade', 'hopital', 'mosquee', 'temple', 'boulangerie',
          'pharmacie', 'carriere', 'usine', 'scierie', 'plage', 'foret', 'source', 'colline', 'mont', 'route', 'avenue', 'boulevard',
          'entre', 'face', 'cote', 'bas', 'haut', 'nord', 'sud', 'est', 'ouest', 'junction', 'corner', 'corners', 'boundary',
          'quarters', 'three', 'limit', 'number', 'lower', 'middle', 'upper', 'native', 'senior', 'farm', 'workers', 'housing',
          'bridge', 'estate', 'street', 'coconut', 'dam', 'enclave', 'small', 'big', 'town', 'creek', 'hill', 'church', 'school',
          'hospital', 'carefour', 'government', 'roundabout', 'motor', 'park', 'police', 'gendarmerie', 'brigade', 'prefecture', 'sous-prefecture', 'mairie',
          'institut', 'sport', 'sports'}
WEAK_EXTRA = WEAK_EXTRA + sorted(COMMON)


BIG_CITIES = ['Libreville', 'Port-Gentil', 'Franceville', 'Oyem', 'Moanda', 'Mouila', 'Lambaréné', 'Tchibanga', 'Koulamoutou',
              'Makokou', 'Bitam', 'Gamba', 'Ntoum', 'Owendo', 'Akanda', 'Lastoursville', 'Mitzic', 'Ndjolé',
              # the region's large cities beyond the borders, whose names travellers and traders know
              'Yaoundé', 'Douala', 'Malabo', 'Bata', 'Brazzaville', 'Pointe-Noire', 'Kinshasa']
CITY_KEYS = {e.name_key(x) for x in BIG_CITIES}
BARE_WORDS = {'secteur', 'zone', 'cite', 'quartier', 'quarter', 'village', 'hameau', 'lotissement', 'logements', 'camp', 'site',
              'centre', 'center', 'carrefour', 'extension', 'layout', 'mission', 'marche', 'market', 'chefferie', 'plantation'}
# Documented spellings and short forms people already use, with a source.
KNOWN = {'Mont Bouet': ('Mont-Bouët', 'the market and quarter as the press and the city write it, e.g. Gabonreview and '
                                      'Gabonmediatime on the Marché de Mont-Bouët')}
freq = {lang: P.word_freq([a['officialName'] for a in named if a['lang'] == lang], lang) for lang in ('fr', 'en')}


def _words(p):
    return [w for w in re.split(r"[\s\-’']+", P.plain(p)) if w]


LINK = P.LINKING['fr'] | P.LINKING['en']
ORDINARY = (COMMON | {P.plain(x) for x in WEAK_EXTRA} | {P.plain(x) for x in GENERIC_EXTRA['fr'] + GENERIC_EXTRA['en']}
            | {P.plain(x) for x in P.GENERIC['fr'] + P.GENERIC['en'] if ' ' not in x} | BARE_WORDS
            | {P.plain(x) for x in P.WEAK['fr'] | P.WEAK['en']})


def only_common(p):
    """A plate made only of ordinary words (and linking words): never a code name on its own."""
    ws = [w for w in _words(p) if w not in LINK]
    return bool(ws) and all(w in ORDINARY for w in ws)


def cut_phrase(p, official):
    """A plate that starts on a linking word ("de la Caisse"), or stops on an ordinary word the official
    name goes on after ("Derrière" of "Derrière l'Hôpital")."""
    ws, ow = _words(p), _words(official)
    if not ws:
        return False
    if ws[0] in LINK:
        return True
    if ws[-1] in ORDINARY:
        for i in range(len(ow) - len(ws) + 1):
            if ow[i:i + len(ws)] == ws:
                rest = [w for w in ow[i + len(ws):] if w not in LINK and not P.ROMAN.match(w)]
                return bool(rest)  # a number or numeral after it ("Afeme Nord 1") is no continuation
    return False


def zone_word(zk):
    """The fallback plate of a zone: its département's chief town, the name people say (Woleu -> Oyem,
    Bendje -> Port-Gentil), never the département's own name."""
    z = zmeta[zk]
    return (z.get('chefLieu') or z['name']).strip()


# Companies' and bodies' names written in capitals, kept so on a plate; any other word in capitals
# in the sources (MIMBOTI, EFFACK) is a village's name, written as a name (Mimboti, Effack).
ACRONYMS = {'SETRAG', 'SOMIMA', 'STFO', 'SNBG', 'CNSS', 'SEEG', 'COMILOG', 'CEMAC', 'ENEF', 'IAI', 'USTM', 'UOB'}


def written(name):
    return re.sub(r"\b[A-ZÀ-Ý]{4,}\b", lambda m: m.group(0) if m.group(0) in ACRONYMS else m.group(0).capitalize(), name)


def latin(name):
    """The words of a name in the Latin alphabet, when it has any: a name given in two scripts
    is written on a plate in the one the codes use."""
    other = lambda w: any(ch.isalpha() and not unicodedata.name(ch, '').startswith('LATIN') for ch in w)
    keep = [w for w in name.split() if not other(w)]
    return ' '.join(keep) if any(ch.isalpha() for ch in ''.join(keep)) else name


def plate_for(a):
    lang = a['lang']
    r = P.derive(latin(a['officialName']), lang, freq[lang], known=KNOWN, avoid=BIG_CITIES, generic_extra=GENERIC_EXTRA[lang],
                 weak_extra=WEAK_EXTRA, avoid_key=e.name_key)
    if r['rule'] in ('distinctive', 'cleaned') and re.search(r'\d', a['officialName']) and not re.search(r'\d', r['plate']):
        r.update(rule='council', needsCouncilChoice=True, reason='the short form drops a number of the official name')
    if r['needsCouncilChoice']:
        r['rule'] = 'council'
    tidy = lambda x: written(re.sub(r"^[^\w]+|[^\w]+$", '', x).strip())
    r['plate'] = tidy(r['plate']) or r['plate']
    r['candidates'] = [c for c in dict.fromkeys(tidy(c) for c in r['candidates']) if c]
    # a plate the code can carry: no digit, no bare generic word, at least 3 letters, no big city elsewhere
    p = r['plate']
    letters = sum(ch.isalpha() for ch in p)
    own = zone_word(a['zone'])
    bad = (re.search(r'\d', p) or P.plain(p) in BARE_WORDS
           or (r['rule'] not in ('as-is', 'known') and (only_common(p) or cut_phrase(p, a['officialName'])
                                                        or (not P.fits(p, lang) and any(w in ORDINARY for w in _words(p)))))
           or (r['rule'] not in ('as-is', 'known', 'cleaned') and letters < 3)
           or (r['rule'] not in ('as-is', 'known') and e.name_key(p) in CITY_KEYS and e.name_key(p) != e.name_key(own)))
    if bad:
        ok = [c for c in r['candidates'] if not re.search(r'\d', c) and sum(ch.isalpha() for ch in c) >= 3
              and P.plain(c) not in BARE_WORDS and not only_common(c) and not cut_phrase(c, a['officialName'])
              and P.fits(c, lang) and (e.name_key(c) not in CITY_KEYS or e.name_key(c) == e.name_key(own))]
        r.update(plate=own, rule='council', needsCouncilChoice=True, zoneFallback=True, candidates=list(dict.fromkeys([own] + ok))[:3],
                 reason="the short form has a number, only ordinary words, a cut phrase or another town's name, or nothing fits: the zone's name until the commune chooses")
    r['fits'] = P.fits(r['plate'], lang)
    return r


for a in named:
    a['plate'] = plate_for(a)
    a['okey'] = e.name_key(a['officialName'])
    # Variants are the same words written differently: accents, case and punctuation only, word
    # breaks kept ("Port-Gentil" = "Port Gentil"). Never the name key's folds: those make "Njinga I"
    # = "Njinga II" (a doubled letter written once) and "Mbengui" = "Mbeng I" (gu before i), and
    # without word breaks "Obangi" = "Obang I": different places with different plates.
    a['vkey'] = re.sub(r'[^A-Z0-9]+', ' ', e._fold(a['officialName'])).strip()
# one official name, one plate: spelling variants of a name ("Akébé-Ville" and "Akebe Ville") take
# the same plate: the one that fits, then the one written with its accents, then the one more
# people live under (compounds), then the most common
byo = collections.defaultdict(list)
for a in named:
    byo[(a['lang'], a['vkey'])].append(a)
for ms in byo.values():
    plates = collections.Counter(a['plate']['plate'] for a in ms)
    if len(plates) > 1:
        lives = collections.Counter()
        for a in ms:
            lives[a['plate']['plate']] += a['compounds']
        accents = lambda p: sum(not ch.isascii() for ch in p)
        best = sorted(plates, key=lambda p: (not P.fits(p, ms[0]['lang']), -accents(p), -lives[p], -plates[p], p))[0]
        src_a = next(a for a in ms if a['plate']['plate'] == best)
        src = src_a['plate']
        for a in ms:
            a['plate'] = dict(src)
            if src.get('zoneFallback') and a['zone'] != src_a['zone']:
                # a zone-name fallback stays each area's own zone (one of Woleu takes Oyem, one of Bendje Port-Gentil)
                a['plate'].update(plate=zone_word(a['zone']), candidates=[zone_word(a['zone'])] + [c for c in src['candidates'] if c != src['plate']])
for a in named:
    a['key'] = e.name_key(a['plate']['plate'])
# a short form equal to the name of another place of the same zone goes to the commune
incommune = collections.defaultdict(set)
for a in named:
    incommune[(a['zone'], a['key'])].add(a['okey'])
for a in named:
    r = a['plate']
    if r['rule'] in ('cleaned', 'distinctive') and len(incommune[(a['zone'], a['key'])]) > 1:
        r.update(rule='council', needsCouncilChoice=True, candidates=r['candidates'] or [r['plate']],
                 reason='another place of the same zone has this name')


def cap(d):
    return int(9 * 10 ** (d - 1) * (1 - SPARE))


def ranges():
    byname = collections.defaultdict(list)
    for a in sorted(named, key=lambda a: (a['zone'], a['index'])):
        byname[a['key']].append(a)
    split, qualified, entries = [], [], {}

    def place(members):
        blocks, total = [], 0
        for a in members:
            if a['compounds'] == 0:
                continue  # no compound yet: its block comes from the spare at its first compound
            b = e.block_size(a['compounds'])
            blocks.append((a, b))
            total += b
        return blocks, total, next((d for d in (3, 4, 5) if total <= cap(d)), None)

    for key in sorted(byname):
        keep = []
        for a in byname[key]:
            if e.block_size(a['compounds']) > cap(5):
                split.append({'officialName': a['officialName'], 'plateName': a['plate']['plate'], 'zone': a['zone'],
                              'index': a['index'], 'compounds': a['compounds']})
            else:
                keep.append(a)
        if not keep:
            continue
        blocks, total, d = place(keep)
        groups = [(key, keep, None)]
        if d is None:  # combined areas do not fit 5 digits: the zone as qualifier for the overflow, decided once
            bare, rest, used = [], [], 0
            for a in keep:
                b = e.block_size(a['compounds']) if a['compounds'] else 0
                if used + b <= cap(5):
                    bare.append(a)
                    used += b
                else:
                    rest.append(a)
            groups = [(key, bare, None)]
            for a in rest:
                q = f"{a['plate']['plate']}-{zone_word(a['zone'])}"
                qualified.append({'plateName': a['plate']['plate'], 'qualified': q, 'zone': a['zone'], 'index': a['index'],
                                  'compounds': a['compounds']})
                groups.append((e.name_key(q), [a], q))
        for k, ms, qname in groups:
            blocks, total, d = place(ms)
            if d is None:
                raise SystemExit(f'{k}: does not fit 5 digits even alone')
            lo = 10 ** (d - 1)
            cur, bl = lo, []
            for a, b in blocks:
                bl.append([a['zone'], a['index'], a['compounds'], cur, cur + b - 1])
                cur += b
            spell = collections.Counter(qname or a['plate']['plate'] for a in ms)
            entries[k] = {'plateName': spell.most_common(1)[0][0], 'members': ms, 'digits': d, 'range': [lo, 10 ** d - 1],
                          'spareFrom': cur, 'areasWithoutCompounds': [[a['zone'], a['index']] for a in ms if a['compounds'] == 0],
                          'blocks': bl}
            if qname:
                for a in ms:
                    a['plate']['plate'] = qname
    return entries, split, qualified


entries, split, qualified = ranges()
if split:
    print('areas too large for 5 digits on their own (split them by named quarters first):', json.dumps(split, ensure_ascii=False))
for i, k in enumerate(sorted(entries)):
    entries[k] = dict(id=i + 1, **entries[k])

claims = collections.defaultdict(set)
for k, v in entries.items():
    for a in v['members']:
        if a['okey'] != k and a['okey']:
            claims[a['okey']].add(k)
aliases, dropped = {}, []
for ak, ks in sorted(claims.items()):
    offs = sorted({a['officialName'] for k in ks for a in entries[k]['members'] if a['okey'] == ak})
    if ak in entries:
        dropped.append({'official': offs, 'key': ak, 'claimedBy': sorted(entries[k]['plateName'] for k in ks),
                        'why': 'is itself the plate name of other areas'})
    elif len(ks) > 1:
        dropped.append({'official': offs, 'key': ak, 'claimedBy': sorted(entries[k]['plateName'] for k in ks),
                        'why': 'claimed by two plate names'})
    else:
        aliases[ak] = next(iter(ks))

# ---------------------------------------------------------------------------
# Stats
rules = collections.Counter(a['plate']['rule'] for a in named)
flag = [a for a in named if a['plate']['needsCouncilChoice']]
rep = {k: v for k, v in entries.items() if len(v['blocks']) + len(v['areasWithoutCompounds']) > 1}
da, dc = collections.Counter(), collections.Counter()
for v in entries.values():
    for b in v['blocks']:
        da[v['digits']] += 1
        dc[v['digits']] += b[2]
tc = sum(dc.values()) or 1
stats = {
    'source': "model/stats/area-compounds.csv (the register's areas with the compounds grouped at first issue)",
    'normalisation': 'ga_engine.name_key of the plate name',
    'plateRule': {'maxChars': P.MAX_CHARS, 'maxWords': P.MAX_WORDS, 'langs': ['fr', 'en'], 'tool': 'engine/reference/plate_names.py'},
    'spare': SPARE, 'areas': len(areas), 'genericLabels': len(generic), 'namedAreas': len(named),
    'plates': {
        'officialOverLimit': sum(1 for a in named if not P.fits(a['officialName'], a['lang'])),
        'byRule': dict(sorted(rules.items())), 'needsCouncilChoice': len(flag),
        'needsCouncilChoiceByReason': dict(collections.Counter(a['plate'].get('reason') for a in flag).most_common()),
        'stillOverLimit': sum(1 for a in flag if not P.fits(a['plate']['plate'], a['lang'])),
        'aliases': len(aliases), 'droppedAliases': len(dropped),
        'provisionalCompounds': sum(a['compounds'] for a in flag)},
    'names': len(entries), 'repeatedNames': len(rep),
    'areasUnderRepeatedNames': sum(len(v['blocks']) + len(v['areasWithoutCompounds']) for v in rep.values()),
    'mostAreas': sorted(([v['plateName'], len(v['blocks']) + len(v['areasWithoutCompounds'])] for v in rep.values()),
                        key=lambda x: (-x[1], x[0]))[:10],
    'areasByDigits': dict(sorted(da.items())), 'compoundsByDigits': dict(sorted(dc.items())),
    'compoundShareByDigits': {k: round(v / tc, 3) for k, v in sorted(dc.items())},
    'splitBeforeIssue': split, 'qualified': qualified,
}

# ---------------------------------------------------------------------------
# Write
out = os.path.join(REPO, 'model', 'areas')
names_out = {}
for k, v in sorted(entries.items()):
    offs = sorted({a['officialName'] for a in v['members']})
    names_out[k] = {'id': v['id'], 'plateName': v['plateName'], 'officialNames': offs,
                    'aliases': sorted(o for o in offs if aliases.get(e.name_key(o)) == k),
                    'digits': v['digits'], 'range': v['range'], 'spareFrom': v['spareFrom'],
                    'areasWithoutCompounds': v['areasWithoutCompounds'], 'blocks': v['blocks']}
    if any(a['plate']['needsCouncilChoice'] for a in v['members']):
        names_out[k]['needsCouncilChoice'] = True
json.dump({'rule': 'one national number range per normalised PLATE name, frozen blocks per area (SPEC 2.4, 2.5)',
           'plateRule': 'at most 12 characters and 2 words, no digit (engine/reference/plate_names.py)',
           'spare': SPARE, 'version': '1.0 (frozen at first issue; OpenStreetMap and GeoNames names)',
           'aliasKeys': dict(sorted(aliases.items())), 'droppedAliases': dropped,
           'names': names_out}, open(os.path.join(out, 'name-ranges.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
reg_path = os.path.join(out, 'register.json')
reg = json.load(open(reg_path, encoding='utf-8'))
byarea = {(a['zone'], a['index']): a for a in named}
for zk, c in reg.items():
    for v in c['villages']:
        a = byarea.get((zk, v['index']))
        for f in ('plateName', 'plateRule', 'needsCouncilChoice', 'plateCandidates', 'plateReason'):
            v.pop(f, None)
        if a is None:
            v['plateRule'] = 'generic label: no plate name'
            continue
        r = a['plate']
        v['plateName'] = r['plate']
        v['plateRule'] = r['rule']
        if r['needsCouncilChoice']:
            v.update(needsCouncilChoice=True, plateCandidates=r['candidates'][:3], plateReason=r.get('reason'))
json.dump(reg, open(reg_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(stats, open(os.path.join(REPO, 'model', 'stats', 'name-stats.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in stats.items() if k not in ('splitBeforeIssue', 'qualified')}, ensure_ascii=False, indent=1))
