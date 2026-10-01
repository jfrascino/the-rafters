#!/usr/bin/env python3
"""Compare every player-season jersey number on the site with the record book's ALL-TIME UNIFORM NUMBERS list
(pipeline/out/official/uniforms.json). Same strict name rule as the build: same first name or a short form of it."""
import json, re, unicodedata, glob, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U = {int(k): v for k, v in json.load(open(os.path.join(ROOT, 'pipeline/out/official/uniforms.json')))['by_year'].items()}


def toks(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?', '', s)
    return re.sub(r'[^a-z ]', '', s).split()


def lookup(y, name):
    p = toks(name)
    last, first = p[-1], (p[0] if len(p) > 1 else '')
    hits, same_last = [], []
    for e in U.get(y, []):
        q = toks(e['name'])
        if not q or q[-1] != last:
            continue
        same_last.append(e)
        f2 = q[0] if len(q) > 1 else ''
        short, long_ = sorted((first, f2), key=len)
        if first == f2 or (len(short) >= 2 and long_.startswith(short)):
            hits.append(e['num'])
    return hits, same_last


res, rows = collections.Counter(), []
for f in sorted(glob.glob(os.path.join(ROOT, 'site/data/seasons/*.json'))):
    d = json.load(open(f))
    for r in d.get('roster') or []:
        y, num = d['y'], str(r.get('num') or '')
        hits, same = lookup(y, r['name'])
        if not hits:
            res['not in list (non-letterwinner or no number)'] += 1
            rows.append(('missing', y, r['name'], num, [f"{e['name']} #{e['num']}" for e in same]))
        elif num in hits or num.lstrip('0') in {h.lstrip('0') for h in hits if h not in ('0', '00')}:
            res['match'] += 1
        else:
            res['differ'] += 1
            rows.append(('differ', y, r['name'], num, hits))
print(dict(res))
for r in rows:
    if r[0] == 'differ' or r[4]:
        print(' ', r)
