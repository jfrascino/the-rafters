"""Check every player-season against UConn's official numbers and settle each stat by a fixed rule.

Official sources (parsed by official_letterwinners.py and official_cume.py):
  cume  season-final stat sheets, 2000-01 to 2025-26 (some years missing): every player, incl. GS, OREB/DREB, PF
  rb    2026-27 Record Book "Letterwinner History": every letterwinner, 1977-78 to 2022-23
  mg    2009-10 and 2008-09 media guides' Letterwinner History (older printings, used only as a tie-break note)

The rule, per stat:
  1. An official value that contradicts its own line (points vs FG/3P/FT, a percentage vs makes/attempts, a total vs its
     per-game average, a career line vs its seasons) or is impossible (minutes per game over 40, attempts with no minutes)
     is a misprint and is set aside.
  2. Both official sources agree -> that value.
  3. They disagree -> keep Sports-Reference's value if it matches either one; otherwise the season-final sheet.
  4. One official source -> it wins (fills a stat Sports-Reference lacks, or corrects it).
  5. pipeline/official_rulings.json can pin a decision by hand, with the reason.
"""
import collections, difflib, json, os, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
OFF = os.path.join(HERE, 'out', 'official')
FIELDS = ['g', 'gs', 'mp', 'fg', 'fga', 'fg3', 'fg3a', 'ft', 'fta', 'orb', 'drb', 'trb', 'pf', 'ast', 'tov', 'blk', 'stl', 'pts']
LABEL = {'g': 'games', 'gs': 'starts', 'mp': 'minutes', 'fg': 'FG made', 'fga': 'FG attempts', 'fg3': '3-pointers', 'fg3a': '3-point attempts', 'ft': 'FT made',
         'fta': 'FT attempts', 'orb': 'offensive rebounds', 'drb': 'defensive rebounds', 'trb': 'rebounds', 'pf': 'fouls', 'ast': 'assists', 'tov': 'turnovers',
         'blk': 'blocks', 'stl': 'steals', 'pts': 'points'}
NICK = {'jim': 'james', 'jimmy': 'james', 'bob': 'robert', 'bobby': 'robert', 'rob': 'robert', 'bill': 'william', 'billy': 'william', 'will': 'william',
        'mike': 'michael', 'tom': 'thomas', 'tony': 'anthony', 'dan': 'daniel', 'danny': 'daniel', 'chris': 'christopher', 'joe': 'joseph',
        'dave': 'david', 'steve': 'steven', 'ed': 'edward', 'eddie': 'edward', 'chuck': 'charles', 'charlie': 'charles', 'nick': 'nicholas',
        'matt': 'matthew', 'andy': 'andrew', 'pat': 'patrick', 'rick': 'richard', 'rich': 'richard', 'ricky': 'richard', 'ted': 'theodore',
        'jeff': 'jeffrey', 'greg': 'gregory', 'ken': 'kenneth', 'tim': 'timothy', 'sam': 'samuel', 'ben': 'benjamin', 'nate': 'nathan',
        'zach': 'zachary', 'alex': 'alexander', 'corny': 'cornelius', 'cliff': 'clifford', 'doug': 'douglas', 'gerry': 'gerald', 'jerry': 'gerald',
        'larry': 'lawrence', 'phil': 'phillip', 'johnny': 'john', 'johnnie': 'john', 'al': 'albert', 'donny': 'donald'}


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?', '', s)
    return re.sub(r'[^a-z ]', '', s).strip()


def split_official(name):
    last, _, first = name.partition(',')
    return norm(last).replace(' ', ''), norm(first).split()


def split_ours(name):
    parts = norm(name).split()
    return (parts[-1] if parts else ''), parts[:-1]


def first_ok(a, b):
    if not a or not b:
        return True
    x, y = a[0], b[0]
    return x == y or NICK.get(x, x) == NICK.get(y, y) or x[0] == y[0] or x in b or y in a


def match(off_name, roster, num=None):
    last, first = split_official(off_name)
    cands = [r for r in roster if split_ours(r['name'])[0] == last or norm(r['name']).replace(' ', '').endswith(last)]
    if len(cands) > 1:
        cands = [r for r in cands if first_ok(first, split_ours(r['name'])[1])] or cands
    if len(cands) > 1:   # two players with the same last name: the first name has to agree properly
        exact = [r for r in cands if first and split_ours(r['name'])[1] and (split_ours(r['name'])[1][0] == first[0] or NICK.get(split_ours(r['name'])[1][0]) == first[0] or NICK.get(first[0]) == split_ours(r['name'])[1][0])]
        cands = exact or cands
    if len(cands) > 1 and num:
        cands = [r for r in cands if str(r.get('num') or '').lstrip('0') == str(num).lstrip('0')] or cands
    if len(cands) == 1:
        return cands[0]
    full = ''.join(first) + last
    best = max(roster, key=lambda r: difflib.SequenceMatcher(None, full, norm(r['name']).replace(' ', '')).ratio(), default=None)
    if best is not None and difflib.SequenceMatcher(None, full, norm(best['name']).replace(' ', '')).ratio() >= 0.8:
        return best
    return None


def misprints(s):
    """fields of a record-book season line that contradict the rest of the line"""
    bad = set()
    g, pts, fg, fg3, ft, trb, mp = (s.get(k) for k in ('g', 'pts', 'fg', 'fg3', 'ft', 'trb', 'mp'))
    if None not in (pts, fg, ft) and 2 * fg + (fg3 or 0) + ft != pts:
        # find the one field that would fix the sum, if any (ppg tells which side is right)
        if g and s.get('ppg') is not None and abs(pts / g - s['ppg']) <= 0.06:
            bad |= {'fg', 'fg3', 'ft'}
        else:
            bad |= {'pts', 'fg', 'fg3', 'ft'}
    if g and trb is not None and s.get('rpg') is not None and abs(trb / g - s['rpg']) > 0.06:
        bad |= {'trb', 'g'} if pts is None or s.get('ppg') is None or abs(pts / g - s['ppg']) > 0.06 else {'trb'}
    if g and pts is not None and s.get('ppg') is not None and abs(pts / g - s['ppg']) > 0.06:
        bad |= {'pts', 'g'} if trb is None or s.get('rpg') is None or abs(trb / g - s['rpg']) > 0.06 else {'pts'}
    for a, b, pct in (('fg', 'fga', 'fg_pct'), ('ft', 'fta', 'ft_pct'), ('fg3', 'fg3a', 'fg3_pct')):
        if s.get(b) and s.get(a) is not None and s.get(pct) is not None and abs(100 * s[a] / s[b] - s[pct]) > 0.06:
            bad |= {a, b}
        if s.get(pct) is not None and s[pct] > 100:
            bad.add(pct)
    if mp is not None and g:
        if mp / g > 40 or (mp < g and (s.get('fga') or 0) + (s.get('fta') or 0) > 2 * max(mp, 1)):
            bad.add('mp')
        if mp / g < 1.2 and (s.get('pts') or 0) > 3 * mp:
            bad.add('mp')
    if s.get('fta') is not None and mp is not None and s['fta'] > 2 * max(mp, 1) + 2:
        bad.add('fta')
    if mp is not None and mp >= 10 and pts is not None and pts / mp > 1.3:
        bad.add('mp')   # e.g. "36" minutes for a 93-point season
    for pair in PAIRS:
        if bad & set(pair):
            bad |= set(pair)
    return bad


PAIRS = (('fg', 'fga'), ('fg3', 'fg3a'), ('ft', 'fta'))


class Official:
    def __init__(self):
        self.cume = {int(k): v for k, v in (json.load(open(os.path.join(OFF, 'cume.json'))) if os.path.exists(os.path.join(OFF, 'cume.json')) else {}).items()}
        lw = json.load(open(os.path.join(OFF, 'letterwinners.json')))['players'] if os.path.exists(os.path.join(OFF, 'letterwinners.json')) else {}
        rp = os.path.join(HERE, 'official_rulings.json')
        self.rulings = {(r['pid'], r['y'], r['field']): r for r in (json.load(open(rp)).get('rulings') if os.path.exists(rp) else [])}
        self.rb = collections.defaultdict(list)
        for p in lw.get('rb2027', []):
            good = [s for s in p['seasons'] if not s.get('bad')]
            tot = p.get('totals') or {}
            tot_bad = set()
            if tot and not tot.get('bad'):
                for k in ('g', 'fg', 'fga', 'fg3', 'fg3a', 'ft', 'fta', 'trb', 'ast', 'tov', 'blk', 'stl', 'mp', 'pts'):
                    vals = [s.get(k) for s in good]
                    if tot.get(k) is not None and vals and all(isinstance(v, int) for v in vals) and sum(vals) != tot[k]:
                        tot_bad.add(k)
            for s in good:
                unreadable = {k for k, v in s.items() if isinstance(v, str) and v.startswith('BAD:')}
                s = {k: (None if k in unreadable else v) for k, v in s.items()}
                bad = misprints(s) | unreadable
                # a career-total mismatch points at a misprint in one of his seasons: distrust that stat wherever the line
                # disagrees with Sports-Reference (decided later), but say which totals failed
                self.rb[s['y']].append({**s, 'name': p['name'], 'misprint': sorted(bad), 'career_mismatch': sorted(tot_bad)})
        self.mg = collections.defaultdict(dict)
        for key in ('mg2010', 'mg2009'):
            for p in lw.get(key, []):
                last, first = split_official(p['name'])
                for s in p['seasons']:
                    if not s.get('bad'):
                        self.mg[(s['y'], last, (first or [''])[0][:1])].setdefault(key, s)
        self.report = {'changed': [], 'filled': [], 'kept': [], 'agree_fields': 0, 'checked_fields': 0, 'player_seasons': 0, 'unmatched_official': [], 'no_official_line': []}

    def covered(self, y):
        return bool(self.cume.get(y)) or bool(self.rb.get(y))

    def apply(self, y, roster, box=None):
        """settle every stat of every player in one season's roster (mutates tot/pg in place).
        box: per-player sums of this season's box scores, when every game has one (an independent tie-breaker)"""
        lines = collections.defaultdict(dict)
        for src, recs in (('cume', (self.cume.get(y) or {}).get('players') or []), ('rb', self.rb.get(y) or [])):
            for rec in recs:
                r = match(rec['name'], roster, rec.get('num'))
                if r is None:
                    if (rec.get('g') or 0) > 0:
                        self.report['unmatched_official'].append({'y': y, 'src': src, 'name': rec['name'], 'g': rec.get('g'), 'pts': rec.get('pts')})
                    continue
                lines[r['pid']][src] = rec
        for item in roster:
            L = lines.get(item['pid'])
            if not L:
                if self.covered(y):
                    self.report['no_official_line'].append({'y': y, 'pid': item['pid'], 'name': item['name'], 'g': (item.get('tot') or item.get('pg') or {}).get('g')})
                continue
            self.report['player_seasons'] += 1
            tot = item.setdefault('tot', {})
            pg = item.setdefault('pg', {})
            ours = {**tot, 'gs': pg.get('gs')}
            c, b = L.get('cume') or {}, L.get('rb') or {}
            bx = (box or {}).get(item['pid'])
            last, first = split_official((b or c)['name'])
            old = self.mg.get((y, last, (first or [''])[0][:1]), {})
            changed, notes = {}, {}
            for f in FIELDS:
                o = ours.get(f)
                cv = c.get(f)
                bv = b.get(f)
                xv = bx.get(f) if bx and f != 'mp' else None   # box minutes are rounded game by game: too coarse to referee exactly
                if bx and f == 'mp' and o is not None and bx.get('mp') and abs(bx['mp'] - o) <= max(3, 0.02 * o):
                    xv_mp = bx['mp']   # but they do show when an official minutes total is far off
                else:
                    xv_mp = None
                if y < 1987 and f in ('fg3', 'fg3a'):
                    continue   # no 3-point line yet
                if cv is None and bv is None:
                    continue
                b_bad = bv is not None and (f in (b.get('misprint') or []) or (f in (b.get('career_mismatch') or []) and cv is not None and cv != bv))
                note = {'y': y, 'pid': item['pid'], 'name': item['name'], 'stat': f, 'ours': o, 'season_sheet': cv, 'record_book': bv,
                        **({'box_scores': xv} if xv is not None else {}), **({'old_guides': {k: v.get(f) for k, v in old.items()}} if old else {})}
                self.report['checked_fields'] += 1
                rule = self.rulings.get((item['pid'], y, f))
                if rule:
                    v = rule.get('value', o)
                    if v != o:
                        changed[f] = v
                        notes[f] = {**note, 'now': v, 'why': rule['why'], 'kind': 'changed'}
                    else:
                        self.report['kept'].append({**note, 'why': rule['why']})
                    continue
                good = [v for v, bad in ((cv, False), (bv, b_bad)) if v is not None and not bad]
                if f == 'mp' and o is not None and good and not (len(good) == 2 and good[0] == good[1] != o) \
                        and all(abs(v - o) <= max(5, 0.005 * o) for v in good):
                    self.report['agree_fields'] += 1   # minutes within rounding (the two official sources rarely agree to the minute)
                    continue
                if not good:
                    if o == cv or o == bv:
                        self.report['agree_fields'] += 1
                    else:
                        self.report['kept'].append({**note, 'why': f"the record book's {bv} contradicts the rest of its own line (misprint)"})
                    continue
                if len(good) == 2 and good[0] != good[1]:
                    if o in good:
                        self.report['kept'].append({**note, 'why': 'the official sources disagree; Sports-Reference matches one of them'})
                        continue
                    v = xv if xv in good else cv
                    why = 'the official sources disagree; ' + ('the box scores side with this one' if xv in good else 'using the season-final stat sheet')
                elif len(good) == 2:
                    v, why = good[0], 'season-final stat sheet and record book agree'
                else:
                    v = good[0]
                    src = 'season-final stat sheet' if v == cv else 'record book'
                    if v != o and o is not None:
                        if f == 'mp' and xv_mp is not None and abs(v - xv_mp) > max(10, 0.1 * xv_mp):
                            self.report['kept'].append({**note, 'box_scores': xv_mp, 'why': f'the {src} says {v} minutes, but the box scores add up to about {xv_mp}'})
                            continue
                        if xv is not None and xv == o:
                            self.report['kept'].append({**note, 'why': f'the {src} says {v}, but the box scores add up to {o}'})
                            continue
                        if abs(v - o) >= 10 and (v * 3 <= o or v >= 3 * o):
                            self.report['kept'].append({**note, 'why': f"the {src}'s {v} is implausible next to the rest of his line (likely misprint); needs a second source"})
                            continue
                    why = src + (' (only official source)' if (cv is None or bv is None) else '')
                    if bv is not None and b_bad and v == cv:
                        why = f"season-final stat sheet (the record book's {bv} is a misprint)"
                    if xv is not None and xv == v:
                        why += '; the box scores agree'
                if v == o:
                    self.report['agree_fields'] += 1
                    continue
                changed[f] = v
                notes[f] = {**note, 'now': v, 'why': why, 'kind': 'filled' if o is None else 'changed'}
            # paired stats must stay coherent: undo a change that leaves makes > attempts or OREB + DREB != REB
            final = {**ours, **changed}
            for a_, b_ in PAIRS:
                if None not in (final.get(a_), final.get(b_)) and final[a_] > final[b_]:
                    for k in (a_, b_):
                        if k in changed:
                            self.report['kept'].append({**notes.pop(k), 'why': f'would leave {a_} > {b_}; keeping the pair as Sports-Reference has it'})
                            changed.pop(k)
            final = {**ours, **changed}
            if None not in (final.get('orb'), final.get('drb'), final.get('trb')) and final['orb'] + final['drb'] != final['trb']:
                for k in ('orb', 'drb'):
                    if k in changed:
                        self.report['kept'].append({**notes.pop(k), 'why': 'would break OREB + DREB = REB with the settled rebound total'})
                        changed.pop(k)
            final = {**ours, **changed}
            if None not in (final.get('pts'), final.get('fg'), final.get('ft')) and 2 * final['fg'] + (final.get('fg3') or 0) + final['ft'] != final['pts']:
                undo = [k for k in ('pts', 'fg', 'fg3', 'ft', 'fga', 'fg3a', 'fta') if k in changed]
                for k in undo:
                    self.report['kept'].append({**notes.pop(k), 'why': 'would break points = 2 x FG + 3P + FT; keeping the shooting line together'})
                    changed.pop(k)
            for f, n in notes.items():
                self.report[n.pop('kind')].append(n)
            if changed:
                for f, v in changed.items():
                    if f == 'gs':
                        pg['gs'] = v
                    else:
                        tot[f] = v
                recompute(item)
            item['verified'] = sorted({'season_sheet' if c else None, 'record_book' if b else None} - {None})

    def summary(self):
        R = self.report
        return (f"official check: {R['player_seasons']} player-seasons, {R['checked_fields']} stats compared, {R['agree_fields']} already right, "
                f"{len(R['changed'])} corrected, {len(R['filled'])} filled in, {len(R['kept'])} kept (official misprint or split sources), "
                f"{len(R['unmatched_official'])} official lines unmatched, {len(R['no_official_line'])} site players without an official line")


def recompute(item):
    """per-game numbers and percentages from the (corrected) season totals"""
    t, pg = item.get('tot') or {}, item.setdefault('pg', {})
    g = t.get('g') or pg.get('g')
    if not g:
        return
    pg['g'] = g
    for k, pk in (('mp', 'mp'), ('pts', 'pts'), ('trb', 'trb'), ('ast', 'ast'), ('stl', 'stl'), ('blk', 'blk'), ('tov', 'tov'), ('orb', 'orb'), ('pf', 'pf')):
        if t.get(k) is not None:
            pg[pk] = round(t[k] / g, 1)
    for a, b, pk in (('fg', 'fga', 'fg_pct'), ('fg3', 'fg3a', 'fg3_pct'), ('ft', 'fta', 'ft_pct')):
        if t.get(b):
            pg[pk] = round(t[a] / t[b], 3)
