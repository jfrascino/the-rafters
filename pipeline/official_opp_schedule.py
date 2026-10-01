"""Opponent schools' official (Sidearm) schedule archives: fetch
https://{site}/sports/mens-basketball/schedule/{season} and print the text of every game vs UConn.
usage: python3 official_opp_schedule.py site season [season ...]
"""
import re, sys, os, subprocess, html as H
BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, 'cache.nosync/official/opp')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'

def page(site, season, sport='mens-basketball'):
    path = os.path.join(CACHE, f'sched_{site}_{season}.html')
    if not os.path.exists(path) or os.path.getsize(path) < 20000:
        subprocess.run(['curl', '-sL', '-m', '40', '-A', UA, f'https://{site}/sports/{sport}/schedule/{season}', '-o', path])
    return open(path, encoding='utf-8', errors='replace').read() if os.path.exists(path) else ''

def text(h):
    t = re.sub(r'<script.*?</script>', ' ', h, flags=re.S)
    t = re.sub(r'<style.*?</style>', ' ', t, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = H.unescape(t)
    return re.sub(r'\s+', ' ', t)

DATE = r'(?:Jan|Feb|Mar|Apr|Nov|Dec|Oct)\.? \d{1,2} \((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\)'

def seasons_available(h):
    import json
    m = re.search(r'<script type="application/json"[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    if not m:
        return set(re.findall(r'schedule/((?:19|20)\d\d-\d\d)', h))
    arr = json.loads(m.group(1))
    return {x for x in arr if isinstance(x, str) and re.fullmatch(r'(19|20)\d\d-\d\d', x)}

def games(site, season):
    h = page(site, season)
    t = text(h)
    if f'{season} Men' not in t:
        av = sorted(seasons_available(h))
        return [f'(season not in archive; archive has {len(av)} seasons: {av[:3]}..{av[-2:]})']
    # the season's own list starts after the carousel; cut at the season title if present
    k = t.find(f'{season} Men')
    body = t[k:] if k >= 0 else t
    out = []
    for m in re.finditer(r'\b(vs\.?|at)\s+(?:#\d+\s+)?(UConn|Connecticut|University of Connecticut)\b(?! State)(?!\s+College)', body):
        seg = body[m.start(): m.start() + 260]
        d = re.search(DATE, seg)
        if d:
            seg = seg[: d.end()]
        out.append(seg)
    return out

if __name__ == '__main__':
    site = sys.argv[1]
    for season in sys.argv[2:]:
        g = games(site, season)
        if not g:
            print(f'{site} {season}: (no UConn game found)')
        for s in g:
            print(f'{site} {season}: {s}')
