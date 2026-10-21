#!/usr/bin/env python3
"""Rename code areas after first issue: model/areas/renames.json applied to the frozen register.

  python3 tools/rename-areas.py

Each rename gives some areas a new plate name. The areas leave their old name's range. A new name
key gets the next name id (ids are append-only) and its blocks laid out from the start of its
range, with the rules of first issue (ga_engine.block_size, NAME_SPARE). Areas joining a name that
already exists take the next blocks above every block of that name, in its spare space (the
growth rule, SPEC 2.4): that name's own areas never move. Within each area the order of the compounds never changes, so a
number moves by the shift of its block: new = new_lo + (old - old_lo). The old official name stays
an alias. Writes model/areas/name-ranges.json and engine/data/register.json, and prints the number
shifts for the issuer (one line per area: key, old_lo, new_lo, name id).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'engine', 'reference'))
import ga_engine as E  # noqa: E402

NR = os.path.join(REPO, 'model', 'areas', 'name-ranges.json')
RG = os.path.join(REPO, 'engine', 'data', 'register.json')
nr = json.load(open(NR, encoding='utf-8'))
reg = json.load(open(RG, encoding='utf-8'))
RN = os.path.join(REPO, 'model', 'areas', 'renames.json')
if not os.path.exists(RN):
    print('no rename to apply: model/areas/renames.json does not exist yet ({"renames": [{"plate": ..., "areas": [...]}]})')
    sys.exit(0)
renames = json.load(open(RN, encoding='utf-8'))['renames']
areas = {a['key']: a for a in reg['areas']}
names = nr['names']
by_key = {n['key']: n for n in reg['names']}


def cap(d):
    return int(9 * 10 ** (d - 1) * (1 - E.NAME_SPARE))


shifts = []
for rn in renames:
    plate, key = rn['plate'], E.name_key(rn['plate'])
    moved = [areas[k] for k in rn['areas']]
    if any(a['name'] == plate for a in moved):
        continue  # already applied
    # 1. the areas leave their old names
    for a in moved:
        old = names[a['nameKey']]
        old['blocks'] = [b for b in old['blocks'] if f"{b[0]}-{b[1]}" != a['key']]
        old['officialNames'] = sorted({areas[f"{b[0]}-{b[1]}"]['officialName'] for b in old['blocks']})
        old['aliases'] = [x for x in old['aliases'] if x in old['officialNames'] and E.name_key(x) != a['nameKey']]
        if not any(areas[f"{b[0]}-{b[1]}"].get('provisional') for b in old['blocks']):
            old.pop('needsCouncilChoice', None)
    # 2. the new name's range, laid out again over all its areas
    entry = names.get(key)
    if entry is None:
        nid = max(v['id'] for v in names.values()) + 1
        entry = names[key] = {'id': nid, 'plateName': plate, 'officialNames': [], 'aliases': [], 'digits': 0,
                              'range': [0, 0], 'spareFrom': 0, 'areasWithoutCompounds': [], 'blocks': []}
        reg['names'].append({'key': key, 'id': nid, 'plateName': plate, 'digits': 0, 'range': [0, 0], 'spareFrom': 0})
        by_key[key] = reg['names'][-1]
    existing = [areas[f"{b[0]}-{b[1]}"] for b in entry['blocks']]
    if existing:
        # Growth rule (SPEC 2.4): areas joining a name take the next blocks above every block of
        # that name, in its spare space; the name's own areas never move.
        d, cur, blocks = entry['digits'], entry['spareFrom'], [list(b) for b in entry['blocks']]
        for a in sorted(moved, key=lambda a: (a['zone'], a['index'])):
            if not a['compounds']:
                continue
            b = E.block_size(a['compounds'])
            if cur + b - 1 > 10 ** d - 1:
                sys.exit(f"{plate}: no room for {a['key']} above the name's blocks ({cur}-{cur + b - 1})")
            shifts.append((a['key'], a['blocks'][0][0], cur, entry['id']))
            blocks.append([a['zone'], a['index'], a['compounds'], cur, cur + b - 1])
            a['blocks'] = [[cur, cur + b - 1]]
            a['digits'], a['nameId'], a['nameKey'] = d, entry['id'], key
            a['name'], a['provisional'] = plate, bool(rn.get('provisional'))
            a.pop('plateCandidates', None)
            cur += b
        members = existing + moved
    else:
        members = sorted(moved, key=lambda a: (a['zone'], a['index']))
        total = sum(E.block_size(a['compounds']) for a in members if a['compounds'])
        d = next(d for d in (3, 4, 5) if total <= cap(d))
        cur, blocks = 10 ** (d - 1), []
        for a in members:
            if not a['compounds']:
                continue
            b = E.block_size(a['compounds'])
            shifts.append((a['key'], a['blocks'][0][0], cur, entry['id']))
            blocks.append([a['zone'], a['index'], a['compounds'], cur, cur + b - 1])
            a['blocks'] = [[cur, cur + b - 1]]
            a['digits'], a['nameId'], a['nameKey'] = d, entry['id'], key
            a['name'], a['provisional'] = plate, bool(rn.get('provisional'))
            a.pop('plateCandidates', None)
            cur += b
    entry.update(digits=d, range=[10 ** (d - 1), 10 ** d - 1], spareFrom=cur, blocks=blocks,
                 officialNames=sorted({a['officialName'] for a in members}))
    entry['aliases'] = sorted({a['officialName'] for a in members if E.name_key(a['officialName']) != key})
    entry['plateName'] = max(sorted({a['name'] for a in members}), key=lambda s: sum(a['name'] == s for a in members))
    by_key[key].update(plateName=entry['plateName'], digits=d, range=entry['range'], spareFrom=cur)
    for a in moved:
        ok = E.name_key(a['officialName'])
        if ok != key:
            nr['aliasKeys'][ok] = key
            reg['aliases'][ok] = key

json.dump(nr, open(NR, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(reg, open(RG, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
for s in shifts:
    print('%s %d %d %d' % s)
