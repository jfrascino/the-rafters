#!/usr/bin/env python3
"""Record book single-season record lists (pp. 66-67) vs the site's season totals."""
import json, re, glob, os, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = [l.strip() for l in open(os.path.join(ROOT, 'pipeline/cache.nosync/official/rb_season_records.txt')).read().splitlines()]
T = [l for l in T if l and l not in ('Games', 'Points', 'Season', 'Season ', 'FG-FGA', 'Year')]

def nn(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(jr|sr|ii|iii)\b\.?', '', s)
    return re.sub(r'[^a-z]', '', s)

CAT = {'Highest Scoring Average': 'ppg', 'Most Points as a Fifth-Year Player': 'pts', 'Most points as a Senior': 'pts', 'Most Points as a Junior': 'pts',
       'Most Points as a Sophomore': 'pts', 'Most Points as a Freshman': 'pts', 'Most Field Goals Made': 'fg', 'Most Field Goal Attempts': 'fga',
       'Highest Field Goal % (min. 100 FGA)': 'fg_pct', 'Most Free Throws': 'ft', 'Highest Free Throw%': 'ft_pct', 'Most  Rebounds': 'trb',
       'Highest Rebound Average': 'rpg', 'Most Assists': 'ast', 'Most Assists Per Game': 'apg', 'Most Blocked Shots': 'blk', 'Most Blocked Shots Per Game': 'bpg',
       'Most Steals': 'stl', 'Most Steals Per Game': 'spg', '3-Point Field Goals Made': 'fg3', '3-Point Field Goals Made Per Game': 'fg3pg',
       '3-Point FG Attempts': 'fg3a', '3-Point Field Goal Percentage (Min. 75 3-Point FGA)': 'fg3_pct', 'Minutes Played': 'mp', 'Minutes Played- Average': 'mpg',
       'Most Double-Doubles': None, 'Most Consecutive Games With At Least One Successful 3-Pt FG': None, 'Most Double Figure Games as a Non-Starter': None}
season = {}
for f in glob.glob(os.path.join(ROOT, 'site/data/seasons/*.json')):
    d = json.load(open(f))
    for r in d.get('roster') or []:
        season[(nn(r['name']), d['y'])] = r
cat, entries, i = None, [], 0
while i < len(T):
    t = T[i]
    if t in CAT:
        cat = CAT[t]; i += 1; continue
    if re.match(r'^[\d.,]+%?$', t) and i + 1 < len(T):
        val, name = t, T[i + 1]
        j, mid = i + 2, []
        while j < len(T) and not re.search(r'\d{4}-\d{2}', T[j]) and j < i + 6 and T[j] not in CAT:
            mid.append(T[j]); j += 1
        if j < len(T) and re.search(r'\d{4}-\d{2}', T[j]):
            yy = re.search(r'(\d{4})-(\d{2})', T[j])
            entries.append({'cat': cat, 'val': val, 'name': name, 'mid': mid + [T[j]], 'y': int(yy.group(1)) + 1})
            i = j + 1
            continue
    i += 1
bad = checked = 0
for e in entries:
    if not e['cat'] or e['y'] < 1978:
        continue
    r = season.get((nn(e['name']), e['y']))
    if not r:
        cand = [v for (k, y), v in season.items() if y == e['y'] and k.endswith(nn(e['name'])[-6:])]
        r = cand[0] if len(cand) == 1 else None
    if not r:
        print('  no site season for', e['name'], e['y'], e['cat']); continue
    t, pg = r.get('tot') or {}, r.get('pg') or {}
    v = float(e['val'].rstrip('%').replace(',', ''))
    cat = e['cat']
    G = t.get('g') or pg.get('g')
    ours = {'ppg': (t.get('pts') or 0) / G if G else None, 'rpg': (t.get('trb') or 0) / G if G else None, 'apg': (t.get('ast') or 0) / G if G else None,
            'bpg': (t.get('blk') or 0) / G if G and t.get('blk') is not None else None, 'spg': (t.get('stl') or 0) / G if G and t.get('stl') is not None else None,
            'fg3pg': (t.get('fg3') or 0) / G if G and t.get('fg3') is not None else None, 'mpg': (t.get('mp') or 0) / G if G and t.get('mp') else None,
            'fg_pct': 100 * t['fg'] / t['fga'] if t.get('fga') else None, 'ft_pct': 100 * t['ft'] / t['fta'] if t.get('fta') else None,
            'fg3_pct': 100 * t['fg3'] / t['fg3a'] if t.get('fg3a') else None}.get(cat, t.get(cat))
    checked += 1
    tol = 0.051 if cat in ('ppg', 'rpg', 'apg', 'mpg', 'bpg', 'spg', 'fg_pct', 'ft_pct', 'fg3_pct') else 0.0051 if cat == 'fg3pg' else 0.5
    if ours is None or abs(ours - v) > tol:
        bad += 1
        print(f"  {e['name']:20s} {e['y']} {cat:7s} record book {e['val']:>6} {' '.join(e['mid'][:-1])[:30]:30s} | site {ours if ours is None else round(ours, 3)}")
print(f'single-season record entries checked: {checked}, disagreements: {bad}')
