"""Fetch a Sidearm 'opponent-history' page (an opponent school's own archive of every game vs UConn)
and decode its Nuxt (devalue) payload into rows: date, location, team score, opponent score, result,
recap title. Usage: python3 official_opp_history.py <url> [cache_name]
"""
import json, re, sys, os, subprocess, hashlib
BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, 'cache.nosync/official/opp')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'

def fetch(url, name=None):
    name = name or hashlib.md5(url.encode()).hexdigest()[:12]
    path = os.path.join(CACHE, name + '.html')
    if not os.path.exists(path) or os.path.getsize(path) < 5000:
        subprocess.run(['curl', '-sL', '-A', UA, url, '-o', path], check=True)
    return open(path, encoding='utf-8', errors='replace').read()

def unflatten(arr):
    memo = {}
    def h(i):
        if isinstance(i, int) and i < 0:
            return None
        if i in memo:
            return memo[i]
        v = arr[i]
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in ('Reactive', 'ShallowReactive', 'Ref', 'ShallowRef', 'EmptyRef', 'EmptyShallowRef'):
                r = h(v[1]) if len(v) > 1 else None
                memo[i] = r
                return r
            if v and isinstance(v[0], str) and v[0] in ('Set', 'Map', 'Date', 'BigInt', 'null', 'undefined', 'NaN', 'Infinity', '-Infinity', '-0', 'RegExp', 'Object'):
                memo[i] = v
                return v
            out = []
            memo[i] = out
            for x in v:
                out.append(h(x) if isinstance(x, int) else x)
            return out
        if isinstance(v, dict):
            out = {}
            memo[i] = out
            for k, x in v.items():
                out[k] = h(x) if isinstance(x, int) else x
            return out
        memo[i] = v
        return v
    return h(0)

def games(html):
    m = re.search(r'<script type="application/json"[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    arr = json.loads(m.group(1))
    root = unflatten(arr)
    rows = []
    def walk(o, depth=0):
        if depth > 40:
            return
        if isinstance(o, dict):
            if 'gameDate' in o and ('teamScore' in o or 'result' in o):
                rows.append(o)
            for v in o.values():
                walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                walk(v, depth + 1)
    walk(root)
    out = []
    seen = set()
    for r in rows:
        key = (r.get('gameId'), r.get('gameDate'))
        if key in seen:
            continue
        seen.add(key)
        res = r.get('result') if isinstance(r.get('result'), dict) else {}
        media = r.get('media') if isinstance(r.get('media'), dict) else {}
        recap = None
        rc = (res or {}).get('recap')
        if isinstance(rc, dict):
            recap = rc.get('url')
        out.append({'date': r.get('gameDate'), 'loc_ind': r.get('gameLocationIndicator'), 'location': r.get('gameLocation'),
                    'team_score': r.get('teamScore'), 'opp_score': r.get('opponentScore'), 'status': r.get('resultStatus'),
                    'season': r.get('seasonTitle'), 'conf': r.get('gameConference'), 'postscore': r.get('resultPostscoreInfo'),
                    'school_is_home': r.get('schoolIsHome'), 'recap': recap})
    out.sort(key=lambda x: x['date'] or '')
    return out

if __name__ == '__main__':
    url = sys.argv[1]
    html = fetch(url, sys.argv[2] if len(sys.argv) > 2 else None)
    rows = games(html)
    lo = sys.argv[3] if len(sys.argv) > 3 else '1977-08-01'
    hi = sys.argv[4] if len(sys.argv) > 4 else '2026-08-01'
    for r in rows:
        if lo <= (r['date'] or '') <= hi:
            print(json.dumps(r, ensure_ascii=False))
    print(len(rows), 'rows total', file=sys.stderr)
