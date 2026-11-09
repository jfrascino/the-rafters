"""Earlier college seasons of current transfers (run by hand; earlier seasons don't change).

Sports-Reference (via sr_fetch, rate limited) is the source of the rows; ESPN's athlete stats API is the second source.
A season is written only with each stat that both agree on (GP/GS equal; MIN/PTS/REB/AST/STL/BLK within 0.1;
FG%/3P%/FT% within 0.2 points). A stat the two disagree on is left None and listed in 'disagreements'.
Run with /usr/bin/python3 (needs bs4):  python3 pipeline/transfer_seasons.py
Output: pipeline/out/official/transfer_seasons.json, used by build.py when SR has no other-school rows for a player.
"""
import os, re, sys, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_fetch, sr_parse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'official', 'transfer_seasons.json')
PLAYERS = {   # build pid -> (SR id, ESPN id)
    'espn-5144124': ('nikolas-khamenia-1', '5144124'),
    'espn-5060718': ('jaye-nash-1', '5060718'),
    'espn-5292602': ('najai-hines-1', '5292602'),
    'espn-5312293': ('oskar-giltay-1', '5312293'),
    'espn-5175080': ('nils-machowski-1', '5175080'),
    'espn-5311500': ('elmir-dzafic-1', '5311500'),
    'espn-4896885': ('isaiah-shaw-1', '4896885'),
}
CNT = [('g', 'games', 0), ('gs', 'games_started', 0)]
AVG = [('mp', 'mp_per_g', 'MIN', 0.1001), ('pts', 'pts_per_g', 'PTS', 0.1001), ('trb', 'trb_per_g', 'REB', 0.1001),
       ('ast', 'ast_per_g', 'AST', 0.1001), ('stl', 'stl_per_g', 'STL', 0.1001), ('blk', 'blk_per_g', 'BLK', 0.1001)]
PCT = [('fg_pct', 'fg_pct', 'FG', 'FG%'), ('fg3_pct', 'fg3_pct', '3PT', '3P%'), ('ft_pct', 'ft_pct', 'FT', 'FT%')]


def espn_seasons(eid):
    u = f'https://site.web.api.espn.com/apis/common/v3/sports/basketball/mens-college-basketball/athletes/{eid}/stats'
    d = json.loads(urllib.request.urlopen(urllib.request.Request(u), timeout=30).read())
    out = {}
    for c in d['categories']:
        if c['name'] == 'averages':
            for s in c['statistics']:
                out[s['season']['displayName']] = (s.get('teamSlug'), dict(zip(c['labels'], s['stats'])))
    return out


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    res = {}
    for pid, (srid, eid) in PLAYERS.items():
        html = sr_fetch.fetch(f'/cbb/players/{srid}.html')
        sp = sr_parse.parse_player(html, srid)
        rows = (sp.get('tables') or {}).get('players_per_game', {}).get('rows', [])
        es = espn_seasons(eid)
        seasons, dis = [], []
        for tr in rows:
            team = tr.get('team_name_abbr') or ''
            yid = tr.get('year_id') or ''
            m = re.match(r'(\d{4})-(\d{2})', yid)
            if not m or 'uconn' in team.lower() or 'connecticut' in team.lower():
                continue
            key = m.group(0)
            eslug, e = es.get(key, (None, None))
            row = {'y': int(m.group(1)) + 1, 'school': team, 'uconn': False, 'cls': tr.get('class')}
            def bad(stat, a, b):
                dis.append({'season': key, 'school': team, 'stat': stat, 'sr': a, 'espn': b})
                return None
            if e is None:
                row['checked'] = 'sr-only'
                for k, sk, *_ in CNT + AVG:
                    row[k] = tr.get(sk)
                for k, sk, *_ in PCT:
                    row[k] = tr.get(sk)
                dis.append({'season': key, 'school': team, 'stat': 'all', 'sr': 'present', 'espn': 'missing'})
            else:
                row['checked'] = 'sr+espn'
                for k, sk, *_ in CNT:
                    a = tr.get(sk); b = fnum(e['GP' if k == 'g' else 'GS'])
                    row[k] = a if a is not None and b is not None and a == b else bad(k, a, b)
                for k, sk, lab, tol in AVG:
                    a = tr.get(sk); b = fnum(e[lab])
                    row[k] = a if a is not None and b is not None and abs(a - b) <= tol else bad(k, a, b)
                for k, sk, made, lab in PCT:
                    a = tr.get(sk)
                    mk, att = (fnum(x) for x in e[made].split('-'))
                    b = fnum(e[lab])
                    if att == 0:   # no attempts: both sources must show a blank
                        row[k] = None if a is None else bad(k, a, 'no attempts')
                    else:
                        row[k] = a if a is not None and b is not None and abs(a * 100 - b) <= 0.2001 else bad(k, a, b)
            seasons.append(row)
        # ESPN seasons (non-UConn) SR lacks
        sr_keys = {re.match(r'\d{4}-\d{2}', t.get('year_id') or '').group(0) for t in rows if re.match(r'\d{4}-\d{2}', t.get('year_id') or '')}
        for key, (slug, _) in es.items():
            if key not in sr_keys and slug and 'uconn' not in slug:
                dis.append({'season': key, 'school': slug, 'stat': 'all', 'sr': 'missing', 'espn': 'present (not added)'})
        res[pid] = {'name': sp.get('name'), 'sr_id': srid, 'espn_id': eid, 'seasons': seasons, 'disagreements': dis}
        print(pid, sp.get('name'), len(seasons), 'seasons,', len(dis), 'disagreements')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
