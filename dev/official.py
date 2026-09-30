#!/usr/bin/env python3
"""Third-source check: UConn Athletics' own schedule archive (uconnhuskies.com) vs the app's games.

python3 dev/official.py   → caches pages in pipeline/cache.nosync/official/, writes pipeline/out/official/schedules.json
                             and dev/official_report.json (every disagreement on date, score, site, opponent)
"""
import json, os, re, time, html, urllib.request, datetime, unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CACHE = os.path.join(ROOT, 'pipeline', 'cache.nosync', 'official')
OUTD = os.path.join(ROOT, 'pipeline', 'out', 'official')
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUTD, exist_ok=True)
MON = {m: i + 1 for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r"\(.*?\)|[.'`’\-&]", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def fetch(label):
    p = os.path.join(CACHE, f'{label}.html')
    if os.path.exists(p) and os.path.getsize(p) > 50000:
        return open(p, encoding='utf-8', errors='replace').read()
    req = urllib.request.Request(f'https://uconnhuskies.com/sports/mens-basketball/schedule/{label}', headers={'User-Agent': 'Mozilla/5.0 (the-rafters fan project)'})
    h = urllib.request.urlopen(req, timeout=40).read().decode('utf-8', 'replace')
    open(p, 'w').write(h)
    time.sleep(1.5)
    return h


def parse(h, y):
    games = []
    for blk in h.split('data-test-id="s-game-card-standard__root"')[1:]:
        t = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', blk)))
        d = re.search(r'\b(Oct|Nov|Dec|Jan|Feb|Mar|Apr) (\d{1,2}) \((\w{3})\)', t)
        if not d:
            continue
        mo = MON[d.group(1)]
        date = datetime.date(y - 1 if mo >= 7 else y, mo, int(d.group(2))).isoformat()
        r = re.search(r'\b([WLT]), (\d+)-(\d+)(?: \((\d?)OT\))?', t)
        vsat = re.search(r'\b(vs|at)\.? (?:#\d+ )?(.+?)(?= [A-Z][a-z]+(?:\.|,)? (?:[A-Z][a-z]*\.?,? )?(?:Conn|N\.Y|Mass|Ore|Hawaii|Ariz|Ala|Okla|La|Tenn|Ohio|Pa|Fla|Ind|Ill|Texas|Calif|Ky|Mich|Ga|Neb|Wis|Md|N\.J|R\.I|D\.C|Colo|Nev|Utah|Wash|Mo|N\.C|S\.C|Va|Minn|Iowa|Kan)\b|\s+(?:Harry|Hugh|XL|PeoplesBank|Hartford Civic|Madison Square|Lahaina|Moda|Veterans)|$)', t)
        loc = re.search(r'([A-Z][A-Za-z .\']+?, (?:Conn|N\.Y|Mass|Ore|Hawaii|Ariz|Ala|Okla|La|Tenn|Ohio|Pa|Fla|Ind|Ill|Texas|Calif|Ky|Mich|Ga|Neb|Wis|Md|N\.J|R\.I|D\.C|Colo|Nev|Utah|Wash|Mo|N\.C|S\.C|Va|Minn|Iowa|Kan)\.?)', t)
        g = {'date': date, 'dow': d.group(3), 'vs': vsat.group(1) if vsat else None, 'opp': (vsat.group(2).strip() if vsat else None), 'where': loc.group(1).strip() if loc else None, 'text': t[:260]}
        if r:
            a, b = int(r.group(2)), int(r.group(3))
            g.update({'res': r.group(1), 'pts': a if r.group(1) == 'W' else min(a, b), 'opp_pts': b if r.group(1) == 'W' else max(a, b), 'ot': (int(r.group(4) or 1) if r.group(4) is not None else 0)})
            # the site always prints the winner's score first
            if r.group(1) == 'W':
                g['pts'], g['opp_pts'] = max(a, b), min(a, b)
        games.append(g)
    return games


def main():
    out = {}
    report = []
    for y in range(1987, 2027):
        label = f'{y - 1}-{str(y)[2:]}'
        try:
            h = fetch(label)
        except Exception as e:
            report.append({'season': y, 'problem': f'fetch failed: {e}'})
            continue
        og = parse(h, y)
        out[y] = og
        app = json.load(open(os.path.join(ROOT, 'site', 'data', 'seasons', f'{y}.json')))['games']
        played = [g for g in app if g.get('res')]
        off = [g for g in og if g.get('res')]
        used = set()
        for g in played:
            # match by score first (unique enough), then by date
            cands = [(i, o) for i, o in enumerate(off) if i not in used and o['pts'] == g['pts'] and o['opp_pts'] == g['opp_pts']]
            if len(cands) > 1:
                cands = sorted(cands, key=lambda c: abs((datetime.date.fromisoformat(c[1]['date']) - datetime.date.fromisoformat(g['date'][:10])).days))
            if not cands:
                same_day = [o for o in off if o['date'] == g['date'][:10]]
                report.append({'season': y, 'game': g['id'], 'date': g['date'][:10], 'opp': g['opp']['name'], 'app': f"{g['res']} {g['pts']}-{g['opp_pts']}",
                               'official': (f"{same_day[0]['res']} {same_day[0]['pts']}-{same_day[0]['opp_pts']} vs {same_day[0]['opp']}" if same_day else 'no game with that score'), 'kind': 'score'})
                continue
            i, o = cands[0]
            used.add(i)
            if o['date'] != g['date'][:10]:
                report.append({'season': y, 'game': g['id'], 'opp': g['opp']['name'], 'app_date': g['date'][:10], 'official_date': o['date'], 'kind': 'date'})
            if o['res'] != g['res']:
                report.append({'season': y, 'game': g['id'], 'opp': g['opp']['name'], 'kind': 'result', 'app': g['res'], 'official': o['res']})
            on, an = norm(o.get('opp')), norm(g['opp']['name'])
            if on and an and not (on in an or an in on or on.split(' ')[0] == an.split(' ')[0]):
                report.append({'season': y, 'game': g['id'], 'kind': 'opponent', 'app': g['opp']['name'], 'official': o.get('opp')})
            site = 'A' if o.get('vs') == 'at' else None
            if site == 'A' and g['ha'] != 'A':
                report.append({'season': y, 'game': g['id'], 'opp': g['opp']['name'], 'kind': 'site', 'app': g['ha'], 'official': f"at ({o.get('where')})"})
            if o.get('vs') == 'vs' and g['ha'] == 'A':
                report.append({'season': y, 'game': g['id'], 'opp': g['opp']['name'], 'kind': 'site', 'app': 'A', 'official': f"vs ({o.get('where')})"})
            if (o.get('ot') or 0) != (int(re.match(r'(\d*)', g['ot']).group(1) or 1) if g.get('ot') else 0):
                report.append({'season': y, 'game': g['id'], 'opp': g['opp']['name'], 'kind': 'ot', 'app': g.get('ot'), 'official': o.get('ot')})
        for i, o in enumerate(off):
            if i not in used:
                report.append({'season': y, 'kind': 'missing_in_app', 'official': f"{o['date']} {o.get('vs')} {o.get('opp')} {o['res']} {o['pts']}-{o['opp_pts']}"})
        print(y, 'official games', len(off), 'app', len(played), flush=True)
    json.dump(out, open(os.path.join(OUTD, 'schedules.json'), 'w'), indent=1)
    json.dump(report, open(os.path.join(ROOT, 'dev', 'official_report.json'), 'w'), indent=1)
    import collections
    print(collections.Counter(r['kind'] if 'kind' in r else 'other' for r in report))


if __name__ == '__main__':
    main()
