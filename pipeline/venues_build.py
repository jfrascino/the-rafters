#!/usr/bin/env python3
"""Home floors: every building UConn has called home -> site/data/venues.json

  official   UConn's record by building and its streaks (record book p. 65, out/official/venue_records.json)
  names      each building's names through time with exact dates (out/official/venues.json "renames", researched)
  since      everything Storrs Lore can count itself: the true building of every game from 1986-87 on
             (out/official/venues.json "game_venue_era", from the record book's site codes) joined to the site's games
Where the record book and our own count cover the same span (Gampel, Bridgeport), they must agree; a mismatch prints."""
import collections, glob, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, '..', 'site', 'data')
OFF = os.path.join(HERE, 'out', 'official')
HOME = ['gampel', 'hartford_arena', 'greer', 'new_haven_coliseum', 'bridgeport_arena']
SHORT = {'gampel': 'Gampel Pavilion', 'hartford_arena': 'The Hartford arena', 'greer': 'The Field House', 'new_haven_coliseum': 'New Haven Coliseum',
         'bridgeport_arena': 'The Bridgeport arena'}
# fan-facing summaries; every fact is taken from the researched building notes in out/official/venues.json (sources listed there)
BLURB = {
    'greer': 'Opened December 1, 1954, with a game against Rhode Island. UConn played here until Gampel Pavilion opened; the last men\'s game was January 24, 1990, against Central Connecticut. It was renamed for coach Hugh Greer in 1991, after basketball had moved out, and is now an indoor track facility.',
    'gampel': 'Opened in January 1990 and never renamed. The first men\'s game was January 27, 1990: UConn 72, St. John\'s 58. Capacity has grown from 8,241 in 1990 to 10,244 today.',
    'hartford_arena': 'Opened January 9, 1975. The roof collapsed on January 18, 1978, and the arena stayed closed until February 1980. It became the XL Center on December 18, 2007, and PeoplesBank Arena on June 2, 2025.',
    'new_haven_coliseum': 'Opened October 4, 1972 (formally the New Haven Veterans Memorial Coliseum). UConn played part-time home games here from 1978 to 1987. The city closed it on September 1, 2002, and it was imploded on January 20, 2007.',
    'bridgeport_arena': 'Opened October 10, 2001, as the Arena at Harbor Yard; Webster Bank Arena from January 6, 2011; Total Mortgage Arena since March 7, 2022. Both UConn games here came in the Webster Bank Arena years.',
}
FULL = {'gampel'}   # buildings whose every UConn game is in the game-by-game data (so our streaks are complete)


def jload(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d


def main():
    V = jload(os.path.join(OFF, 'venues.json'), {}) or {}
    R = jload(os.path.join(OFF, 'venue_records.json'), {}) or {}
    bld = {b['key']: b for b in V.get('renames') or []}
    era = {x['id']: x for x in V.get('game_venue_era') or []}
    games, det = {}, {}
    for f in glob.glob(os.path.join(SITE, 'seasons', '*.json')):
        s = jload(f, {})
        for g in s.get('games') or []:
            if g.get('res'):
                games[g['id']] = {**g, 'y': s['y']}
    for f in glob.glob(os.path.join(SITE, 'games', '*.json')):
        det.update(jload(f, {}) or {})
    moments = {m['gid']: m for m in (jload(os.path.join(SITE, 'moments.json'), {}) or {}).get('moments') or [] if m.get('gid')}

    by = collections.defaultdict(list)
    for gid, e in era.items():
        g = games.get(gid)
        if g and e.get('building_key'):
            by[e['building_key']].append({**g, 'era_name': e.get('era_name'), 'att': (det.get(gid) or {}).get('att') or g.get('att')})
    out = []
    for key in HOME + sorted(k for k in by if k not in HOME and any(g['ha'] == 'H' for g in by[k])):
        b = bld.get(key) or {}
        gs = sorted(by.get(key, []), key=lambda g: g['date'])
        w = sum(g['res'] == 'W' for g in gs)
        seasons = collections.OrderedDict()
        for g in gs:
            s = seasons.setdefault(g['y'], [0, 0])
            s[0 if g['res'] == 'W' else 1] += 1
        # longest winning streak at the building (games in date order)
        best, cur, start, bs = 0, 0, None, None
        for g in gs:
            if g['res'] == 'W':
                cur += 1
                start = start or g
                if cur > best:
                    best, bs = cur, (start, g)
            else:
                cur, start = 0, None
        card = lambda g: {'gid': g['id'], 'date': g['date'][:10], 'opp': g['opp']['name'], 'logo': g['opp'].get('logo'), 'res': g['res'], 'pts': g['pts'],
                          'opp_pts': g['opp_pts'], 'ot': g.get('ot'), 'att': g.get('att'), 'ha': g['ha'], 'round': g.get('round'), 'name': g.get('era_name')}
        crowds = sorted((g for g in gs if g.get('att')), key=lambda g: -g['att'])[:5]
        wins = sorted((g for g in gs if g['res'] == 'W'), key=lambda g: -(g['pts'] - g['opp_pts']))[:3]
        off = (R.get('buildings') or {}).get(key)
        if key not in FULL and key != 'bridgeport_arena' and best and bs and bs[0] is gs[0]:
            best, bs = 0, None   # the streak may have started before 1986-87, where we can't see the building
        row = {'key': key, 'short': SHORT.get(key) or (b.get('names') or [{}])[-1].get('name'), 'blurb': BLURB.get(key), 'full': key in FULL or key == 'bridgeport_arena', 'current': key in ('gampel', 'hartford_arena'),
               'building': b.get('building'), 'city': b.get('city'), 'opened': b.get('opened'), 'closed': b.get('closed'), 'demolished': b.get('demolished'),
               'names': [{'name': n['name'], 'from': n.get('from'), 'to': n.get('to')} for n in b.get('names') or []],
               'notes': b.get('notes'), 'sources': b.get('sources') or [],
               'official': off and {'lines': off['lines'], 'streaks': (R.get('streaks') or {}).get(key) or []},
               'since': gs and {'from': gs[0]['y'], 'g': len(gs), 'w': w, 'l': len(gs) - w,
                                'home': [sum(1 for g in gs if g['ha'] == 'H' and g['res'] == 'W'), sum(1 for g in gs if g['ha'] == 'H' and g['res'] == 'L')],
                                'seasons': [{'y': y, 'w': a, 'l': c} for y, (a, c) in seasons.items()],
                                'streak': best and {'n': best, 'from': card(bs[0]), 'to': card(bs[1])},
                                'first': card(gs[0]), 'last': card(gs[-1]), 'crowds': [card(g) for g in crowds], 'bigWins': [card(g) for g in wins]},
               'moments': [{'slug': m['slug'], 'title': m['title'], 'date': m['date']} for gid, m in moments.items() if any(g['id'] == gid for g in gs)]}
        # where both cover the same games, our count must match UConn's
        if off and gs and key in ('gampel', 'bridgeport_arena'):
            o = off['lines'][0]
            if (o['w'], o['l']) != (w, len(gs) - w):
                print(f"  !! {key}: record book {o['w']}-{o['l']} vs Storrs Lore {w}-{len(gs) - w}")
        out.append(row)
    json.dump({'buildings': out, 'homeStreaks': (R.get('streaks') or {}).get('home') or [], 'source': R.get('source')},
              open(os.path.join(SITE, 'venues.json'), 'w'), separators=(',', ':'))
    print('venues: ' + ', '.join(f"{r['key']} {r['since']['w']}-{r['since']['l']}" if r['since'] else r['key'] for r in out))


if __name__ == '__main__':
    main()
