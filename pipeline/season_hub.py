#!/usr/bin/env python3
"""Live data for the current-season hub -> pipeline/out/hub/
  standings.json   Big East standings (ESPN)
  polls.json       AP + Coaches Top 25 this week (ESPN), plus polls_history.json: UConn's rank week by week
  net.json         NCAA NET rankings, all teams (ncaa.com)
  bracket.json     consensus projected NCAA seed (bracketmatrix.com)
  next_opp.json    the next opponent: record, rank, stat leaders (ESPN)
Every source is optional: a failed fetch keeps the last good file. Each file records its own season so the site can
say "2025-26 final" in the off-season instead of passing old numbers off as current."""
import datetime as dt, html, json, os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'hub')
SITE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball'
UA_BROWSER = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36'
UCONN_ESPN = '41'
now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def get(url, browser=False):
    # ESPN's site API refuses browser user agents; ncaa.com and bracketmatrix want one
    req = urllib.request.Request(url, headers={'User-Agent': UA_BROWSER} if browser else {})
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')


def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    try:
        old = json.load(open(path))
        if {k: v for k, v in old.items() if k != 'fetched'} == {k: v for k, v in obj.items() if k != 'fetched'}:
            return   # unchanged: keep the file (and its fetch time) as is
    except Exception:
        pass
    json.dump({**obj, 'fetched': now}, open(path, 'w'), indent=1)


def team(t):
    return {'id': str(t.get('id')), 'name': t.get('location') or t.get('displayName'), 'full': t.get('displayName'), 'abbr': t.get('abbreviation'),
            'logo': (t.get('logos') or [{}])[0].get('href') or t.get('logo')}


def standings():
    d = json.loads(get(f'{SITE.replace("/site/v2", "/v2")}/standings?group=4'))
    st = d.get('standings') or {}
    rows = []
    for e in st.get('entries') or []:
        s = {x.get('type') or x.get('name'): x for x in e.get('stats') or []}
        rows.append({**team(e['team']), 'conf': (s.get('vsconf') or {}).get('summary'), 'overall': (s.get('total') or {}).get('summary'),
                     'seed': (s.get('playoffseed') or {}).get('displayValue'), 'gb': (s.get('vsconf_gamesbehind') or s.get('gamesbehind') or {}).get('displayValue'),
                     'streak': (s.get('streak') or {}).get('displayValue')})
    rows.sort(key=lambda r: int(r['seed']) if (r.get('seed') or '').isdigit() else 99)
    save('standings.json', {'season': st.get('season'), 'seasonLabel': st.get('seasonDisplayName'), 'phase': st.get('seasonType'), 'rows': rows})


def polls():
    d = json.loads(get(f'{SITE}/rankings'))
    out = {}
    for p in d.get('rankings') or []:
        key = {'AP Top 25': 'ap', 'Coaches Poll': 'coaches'}.get(p.get('name'))
        if not key:
            continue
        out[key] = {'date': (p.get('date') or '')[:10], 'headline': p.get('headline'), 'season': (p.get('season') or {}).get('year'),
                    'seasonLabel': (p.get('season') or {}).get('displayName'),
                    'ranks': [{'rank': r.get('current'), 'prev': r.get('previous'), 'pts': r.get('points'), 'fpv': r.get('firstPlaceVotes'),
                               'record': r.get('recordSummary'), **team(r.get('team') or {})} for r in p.get('ranks') or []],
                    'others': [{'pts': r.get('points'), 'record': r.get('recordSummary'), **team(r.get('team') or {})} for r in p.get('others') or []]}
    if not out:
        return
    save('polls.json', out)
    # UConn's week-by-week line for the season (append-only)
    hp = os.path.join(OUT, 'polls_history.json')
    hist = json.load(open(hp)) if os.path.exists(hp) else {}
    for key, p in out.items():
        u = next((r for r in p['ranks'] if r['id'] == UCONN_ESPN), None)
        votes = next((r['pts'] for r in p['others'] if r['id'] == UCONN_ESPN), None)
        row = {'date': p['date'], 'rank': u['rank'] if u else None, 'votes': votes, 'record': u['record'] if u else None}
        seas = hist.setdefault(str(p.get('season')), {}).setdefault(key, [])
        if not any(x['date'] == row['date'] for x in seas):
            seas.append(row)
    json.dump(hist, open(hp, 'w'), indent=1)


def net():
    s = get('https://www.ncaa.com/rankings/basketball-men/d1/ncaa-mens-basketball-net-rankings', browser=True)
    t = re.findall(r'<table.*?</table>', s, re.S)
    if not t:
        return
    heads = [re.sub(r'<[^>]+>', '', h).strip() for h in re.findall(r'<th[^>]*>(.*?)</th>', t[0], re.S)]
    rows = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t[0], re.S):
        c = [html.unescape(re.sub(r'<[^>]+>', '', x)).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
        if len(c) == len(heads):
            rows.append(dict(zip(heads, c)))
    m = re.search(r'(?i)through games?\s+(?:of\s+)?([A-Z][a-z]+\.?\s+\d{1,2},\s+\d{4})', s)
    if rows:
        save('net.json', {'through': m.group(1) if m else None, 'rows': rows})


def bracket():
    s = get('http://www.bracketmatrix.com/', browser=True)
    txt = [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '|', s)).split('|')]
    txt = [x for x in txt if x and x != '\xa0']
    i = next((k for k, x in enumerate(txt) if x in ('Connecticut', 'UConn')), None)
    if i is None:
        save('bracket.json', {'seed': None, 'note': 'not projected'})
        return
    # row reads: seed, ..., team, conference, average seed, number of brackets
    seed = next((txt[k] for k in range(i - 1, i - 4, -1) if re.fullmatch(r'\d{1,2}', txt[k])), None)
    avg = next((txt[k] for k in range(i + 1, i + 4) if re.fullmatch(r'\d{1,2}\.\d+', txt[k])), None)
    n = None
    if avg:
        j = txt.index(avg, i)
        n = next((txt[k] for k in range(j + 1, j + 3) if re.fullmatch(r'\d{1,3}', txt[k])), None)
    upd = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    date = f'{upd.group(3)}-{int(upd.group(2)):02d}-{int(upd.group(1)):02d}' if upd else None   # the page writes day/month/year
    save('bracket.json', {'seed': int(seed) if seed else None, 'avg': float(avg) if avg else None, 'brackets': int(n) if n else None, 'updated': date})


def next_opp():
    core = json.load(open(os.path.join(HERE, '..', 'site', 'data', 'core.json')))
    nxt = (core.get('current') or {}).get('next') or {}
    m = re.search(r'/(\d+)\.png', ((nxt.get('opp') or {}).get('logo') or ''))
    if not m:
        return
    tid = m.group(1)
    t = json.loads(get(f'{SITE}/teams/{tid}')).get('team') or {}
    rec = ((t.get('record') or {}).get('items') or [{}])[0]
    st = json.loads(get(f'{SITE}/teams/{tid}/statistics'))
    leaders = []
    for cat in ((st.get('results') or {}).get('leaders') or st.get('leaders') or []):
        for ld in (cat.get('leaders') or [])[:1]:
            leaders.append({'stat': cat.get('displayName') or cat.get('name'), 'name': (ld.get('athlete') or {}).get('displayName'), 'value': ld.get('displayValue')})
    save('next_opp.json', {'game': nxt.get('id'), 'team': team(t), 'record': rec.get('summary'), 'standing': t.get('standingSummary'), 'rank': t.get('rank'),
                           'leaders': leaders[:4]})


def main():
    for f in (standings, polls, net, bracket, next_opp):
        try:
            f()
            print(f'hub: {f.__name__} ok')
        except Exception as e:
            print(f'hub: {f.__name__} failed ({e}); keeping the last copy')


if __name__ == '__main__':
    main()
