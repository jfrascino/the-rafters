#!/usr/bin/env python3
"""Compose pipeline/game_rulings.json: every settled game fact where the site and UConn's record book disagreed.

Inputs (pipeline/out/official/):
  verify_games.json        every app-vs-record-book disagreement, with researched truth where found
  research_batch_[ABC].json, research_dates.json   follow-up research on the unresolved ones
Policy for disagreements nobody could research further:
  overtime   take the record book's overtime count (our older sources don't carry OT at all)
  site       take the record book's home/away/neutral designation (UConn's own call; e.g. Connecticut Mutual Classic = home)
  date       leave as is and list it as open

Rulings are keyed by season + date + opponent (not game number), so inserting a missing game can't misapply them.
"""
import glob, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
OFF = os.path.join(HERE, 'out', 'official')
SITE = os.path.join(HERE, '..', 'site', 'data', 'seasons')

VENUES = [('CMC-NHC', 'New Haven Coliseum'), ('CMC-HCC', 'Hartford Civic Center'), ('HCC', 'Hartford Civic Center'), ('New Haven Coliseum', 'New Haven Coliseum'),
          ('Hartford Civic Center', 'Hartford Civic Center'), ('Boston Garden', 'Boston Garden'), ('Kemper Arena', 'Kemper Arena'), ('Webster Bank Arena', 'Webster Bank Arena'),
          ('(WB)', 'Webster Bank Arena'), ('(WBA)', 'Webster Bank Arena'), ('Madison Square Garden', 'Madison Square Garden')]


def site_of(t):
    t = (t or '').strip()
    first = t.split(' ')[0].split('(')[0].lower()
    kind = {'h': 'home', 'home': 'home', 'a': 'away', 'away': 'away', 'n': 'neutral', 'neutral': 'neutral'}.get(first)
    venue = next((v for k, v in VENUES if k in t), None)
    return kind, venue


def ot_of(t):
    t = str(t or '')
    m = re.match(r'(\d)?OT\b', t)
    if m:
        return f"{m.group(1)}OT" if m.group(1) and m.group(1) != '1' else 'OT'
    if t.isdigit():
        n = int(t)
        return None if n == 0 else ('OT' if n == 1 else f'{n}OT')
    return None


def main():
    v = json.load(open(os.path.join(OFF, 'verify_games.json')))
    research = {}
    for f in sorted(glob.glob(os.path.join(OFF, 'research_batch_*.json'))):
        for r in json.load(open(f)):
            research[r['key']] = r
    games = {}   # game id -> (date, opp name) as the site has them now
    for f in glob.glob(os.path.join(SITE, '*.json')):
        d = json.load(open(f))
        for g in d.get('games') or []:
            games[g['id']] = (g['date'][:10], (g.get('opp') or {}).get('name'))
    rulings, open_items = [], []
    for it in v['items']:
        gid, field = it.get('game_id'), it['field']
        key = f"{gid}|{field}" if gid else None
        r = research.get(key) if key else None
        truth = (r or {}).get('truth') or it.get('truth')
        conf = (r or {}).get('confidence') or it.get('confidence')
        srcs = (r or {}).get('sources') or it.get('sources') or []
        note = (r or {}).get('note') or it.get('note')
        if field == 'missing_in_app':
            continue   # added through manual_games.json
        if not gid or gid not in games:
            continue
        date, opp = games[gid]
        base = {'season': it['season'], 'date': date, 'opp': opp, 'field': field}
        if truth is None:
            if field == 'ot':
                ot = ot_of(it.get('recordbook'))
                if ot and ot_of(it.get('app')) != ot:
                    rulings.append({**base, 'set': {'ot': ot}, 'why': "UConn's record book lists overtime; our older sources don't record OT", 'confidence': 'record book', 'sources': []})
                continue
            if field == 'site':
                kind, venue = site_of(it.get('recordbook'))
                if kind:
                    s = {'site': kind}
                    if venue:
                        s['arena'] = venue
                    rulings.append({**base, 'set': s, 'why': f"UConn's record book designation: {it.get('recordbook')}", 'confidence': 'record book', 'sources': []})
                continue
            if field == 'result' and str(it.get('recordbook', '')).startswith('W'):
                continue   # handled with research (forfeit)
            open_items.append({**base, 'app': it.get('app'), 'recordbook': it.get('recordbook')})
            continue
        if it.get('app_correct') is True and not r:
            continue   # the site already has it right
        s = {}
        if field == 'score':
            m = re.match(r'([WL]) (\d+)-(\d+)', truth)
            if m:
                s = {'res': m.group(1), 'pts': int(m.group(2)), 'opp_pts': int(m.group(3))}
            if '(OT)' in truth:
                s['ot'] = 'OT'
        elif field == 'ot':
            ot = ot_of(truth)
            s = {'ot': ot} if ot else {}
        elif field == 'date' and re.fullmatch(r'\d{4}-\d\d-\d\d', truth or ''):
            if truth != date:
                s = {'date': truth}
        elif field == 'site':
            kind, venue = site_of(truth)
            if kind:
                s = {'site': kind, **({'arena': venue} if venue else {})}
        elif field == 'result' and 'forfeit' in truth.lower():
            s = {'res': 'W', 'forfeit': True, 'note': 'Lost 66-73 on the court; Utah later forfeited the game for using an ineligible player, so it counts as a UConn win.'}
        if s:
            rulings.append({**base, 'set': s, 'why': note or '', 'confidence': conf, 'sources': srcs[:3]})
    # follow-up date research
    rd = os.path.join(OFF, 'research_dates.json')
    if os.path.exists(rd):
        for r in json.load(open(rd)).get('rulings') or []:
            if r.get('truth') and re.fullmatch(r'\d{4}-\d\d-\d\d', str(r['truth'])) and r.get('confidence') in ('high', 'medium'):
                rulings.append({'research_key': r['key'], 'season': r.get('season'), 'opp': r.get('opponent'), 'set': {'date': r['truth']}, 'why': r.get('note') or '', 'confidence': r['confidence'], 'sources': (r.get('sources') or [])[:3], 'needs_match': True})
    out = {'_about': __doc__.strip().splitlines()[0], 'rulings': rulings, 'open': open_items}
    json.dump(out, open(os.path.join(HERE, 'game_rulings.json'), 'w'), indent=1)
    by = {}
    for r in rulings:
        for k in r['set']:
            by[k] = by.get(k, 0) + 1
    print(f"{len(rulings)} rulings ({by}); {len(open_items)} still open")
    for o in open_items:
        print('  open:', o)


if __name__ == '__main__':
    main()
