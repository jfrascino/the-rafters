#!/usr/bin/env python3
"""Fetch UConn's official cumulative stats page for the current season (uconnhuskies.com, Sidearm) and re-parse all
official season sheets, so build.py can check every 2026-27 stat line against UConn's own numbers after each game."""
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
D = os.path.join(HERE, 'cache.nosync', 'official', 'stats')


def current_season():
    core = json.load(open(os.path.join(HERE, '..', 'site', 'data', 'core.json')))
    return (core.get('current') or {}).get('season') or core['seasons'][-1]['y']


def main():
    y = current_season()
    url = f'https://uconnhuskies.com/sports/mens-basketball/stats/{y - 1}-{str(y)[2:]}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36'})
    try:
        html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')
    except Exception as e:
        print(f'official stats page not reachable ({e}); keeping the last copy')
        return
    if 'Player name' not in html and 'Player uniform' not in html:
        print('official stats page has no player table yet (no games played?)')
        return
    os.makedirs(D, exist_ok=True)
    open(os.path.join(D, f'{y}.sidearm.html'), 'w').write(html)
    import official_cume
    official_cume.main()


if __name__ == '__main__':
    main()
