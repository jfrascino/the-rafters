#!/usr/bin/env python3
"""The early years (1900-01 to 1976-77) -> site/data/history.json, from out/official/history.json (official_history.py).

Each season keeps the record book's own numbers (record, home/away/neutral, points) and its game list exactly as printed.
Where the book disagrees with itself (season points vs the game scores, a score printed two ways) the page says so."""
import json, os, re
LAST = 1977

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


def proper(name):
    """'BIALOSUKNIA, WESLEY' -> 'Wesley Bialosuknia'; keeps the record book's own mixed case (McKAY -> McKay)"""
    last, _, first = name.partition(',')
    def word(w):
        if re.search(r'[a-z]', w):   # 'McKAY' / 'DePRIEST': keep the printed prefix, lower the rest
            m = re.match(r'^([A-Z][a-z]+)([A-Z]+)$', w)
            return m.group(1) + m.group(2).capitalize() if m else w
        return '-'.join("'".join(x.capitalize() for x in part.split("'")) for part in w.split('-'))
    fix = lambda s: ' '.join(word(w) for w in s.replace('’', "'").split())
    return f"{fix(first.strip())} {fix(last.strip())}".strip()


def check_line(r):
    """points must equal 2 x FG + FT (no 3-point line before 1986-87). When the printed points disagree, the version that the
    per-game average backs wins (two of three agree); if nothing agrees, the printed number stays and is flagged."""
    fg, ft, pts, g, ppg = r.get('fg'), r.get('ft'), r.get('pts'), r.get('g'), r.get('ppg')
    if None in (fg, ft, pts) or 2 * fg + ft == pts:
        return
    calc = 2 * fg + ft
    fits = lambda v: bool(g) and ppg is not None and abs(v / g - ppg) <= 0.06
    if fits(calc) and not fits(pts):
        r['note'] = f"The record book prints {pts} points; his {fg} field goals and {ft} free throws make {calc}, which matches its {ppg} per game, so {calc} is shown."
        r['pts'] = calc
    elif fits(pts):
        r['note'] = f"The record book's {fg} field goals and {ft} free throws make {calc} points, not the {pts} it prints; {pts} matches its {ppg} per game, so the field goal or free throw count is likely the misprint."
    else:
        r['note'] = f"The record book's line doesn't add up: {fg} field goals and {ft} free throws make {calc}, it prints {pts} points, and {ppg} per game over {g} games is about {round(ppg * g)}. Shown as printed."


def rosters(H):
    """letterwinners per early season: stat lines from the Letterwinner History (1946-47 on), names only before that"""
    L = json.load(open(os.path.join(OFF, 'letterwinners.json')))['players'].get('rb2027') or []
    by = {}
    for p in L:
        for s in p['seasons']:
            if s['y'] <= LAST and not s.get('bad'):
                row = {'name': proper(p['name']), **{k: s.get(k) for k in ('g', 'fg', 'fga', 'ft', 'fta', 'trb', 'pts', 'ppg', 'rpg')}}
                check_line(row)
                by.setdefault(s['y'], []).append(row)
    for p in H.get('namesOnly') or []:
        for y in p['seasons']:
            if y <= LAST:
                by.setdefault(y, []).append({'name': proper(p['name']), **({'mgr': True} if p['mgr'] else {})})
    return by


def main():
    H = json.load(open(os.path.join(OFF, 'history.json')))
    R = rosters(H)
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
                        'post': s.get('post'), 'titles': titles, 'games': games, 'notes': notes_for(s) if not s.get('none') else [],
                        'roster': sorted(R.get(s['y'], []), key=lambda r: (bool(r.get('mgr')), -(r.get('pts') or -1), r['name']))})
    heads = [h for h in A.get('head_coaches') or [] if (h.get('to') or 9999) <= 1977 or (h.get('from') or 0) <= 1977]
    out = {'source': "UConn 2026-27 Record Book: year-by-year summary (pp. 3-4), season-by-season results (pp. 5-21), results by opponent (pp. 27-39)",
           'seasons': seasons, 'coaches': heads}
    json.dump(out, open(os.path.join(SITE, 'history.json'), 'w'), separators=(',', ':'))
    print(f"history: {len(seasons)} early seasons, {sum(len(s['games']) for s in seasons)} games, "
          f"{sum(1 for s in seasons if s['notes'])} with a note where the record book disagrees with itself")


if __name__ == '__main__':
    main()
