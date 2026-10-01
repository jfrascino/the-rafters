#!/usr/bin/env python3
"""Site player bios (height, weight, class, position, hometown) vs UConn's official season rosters (2003-04 on)."""
import json, re, os, glob, collections, unicodedata, difflib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFF = json.load(open(os.path.join(ROOT, 'pipeline/out/official/roster_bios.json')))
nn = lambda s: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', re.sub(r'\b(Jr|Sr|II|III)\b\.?', '', s or '')).encode('ascii', 'ignore').decode().lower())


def inches(h):
    m = re.match(r"\s*(\d)\s*['-]\s*(\d{1,2})", h or '')
    return int(m.group(1)) * 12 + int(m.group(2)) if m else None


def cls_(c):
    c = (c or '').lower().replace('redshirt', 'r-').replace(' ', '')
    base = re.sub(r'^r-?', '', c).rstrip('.')
    base = {'fr': 'FR', 'freshman': 'FR', 'so': 'SO', 'sophomore': 'SO', 'jr': 'JR', 'junior': 'JR', 'sr': 'SR', 'senior': 'SR', 'gr': 'GR', 'grad': 'GR', 'graduate': 'GR', 'gs': 'GR'}.get(base, base.upper())
    return base


def city(h):
    return nn((h or '').split(',')[0])


diffs = collections.defaultdict(list)
n = collections.Counter()
for f in sorted(glob.glob(os.path.join(ROOT, 'site/data/seasons/*.json'))):
    d = json.load(open(f)); y = str(d['y'])
    if y not in OFF:
        continue
    offs = [o for o in OFF[y] if o.get('cls') or o.get('ht')]
    for r in d.get('roster') or []:
        o = next((o for o in offs if nn(o['name']) == nn(r['name'])), None)
        if not o:
            cand = [o for o in offs if nn(o['name'])[-6:] == nn(r['name'])[-6:]]
            o = cand[0] if len(cand) == 1 else None
        if not o:
            n['no official card'] += 1; continue
        n['compared'] += 1
        if inches(o.get('ht')) and inches(r.get('ht')) and inches(o['ht']) != inches(r['ht']):
            diffs['height'].append((y, r['name'], r.get('ht'), o['ht']))
        wo = int(re.match(r'\d+', o['wt']).group()) if o.get('wt') and re.match(r'\d+', o['wt']) else None
        if wo and r.get('wt') and int(r['wt']) != wo:
            diffs['weight'].append((y, r['name'], r.get('wt'), wo))
        if o.get('cls') and r.get('cls') and cls_(o['cls']) != cls_(r['cls']):
            diffs['class'].append((y, r['name'], r.get('cls'), o['cls']))
        if o.get('home') and r.get('home') and city(o['home']) != city(r['home']):
            diffs['hometown'].append((y, r['name'], r.get('home'), o['home']))
print(dict(n))
for k, v in diffs.items():
    print(f'{k}: {len(v)} differ')
    for x in v[:12]: print('   ', x)
