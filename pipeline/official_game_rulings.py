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


# rulings found after the record-book sweep (e.g. by the Moments research), with their evidence
MANUAL = [
    {'season': 1978, 'date': '1978-01-21', 'opp': 'Providence', 'field': 'score', 'set': {'res': 'L', 'pts': 47, 'opp_pts': 57, 'site': 'home', 'arena': 'New Haven Coliseum'},
     'why': "UConn's record book (1977-78 results: '1/21 Providence at New Haven Coliseum L 47-57'), the Manchester Evening Herald (Jan. 23, 1978) "
            "and the NYT headline all have 57-47; Sports-Reference's 49-57 is the outlier. The game was moved to the New Haven Coliseum after "
            "the Hartford Civic Center roof collapsed on Jan. 18 (Herald preview, Jan. 21, 1978).",
     'confidence': 'high', 'sources': ['https://uconnhuskies.com/documents/download/2026/8/13/RECORD_BOOK_26-27_V2_.pdf',
                                       'https://cdn.manchesterhistory.org/News/Manchester%20Evening%20Hearld_1978-01-23.pdf#page=5',
                                       'https://www.nytimes.com/1978/01/22/archives/providence-57-uconn-47.html',
                                       'https://cdn.manchesterhistory.org/News/Manchester%20Evening%20Hearld_1978-01-21.pdf#page=4']},
]


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
        if not gid:
            continue
        # key on the game as it was when verified (the original Sports-Reference date), not today's site data,
        # which already carries earlier rulings and renumbered game ids
        date, opp = it['date'], it['opp']
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
        from datetime import date as _d
        by_season = {}   # games as originally verified (date before any ruling), per season
        for it in v['items']:
            if it.get('game_id') and it.get('date') and it.get('opp'):
                by_season.setdefault(int(it['season']), []).append((it['date'], it['opp']))
        for gid, (gdate, gopp) in games.items():   # games nobody disputed keep their dates, so today's data is fine for them
            y_ = int(gid.split('-')[0])
            if not any(go == gopp for _, go in by_season.get(y_, [])):
                by_season.setdefault(y_, []).append((gdate, gopp))
        for r in json.load(open(rd)).get('rulings') or []:
            truth = str(r.get('truth') or '')
            if not re.fullmatch(r'\d{4}-\d\d-\d\d', truth) or r.get('confidence') not in ('high', 'medium'):
                continue
            y = int(str(r.get('season'))[:4]) + 1
            opp_name = re.split(r'\s*[(-]', r.get('opponent') or '')[0].strip().lower()
            cands = [(gd, go) for gd, go in by_season.get(y, []) if go and (go.lower() in opp_name or opp_name in go.lower())]
            if not cands:
                open_items.append({'season': y, 'research_key': r['key'], 'note': 'researched date matched no game'})
                continue
            t = _d.fromisoformat(truth)
            gd, go = min(cands, key=lambda c: abs((_d.fromisoformat(c[0]) - t).days))
            open_items[:] = [o for o in open_items if not (o.get('season') == y and o.get('opp') == go and o.get('field') == 'date')]
            if gd != truth:
                rulings.append({'season': y, 'date': gd, 'opp': go, 'field': 'date', 'set': {'date': truth}, 'why': r.get('note') or '', 'confidence': r['confidence'],
                                'sources': (r.get('sources') or [])[:3], 'research_key': r['key']})
    rulings += MANUAL
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
