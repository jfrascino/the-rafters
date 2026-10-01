#!/usr/bin/env python3
"""Record book "30-POINT GAMES" list vs. the box scores on the site (both directions)."""
import json, re, glob, os, unicodedata, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = [l.strip() for l in open(os.path.join(ROOT, 'pipeline/cache.nosync/official/rb_game_records.txt')).read().splitlines()]
nn = lambda s: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', re.sub(r'\b(Jr|Sr|II|III)\b\.?', '', s or '')).encode('ascii', 'ignore').decode().lower())
SECTIONS = [('30-POINT GAMES', '20-REBOUND GAMES', 'pts', 30), ('20-REBOUND GAMES', '10-ASSIST GAMES', 'reb', 20), ('10-ASSIST GAMES', 'MOST POINTS', 'ast', 10)]
rb = []
for head, nxt, stat, floor in SECTIONS:
    i0 = T.index(head)
    i1 = next(k for k in range(i0 + 1, len(T)) if T[k] == nxt)
    name, i = None, i0 + 1
    while i < i1:
        t = T[i]
        if re.fullmatch(r'\d{4}-\d{2}', t) or t in ('Name', 'Date', 'Opponent', 'Points', 'Rebounds', 'Assists', '') or 'UCONN MEN' in t or 'NATIONAL CHAMPIONS' in t or 'SINGLE GAME RECORDS' in t or re.fullmatch(r'\d{2}', t):
            i += 1; continue
        if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{2}', t) and i + 2 < i1 and re.fullmatch(r'\d{2}', T[i + 2].strip()):
            m, d, y = map(int, t.split('/')); y += 1900 if y > 40 else 2000
            rb.append({'name': name, 'date': f'{y:04d}-{m:02d}-{d:02d}', 'opp': T[i + 1], 'stat': stat, 'v': int(T[i + 2]), 'floor': floor}); i += 3; continue
        if re.match(r"^[A-Z][A-Za-z.'’\- ]+$", t) and not t.isupper():
            name = t
        i += 1
print('record book entries:', {st: sum(1 for e in rb if e['stat'] == st) for st in ('pts', 'reb', 'ast')})
logs = {}
for f in glob.glob(os.path.join(ROOT, 'site/data/players/*.json')):
    d = json.load(open(f))
    for g in d.get('gamelog') or []:
        logs[(nn(d['name']), g['date'][:10])] = (d['name'], g)
covered = {g['date'][:10] for (_, _), (_, g) in logs.items()}
miss = mism = ok = 0
for e in rb:
    key = (nn(e['name']), e['date'])
    hit = logs.get(key)
    if not hit:   # try +-1 day (West Coast dates) and nickname variants
        for dd in (-1, 1):
            d2 = (datetime.date.fromisoformat(e['date']) + datetime.timedelta(days=dd)).isoformat()
            hit = hit or logs.get((nn(e['name']), d2))
    if not hit:
        hit = next((v for (k, dte), v in logs.items() if dte == e['date'] and k.endswith(nn(e['name']).split()[-1] if ' ' in e['name'] else nn(e['name'])[-5:])), None)
    if not hit:
        if e['date'] in covered:
            miss += 1; print('  in record book, not in our box score:', e)
        continue
    if hit[1].get(e['stat']) != e['v']:
        mism += 1; print(f"  {e['stat']} differ: {e['name']} {e['date']} {e['opp']}: record book {e['v']}, box {hit[1].get(e['stat'])}")
    else:
        ok += 1
extra = 0
for stat, floor in (('pts', 30), ('reb', 20), ('ast', 10)):
    rbkeys = {(nn(e['name']), e['date']) for e in rb if e['stat'] == stat}
    for (k, dte), (nm, g) in logs.items():
        if (g.get(stat) or 0) >= floor and (k, dte) not in rbkeys:
            alt = any((k, (datetime.date.fromisoformat(dte) + datetime.timedelta(days=dd)).isoformat()) in rbkeys for dd in (-1, 1))
            if not alt:
                extra += 1; print(f"  {stat} {g[stat]} in our box, not in record book list: {nm} {dte} vs {g['opp']['name']}")
print(f'matched {ok}, points differ {mism}, missing from our boxes {miss}, extra in ours {extra}')
