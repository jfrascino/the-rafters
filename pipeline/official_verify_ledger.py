"""Build the verification ledger out/official/verify_games.json from
  - out/official/verify_diffs_raw.json  (official_verify_games.py: app vs record book differences)
  - out/official/verify_rulings.json    (research rulings: truth, confidence, sources, note)
  - out/official/adjudication.json      (earlier settled disputes; reused, not redone)
"""
import json, os, re, collections

BASE = os.path.dirname(os.path.abspath(__file__))
OFF = os.path.join(BASE, 'out', 'official')
RAW = json.load(open(os.path.join(OFF, 'verify_diffs_raw.json')))
RUL = json.load(open(os.path.join(OFF, 'verify_rulings.json')))['rulings']
ADJ = json.load(open(os.path.join(OFF, 'adjudication.json')))
RBS = json.load(open(os.path.join(OFF, 'recordbook_seasons.json')))

# not real differences (both sides name the same team)
FALSE_POSITIVES = {('1991-1', 'opponent'): "Both are College of Charleston; the app's opponent key for this game is 'college of charleston' (spaces) while other seasons use 'college-of-charleston' - a key-format inconsistency, not a wrong opponent."}


def key_of(x):
    if x.get('game_id'):
        return f"{x['game_id']}|{x['field']}"
    return f"{x['season']}:{x['date']}:{x['opp']}|{x['field']}"


def ot_count(s):
    if s is None:
        return None
    s = str(s)
    if re.search(r'no ot', s, re.I) or s.strip() == '0':
        return 0
    m = re.search(r'(\d)\s*OT', s, re.I)
    if m:
        return int(m.group(1))
    if re.search(r'\bOT\b', s, re.I):
        return 1
    if s.strip().isdigit():
        return int(s)
    return None


def app_correct(field, app, truth):
    if truth is None:
        return None
    t = str(truth)
    if field in ('score', 'result'):
        m1 = re.match(r'([WL]) (\d+)-(\d+)', str(app) or '')
        m2 = re.search(r'([WL]) (\d+)-(\d+)', t)
        if m1 and m2:
            return m1.groups() == m2.groups()
        return None
    if field == 'date':
        m = re.search(r'\d{4}-\d\d-\d\d', t)
        return (m.group(0) == str(app)[:10]) if m else None
    if field == 'site':
        return t[:1] == str(app)[:1]
    if field == 'ot':
        tc = ot_count(t)
        return None if tc is None else tc == int(app or 0)
    if field == 'missing_in_app':
        return not t.lower().startswith('played')
    if field == 'missing_in_recordbook':
        return t.lower().startswith('played')
    return None


def main():
    adj = {(d['game'], d['field']): d for d in ADJ['decisions']}
    items = []
    unresolved = []
    for x in RAW['diffs']:
        k = key_of(x)
        gid, field = x.get('game_id'), x['field']
        if (gid, field) in FALSE_POSITIVES:
            continue
        it = {'game_id': gid, 'season': x.get('season') or (int(gid.split('-')[0]) if gid else None), 'date': x['date'], 'opp': x['opp'],
              'field': field, 'app': x['app'], 'recordbook': x['recordbook']}
        r = RUL.get(k)
        a = adj.get((gid, field))
        if r:
            it.update({'truth': r['truth'], 'confidence': r['confidence'], 'sources': r['sources'], 'note': r.get('note')})
            if r.get('category'):
                it['category'] = r['category']
        elif a:
            it.update({'truth': a['truth'], 'confidence': a['confidence'], 'sources': a['sources'][:3],
                       'note': 'Settled earlier in adjudication.json (winner: ' + a.get('winner', '?') + '). ' + (a.get('note') or '')})
            it['adjudicated'] = True
        else:
            it.update({'truth': None, 'confidence': None, 'sources': [], 'note': 'UNRESOLVED'})
            unresolved.append(k)
        ac = r.get('app_correct') if r and 'app_correct' in r else app_correct(field, x['app'], it['truth'])
        it['app_correct'] = ac
        it['recordbook_correct'] = r.get('recordbook_correct') if r and 'recordbook_correct' in r else None
        if 'category' not in it:
            it['category'] = 'convention' if (r and r.get('confidence') == 'medium' and field == 'site' and 'onvention' in (r.get('note') or '')) else 'fact'
        items.append(it)
    by_field = collections.Counter(i['field'] for i in items)
    wrong = [i for i in items if i['app_correct'] is False]
    out = {
        '_about': 'Every played UConn game 1977-78..2025-26 in the app (site/data/seasons/{y}.json) compared with UConn\'s 2026-27 Record Book season-by-season results (out/official/recordbook_games.json), matched by date (+-1 day) and opponent. Each item is one disagreement; truth is from independent sources (opponent archives/media guides, newspapers, ESPN), reusing adjudication.json where already settled. app_correct=false means the app shows the wrong value. category=convention marks site-designation calls (off-campus venue) rather than factual errors.',
        'checked_games': RAW['checked_games'],
        'summary': {'disagreements': len(items), 'by_field': dict(by_field), 'app_wrong': len(wrong),
                    'app_wrong_by_field': dict(collections.Counter(i['field'] for i in wrong)),
                    'app_wrong_facts': len([i for i in wrong if i['category'] == 'fact']),
                    'unresolved': unresolved},
        'items': items,
        'season_checks': RAW['season_checks'],
        'data_quality_notes': [v for v in FALSE_POSITIVES.values()],
    }
    json.dump(out, open(os.path.join(OFF, 'verify_games.json'), 'w'), indent=1, ensure_ascii=False)
    return out


if __name__ == '__main__':
    o = main()
    print(json.dumps(o['summary'], indent=1))
