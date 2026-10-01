#!/usr/bin/env python3
"""The early years (1900-01 to 1976-77) -> site/data/history.json, from out/official/history.json (official_history.py).

Each season keeps the record book's own numbers (record, home/away/neutral, points) and its game list exactly as printed.
Where the book disagrees with itself (season points vs the game scores, a score printed two ways) the page says so."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, '..', 'site', 'data')
OFF = os.path.join(HERE, 'out', 'official')


def notes_for(s):
    out = []
    games = s['games']
    pf, pa = sum(g['pts'] for g in games), sum(g['opp_pts'] for g in games)
    if games and s.get('pts') is not None and (pf, pa) != (s['pts'], s['opp']):
        parts = []
        if pf != s['pts']:
            parts.append(f"{s['pts']:,} points scored")
        if pa != s['opp']:
            parts.append(f"{s['opp']:,} allowed")
        out.append(f"The record book's season summary lists {' and '.join(parts)}; its game-by-game scores add up to {pf:,}–{pa:,}. "
                   'Both are shown as printed.')
    for g in games:
        if g.get('series') == 'differs':
            out.append(f"{g['opp']}: the season list prints {g['res']} {g['pts']}–{g['opp_pts']}, the book's results-by-opponent pages "
                       f"{' / '.join(x.replace('-', '–') for x in g['seriesSays'])}. The season list matches the season totals, so it is used here.")
    return out


# the record book spells a name two ways; settled from outside sources
COACH_FIX = {'M.R. Schwartz': ('M.R. Swartz', "The record book's year-by-year table spells him Schwartz; its list of head coaches has Swartz, "
                                              'and he was Milford Ross "Carty" Swartz (en.wikipedia.org/wiki/Ross_Swartz).')}


def main():
    H = json.load(open(os.path.join(OFF, 'history.json')))
    A = json.load(open(os.path.join(OFF, 'assistants.json')))
    seasons = []
    CODE = {'H': 'H', 'A': 'A', 'N': 'N', 'GP': 'H', 'HCC': 'H', 'XL': 'H', 'FH': 'H', 'NHC': 'H', 'NH': 'H'}
    for s in H['seasons']:
        # the season lists only mark away ("at") and neutral ("vs.") games from 1949-50 on; before that a game's site is unknown
        # unless the results-by-opponent pages give it a code
        marked = any(g['site'] in ('A', 'N') for g in s['games'])
        site = lambda g: g['site'] if marked else CODE.get(g.get('code'))
        games = [{'date': g.get('iso'), 'opp': g['opp'], 'site': site(g), 'res': g['res'], 'pts': g['pts'], 'opp_pts': g['opp_pts'],
                  **({'ot': g['ot']} if g.get('ot') else {}), **({'event': g['event']} if g.get('event') else {})} for g in s['games']]
        titles = [t.replace('Yanke Conference', 'Yankee Conference') for t in s.get('titles') or []]
        coach, cnote = COACH_FIX.get(s['coach'], (s['coach'], None))
        line = s.get('coachLine')
        for bad, (good, _) in COACH_FIX.items():
            line = line.replace(bad, good) if line else line
        seasons.append({'y': s['y'], 'coach': coach, 'coachLine': line, 'none': s.get('none') or False, **({'coachNote': cnote} if cnote else {}),
                        'w': (s.get('overall') or [None, None])[0], 'l': (s.get('overall') or [None, None])[1],
                        'home': s.get('home'), 'away': s.get('away'), 'neutral': s.get('neutral'), 'pts': s.get('pts'), 'opp': s.get('opp'),
                        'post': s.get('post'), 'titles': titles, 'games': games, 'notes': notes_for(s) if not s.get('none') else []})
    heads = [h for h in A.get('head_coaches') or [] if (h.get('to') or 9999) <= 1977 or (h.get('from') or 0) <= 1977]
    out = {'source': "UConn 2026-27 Record Book: year-by-year summary (pp. 3-4), season-by-season results (pp. 5-21), results by opponent (pp. 27-39)",
           'seasons': seasons, 'coaches': heads}
    json.dump(out, open(os.path.join(SITE, 'history.json'), 'w'), separators=(',', ':'))
    print(f"history: {len(seasons)} early seasons, {sum(len(s['games']) for s in seasons)} games, "
          f"{sum(1 for s in seasons if s['notes'])} with a note where the record book disagrees with itself")


if __name__ == '__main__':
    main()
