"""Compare every played game in the app (site/data/seasons/{y}.json) with UConn's
2026-27 record book season-by-season results (out/official/recordbook_games.json).

Writes out/official/verify_diffs_raw.json (machine diff list) and, merged with the
research rulings in out/official/verify_rulings.json, the ledger
out/official/verify_games.json.
"""
import json, os, re, datetime, collections

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BASE, '..', 'site', 'data', 'seasons')
OFF = os.path.join(BASE, 'out', 'official')
RB = json.load(open(os.path.join(OFF, 'recordbook_games.json')))
RBS = json.load(open(os.path.join(OFF, 'recordbook_seasons.json')))
ADJ = json.load(open(os.path.join(OFF, 'adjudication.json')))

# record-book spelling -> app opponent key
ALIAS = {
    'Arizona St.': 'arizona-state', 'Brigham Young': 'brigham-young', 'BYU': 'brigham-young',
    'Boston Coll.': 'boston-college', 'Boston Col.': 'boston-college',
    'Boston Univ.': 'boston-university', 'Boston U.': 'boston-university', 'Brooklyn College': 'brooklyn',
    'Cent. Arkansas': 'central-arkansas', 'Central Conn.': 'central-connecticut-state', 'Central Connecticut': 'central-connecticut-state',
    'Charleston': 'college-of-charleston', 'Col. of Charleston': 'college-of-charleston', 'Col. of Charlstn': 'college-of-charleston',
    'N.C.-Charlotte': 'charlotte', 'Tenn.-Chatt.': 'chattanooga', 'Coppin St.': 'coppin-state',
    'Delaware St.': 'delaware-state', 'Detroit': 'detroit-mercy', 'ECU': 'east-carolina', 'East Texas A&M': 'texas-am-commerce',
    'E. Michigan': 'eastern-michigan', 'Eastern Wash.': 'eastern-washington', 'Fair. Dickinson': 'fairleigh-dickinson',
    'Florida A&M': 'florida-am', 'Fla. International': 'florida-international', 'Florida St.': 'florida-state',
    'G.Washington': 'george-washington', 'G. Washington': 'george-washington', 'Grambling St.': 'grambling',
    'Iowa St.': 'iowa-state', 'UMKC': 'missouri-kansas-city', 'Louisiana State': 'louisiana-state', 'LSU': 'louisiana-state',
    'LaSalle': 'la-salle', 'Long Island': 'long-island-university', 'LIU': 'long-island-university', 'La. Tech': 'louisiana-tech',
    'Loyola-Md.': 'loyola-md', 'Loy. Marymount': 'loyola-marymount', 'Md-Eastern Shore': 'maryland-eastern-shore',
    'Md.-Eastern Shore': 'maryland-eastern-shore', 'UMES': 'maryland-eastern-shore', 'McNeese St.': 'mcneese-state',
    'Miami': 'miami-fl', 'Michigan St.': 'michigan-state', 'Mississippi St.': 'mississippi-state', 'Miss. Valley St.': 'mississippi-valley-state',
    'Momouth': 'monmouth', 'Morgan St.': 'morgan-state', 'North Carolina St.': 'north-carolina-state', 'No. Carolina St.': 'north-carolina-state',
    'New Mexico St.': 'new-mexico-state', 'N. Carolina': 'north-carolina', 'North. Arizona': 'northern-arizona', 'Ohio U.': 'ohio',
    'Ohio University': 'ohio', 'Oklahoma St.': 'oklahoma-state', 'Mississippi': 'mississippi', 'SMU': 'southern-methodist',
    "St. Joseph's": 'saint-josephs', 'Saint Joseph’s': 'saint-josephs', "St. Mary's-CA": 'saint-marys-ca', "Saint Mary's": 'saint-marys-ca',
    'St. Peter’s': 'saint-peters', "Saint Peter's": 'saint-peters', 'San Diego St.': 'san-diego-state', 'USF': 'south-florida',
    'South Florida': 'south-florida', 'Southern Conn.': 'southern-connecticut', 'St. John’s': 'st-johns-ny', "St. John's": 'st-johns-ny',
    'Texas Christian': 'texas-christian', 'SW Texas St.': 'texas-state', 'Towson St.': 'towson', 'Towson State': 'towson',
    'U.S. International': 'alliant-international', 'Alabama-Birm.': 'alabama-birmingham', 'Albany': 'albany-ny',
    'Central Florida': 'central-florida', 'UCF': 'central-florida', 'UMBC': 'maryland-baltimore-county', 'UMass-Lowell': 'massachusetts-lowell',
    'UMass Lowell': 'massachusetts-lowell', 'UNC Asheville': 'north-carolina-asheville', 'UNC-Wilmington': 'north-carolina-wilmington',
    'UNC Wilmington': 'north-carolina-wilmington', 'S. California': 'southern-california', 'Texas-Arlington': 'texas-arlington',
    'TX-San Antonio': 'texas-san-antonio', 'Va-Commonwealth': 'virginia-commonwealth', 'VCU': 'virginia-commonwealth',
    'W. Virginia': 'west-virginia', 'W. Kentucky': 'western-kentucky', 'Wichita St.': 'wichita-state', 'William & Mary': 'william-mary',
    'Morehead State': 'morehead-state', 'Morgan State': 'morgan-state', 'Delaware State': 'delaware-state', 'Coppin State': 'coppin-state',
    'Arkansas-Pine Bluff': 'arkansas-pine-bluff', 'Gardner-Webb': 'gardner-webb', 'Texas A&M': 'texas-am',
}
AMBIG = {'St. Francis': {'saint-francis-pa', 'st-francis-ny'}}


def slug(s):
    s = s.lower().replace('’', "'").replace('&', '')
    s = re.sub(r"[.']", '', s)
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def rb_keys(name):
    if name in AMBIG:
        return AMBIG[name]
    if name in ALIAS:
        return {ALIAS[name]}
    return {slug(name)}


def d(s):
    return datetime.date.fromisoformat(s[:10])


def app_ot(g):
    o = g.get('ot')
    if not o:
        return 0
    m = re.match(r'(\d*)OT', str(o))
    return int(m.group(1) or 1) if m else 1


def fmt_score(res, a, b, ot=0):
    return f"{res} {a}-{b}" + (f" ({ot}OT)" if ot > 1 else ' (OT)' if ot == 1 else '')


def main():
    diffs = []
    season_checks = []
    checked = 0
    matches = {}
    for y in range(1978, 2027):
        S = json.load(open(os.path.join(SITE, f'{y}.json')))
        app = [g for g in S['games'] if g.get('res')]
        rb = RB[str(y)]
        used = set()
        pair = {}
        # pass 1..4: same opponent within 0, 1, 3 days, then anywhere in season
        for tol in (0, 1, 3, 400):
            for g in app:
                if g['id'] in pair:
                    continue
                k = g['opp'].get('key')
                best = None
                for i, r in enumerate(rb):
                    if i in used or k not in rb_keys(r['opp']):
                        continue
                    dd = abs((d(r['date']) - d(g['date'])).days)
                    if dd <= tol and (best is None or dd < best[0]):
                        best = (dd, i)
                if best:
                    pair[g['id']] = best[1]
                    used.add(best[1])
        # pass 5: date-only (opponent disagreement)
        for g in app:
            if g['id'] in pair:
                continue
            for i, r in enumerate(rb):
                if i not in used and abs((d(r['date']) - d(g['date'])).days) <= 1:
                    pair[g['id']] = i
                    used.add(i)
                    break
        for g in app:
            checked += 1
            if g['id'] not in pair:
                diffs.append({'game_id': g['id'], 'date': g['date'][:10], 'opp': g['opp']['name'], 'field': 'missing_in_recordbook',
                              'app': fmt_score(g['res'], g['pts'], g['opp_pts'], app_ot(g)) + f" {g['ha']}", 'recordbook': None})
                continue
            r = rb[pair[g['id']]]
            matches[g['id']] = r
            base = {'game_id': g['id'], 'date': g['date'][:10], 'opp': g['opp']['name'], 'type': g['type']}
            if g['opp'].get('key') not in rb_keys(r['opp']):
                diffs.append({**base, 'field': 'opponent', 'app': g['opp']['name'], 'recordbook': r['opp']})
            if g['date'][:10] != r['date']:
                diffs.append({**base, 'field': 'date', 'app': g['date'][:10], 'recordbook': r['date'], 'rb_note': r.get('note')})
            if g['res'] != r['res']:
                diffs.append({**base, 'field': 'result', 'app': fmt_score(g['res'], g['pts'], g['opp_pts']), 'recordbook': fmt_score(r['res'], r['pts'], r['opp_pts']), 'rb_printed': r['printed'], 'rb_note': r.get('note')})
            elif (g['pts'], g['opp_pts']) != (r['pts'], r['opp_pts']):
                diffs.append({**base, 'field': 'score', 'app': fmt_score(g['res'], g['pts'], g['opp_pts']), 'recordbook': fmt_score(r['res'], r['pts'], r['opp_pts']), 'rb_printed': r['printed']})
            if g['ha'] != r['site']:
                diffs.append({**base, 'field': 'site', 'app': g['ha'] + (f" ({g.get('arena')})" if g.get('arena') else ''), 'recordbook': r['site'] + (f" {r['site_raw']}" if r.get('site_raw') else ''),
                              'rb_line': r['line']})
            if app_ot(g) != r['ot']:
                diffs.append({**base, 'field': 'ot', 'app': app_ot(g), 'recordbook': r['ot'], 'rb_printed': r['printed'] + ('' if not r['ot'] else f" {r['ot']}ot")})
        for i, r in enumerate(rb):
            if i not in used:
                diffs.append({'game_id': None, 'season': y, 'date': r['date'], 'opp': r['opp'], 'field': 'missing_in_app', 'app': None,
                              'recordbook': fmt_score(r['res'], r['pts'], r['opp_pts'], r['ot']) + f" {r['site']}" + (f" {r['site_raw']}" if r.get('site_raw') else ''), 'rb_line': r['line']})
        # season checks
        hs = RBS[str(y)]
        gw = sum(1 for g in app if g['res'] == 'W')
        gl = sum(1 for g in app if g['res'] == 'L')
        sc = {'season': y, 'label': S.get('label'),
              'app_wl': f"{S.get('w')}-{S.get('l')}", 'app_games_wl': f'{gw}-{gl}', 'recordbook_wl': '-'.join(map(str, hs['overall'])),
              'app_conf': f"{S.get('cw')}-{S.get('cl')}" if S.get('cw') is not None else None, 'recordbook_conf': '-'.join(map(str, hs['conf'])) if hs.get('conf') else None,
              'app_coach': S.get('coach'), 'recordbook_coach': hs.get('coach'),
              'recordbook_games': len(rb), 'app_games': len(app)}
        sc['wl_match'] = sc['app_wl'] == sc['recordbook_wl']
        sc['games_wl_match'] = sc['app_games_wl'] == sc['recordbook_wl']
        sc['conf_match'] = sc['app_conf'] == sc['recordbook_conf']
        sc['coach_match'] = (S.get('coach') or '').split()[-1] == (hs.get('coach') or '').split()[-1] and (S.get('coach') or '')[:3] == (hs.get('coach') or '')[:3]
        season_checks.append(sc)
    json.dump({'checked_games': checked, 'diffs': diffs, 'season_checks': season_checks}, open(os.path.join(OFF, 'verify_diffs_raw.json'), 'w'), indent=1, ensure_ascii=False)
    return checked, diffs, season_checks


if __name__ == '__main__':
    checked, diffs, sc = main()
    c = collections.Counter(x['field'] for x in diffs)
    print('checked', checked, 'diffs', len(diffs), dict(c))
    for s in sc:
        if not (s['wl_match'] and s['conf_match'] and s['coach_match'] and s['games_wl_match']):
            print('SEASON', s)
