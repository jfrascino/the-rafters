#!/usr/bin/env python3
"""Current UConn roster straight from uconnhuskies.com (names, numbers, headshots, bio links).

ESPN's college roster lags a season behind, so the official page is the source of truth for the current team.
python3 pipeline/official_roster.py → pipeline/out/official/roster_current.json
"""
import json, os, re, html, urllib.request, urllib.parse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'official')
os.makedirs(OUT, exist_ok=True)
URL = 'https://uconnhuskies.com/sports/mens-basketball/roster'


def main():
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (the-rafters fan project)'})
    h = urllib.request.urlopen(req, timeout=40).read().decode('utf-8', 'replace')
    players, seen = [], set()
    for blk in h.split('data-test-id="s-person-card')[1:]:
        t = html.unescape(blk[:12000])
        m = re.search(r'aria-label="(.+?) jersey number (\w+) full bio"', t)
        if not m:
            continue
        name, num = m.group(1).strip(), m.group(2)
        if name in seen:
            continue
        seen.add(name)
        img = None
        src = re.search(r'https://images\.sidearmdev\.com/crop\?url=([^&"\s]+)', t)
        if src:
            img = urllib.parse.unquote(src.group(1))
        bio = re.search(r'href="(/sports/mens-basketball/roster/[^"]+)"', t)
        players.append({'name': name, 'num': num, 'headshot': img, 'bio': ('https://uconnhuskies.com' + bio.group(1)) if bio else None})
    if not players:
        raise SystemExit('roster page parsed 0 players — layout changed?')
    json.dump({'fetched': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'source': URL, 'players': players},
              open(os.path.join(OUT, 'roster_current.json'), 'w'), indent=1)
    print(f'official roster: {len(players)} players, {sum(1 for p in players if p["headshot"])} headshots')


if __name__ == '__main__':
    main()
