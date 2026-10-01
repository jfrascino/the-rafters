#!/usr/bin/env python3
"""Three-way check of every player-season on the site against UConn's official numbers.

  ours  = site/data/seasons/{y}.json roster (what the site shows; Sports-Reference based)
  cume  = pipeline/out/official/cume.json        official season-final stat sheets (2001-2026, not every year)
  rb    = pipeline/out/official/letterwinners.json  record book Letterwinner History (1978-2023, letterwinners only)

Writes dev/stats_validation.json and prints a summary.  Run after a build.
"""
import difflib, json, os, re, sys, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site', 'data')
OFF = os.path.join(ROOT, 'pipeline', 'out', 'official')
FIELDS = ['g', 'gs', 'mp', 'fg', 'fga', 'fg3', 'fg3a', 'ft', 'fta', 'orb', 'drb', 'trb', 'pf', 'ast', 'tov', 'blk', 'stl', 'pts']
NICK = {'jim': 'james', 'jimmy': 'james', 'bob': 'robert', 'bobby': 'robert', 'rob': 'robert', 'bill': 'william', 'billy': 'william', 'will': 'william',
        'mike': 'michael', 'tom': 'thomas', 'tony': 'anthony', 'dan': 'daniel', 'danny': 'daniel', 'chris': 'christopher', 'joe': 'joseph',
        'dave': 'david', 'steve': 'steven', 'ed': 'edward', 'eddie': 'edward', 'chuck': 'charles', 'charlie': 'charles', 'nick': 'nicholas',
        'matt': 'matthew', 'andy': 'andrew', 'pat': 'patrick', 'ray': 'walter', 'rick': 'richard', 'rich': 'richard', 'ricky': 'richard',
        'ted': 'theodore', 'jeff': 'jeffrey', 'greg': 'gregory', 'ken': 'kenneth', 'tim': 'timothy', 'sam': 'samuel', 'ben': 'benjamin',
        'nate': 'nathan', 'zach': 'zachary', 'alex': 'alexander', 'corny': 'cornelius', 'cliff': 'clifford', 'doug': 'douglas',
        'kev': 'kevin', 'gerry': 'gerald', 'jerry': 'gerald', 'larry': 'lawrence', 'phil': 'phillip', 'johnny': 'john', 'johnnie': 'john'}


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
    """do two first-name token lists plausibly name the same person?"""
    if not a or not b:
        return True
    x, y = a[0], b[0]
    x2, y2 = NICK.get(x, x), NICK.get(y, y)
    return x == y or x2 == y2 or x[0] == y[0] or x in b or y in a


def match(off_name, roster, num=None):
    last, first = split_official(off_name)
    cands = [r for r in roster if split_ours(r['name'])[0].replace(' ', '') == last or norm(r['name']).replace(' ', '').endswith(last)]
    if len(cands) > 1:
        c2 = [r for r in cands if first_ok(first, split_ours(r['name'])[1])]
        cands = c2 or cands
    if len(cands) > 1 and num:
        c3 = [r for r in cands if str(r.get('num') or '').lstrip('0') == str(num).lstrip('0')]
        cands = c3 or cands
    if len(cands) == 1:
        return cands[0], 'name'
    # fuzzy: full-name similarity
    full = ' '.join(first + [last])
    best = max(roster, key=lambda r: difflib.SequenceMatcher(None, full, norm(r['name']).replace(' ', '')).ratio(), default=None)
    if best is not None and difflib.SequenceMatcher(None, ' '.join(first) + last, norm(best['name']).replace(' ', '')).ratio() >= 0.8:
        return best, 'fuzzy'
    return None, None


def rb_consistency(s, totals_ok):
    bad = []
    g, pts, fg, fg3, ft, trb = (s.get(k) for k in ('g', 'pts', 'fg', 'fg3', 'ft', 'trb'))
    if None not in (pts, fg, ft) and 2 * fg + (fg3 or 0) + ft != pts:
        bad.append('pts != 2*FG + 3P + FT')
    if g and trb is not None and s.get('rpg') is not None and abs(trb / g - s['rpg']) > 0.06:
        bad.append(f'REB {trb} vs {s["rpg"]}/game')
    if g and pts is not None and s.get('ppg') is not None and abs(pts / g - s['ppg']) > 0.06:
        bad.append(f'PTS {pts} vs {s["ppg"]}/game')
    for a, b, pct in (('fg', 'fga', 'fg_pct'), ('ft', 'fta', 'ft_pct'), ('fg3', 'fg3a', 'fg3_pct')):
        if s.get(b) and s.get(a) is not None and s.get(pct) is not None and abs(100 * s[a] / s[b] - s[pct]) > 0.06:
            bad.append(f'{a}/{b} vs {pct}')
    return bad


def main():
    core = json.load(open(os.path.join(SITE, 'core.json')))
    cume = {int(k): v for k, v in json.load(open(os.path.join(OFF, 'cume.json'))).items()}
    lw = json.load(open(os.path.join(OFF, 'letterwinners.json')))['players']
    # record book lines by season, with a check of each player's season sum against his TOTALS line
    rb = collections.defaultdict(list)
    for p in lw.get('rb2027', []):
        good = [s for s in p['seasons'] if not s.get('bad')]
        tot = p.get('totals') or {}
        tot_bad = {}
        if tot and not tot.get('bad'):
            for k in ('g', 'fg', 'fga', 'fg3', 'fg3a', 'ft', 'fta', 'trb', 'ast', 'tov', 'blk', 'stl', 'mp', 'pts'):
                vals = [s.get(k) for s in good]
                if tot.get(k) is not None and all(isinstance(v, int) for v in vals) and sum(vals) != tot[k]:
                    tot_bad[k] = (sum(vals), tot[k])
        for s in good:
            rb[s['y']].append({**s, 'name': p['name'], 'totals_mismatch': tot_bad or None})
    mg = collections.defaultdict(dict)   # older guides, for tie-breaks
    for key in ('mg2010', 'mg2009'):
        for p in lw.get(key, []):
            for s in p['seasons']:
                if not s.get('bad'):
                    mg[(s['y'], split_official(p['name'])[0])].setdefault(key, s)

    report = {'seasons': {}, 'diffs': [], 'missing_from_site': [], 'not_in_official': []}
    totals = collections.Counter()
    for s in core['seasons']:
        y = s['y']
        if s.get('future'):
            continue
        sd = json.load(open(os.path.join(SITE, 'seasons', f'{y}.json')))
        roster = [r for r in sd.get('roster') or [] if r.get('tot') or r.get('pg')]
        seen = set()
        lines = collections.defaultdict(dict)   # pid -> {'cume': rec, 'rb': rec}
        for src, recs in (('cume', (cume.get(y) or {}).get('players') or []), ('rb', rb.get(y) or [])):
            for rec in recs:
                r, how = match(rec['name'], roster, rec.get('num'))
                if not r:
                    report['missing_from_site'].append({'y': y, 'src': src, 'name': rec['name'], 'g': rec.get('g'), 'pts': rec.get('pts')})
                    continue
                lines[r['pid']][src] = {**rec, 'how': how}
        n_eq = n_diff = 0
        for r in roster:
            L = lines.get(r['pid'])
            if not L:
                report['not_in_official'].append({'y': y, 'pid': r['pid'], 'name': r['name'], 'g': (r.get('tot') or {}).get('g') or (r.get('pg') or {}).get('g'),
                                                  'covered': bool(cume.get(y)) or bool(rb.get(y))})
                continue
            ours = dict(r.get('tot') or {})
            ours['gs'] = (r.get('pg') or {}).get('gs')
            row_diff = False
            for f in FIELDS:
                o = ours.get(f)
                c = (L.get('cume') or {}).get(f)
                b = (L.get('rb') or {}).get(f)
                offs = [v for v in (c, b) if v is not None]
                if not offs:
                    continue
                totals['fields'] += 1
                if all(v == o for v in offs):
                    totals['agree'] += 1
                    continue
                row_diff = True
                last = split_official((L.get('rb') or L.get('cume'))['name'])[0]
                g_old = {k: (v.get(f) if isinstance(v, dict) else None) for k, v in mg.get((y, last), {}).items()}
                report['diffs'].append({'y': y, 'pid': r['pid'], 'name': r['name'], 'field': f, 'ours': o, 'cume': c, 'rb': b, **({'mg': g_old} if any(v is not None for v in g_old.values()) else {}),
                                        'rb_flags': rb_consistency(L['rb'], True) if L.get('rb') else None,
                                        'rb_totals_mismatch': (L.get('rb') or {}).get('totals_mismatch')})
                totals['differ'] += 1
            n_diff += row_diff
            n_eq += not row_diff
        report['seasons'][y] = {'roster': len(roster), 'checked': n_eq + n_diff, 'all_equal': n_eq, 'with_diffs': n_diff,
                                'sources': [k for k, v in (('cume', cume.get(y)), ('rb', rb.get(y))) if v]}
    json.dump(report, open(os.path.join(ROOT, 'dev', 'stats_validation.json'), 'w'), indent=1)
    print(f"fields compared: {totals['fields']}  agree: {totals['agree']}  differ: {totals['differ']}")
    print(f"player-seasons checked: {sum(v['checked'] for v in report['seasons'].values())} of {sum(v['roster'] for v in report['seasons'].values())}")
    print(f"official lines with no site match: {len(report['missing_from_site'])}   site players with no official line: {len(report['not_in_official'])}")
    by_field = collections.Counter(d['field'] for d in report['diffs'])
    print('diffs by field:', dict(by_field.most_common()))


if __name__ == '__main__':
    main()
