#!/usr/bin/env python3
"""UConn men's basketball before Storrs Lore's game data (1900-01 to 1976-77), straight from the 2026-27 Record Book.

  pp. 3-4    year-by-year summary: coach, overall/conference/home/away/neutral records, points for and against, postseason
  pp. 5-21   season-by-season results: every game's opponent and score (dates and home/away/neutral from the mid-1940s)
  pp. 22-23  all-time postseason results (date and site of every NCAA/NIT game)
  pp. 27-49  results by opponent: dates and H/A/N site codes for many games the season lists leave undated

Every season is checked against itself: the games must add up to the summary's W-L and points scored/allowed.
Output: out/official/history.json (seasons + per-season games + check results)."""
import collections, json, os, re
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, 'cache.nosync', 'official', 'RECORD_BOOK_26-27_V2_.pdf')
OUT = os.path.join(HERE, 'out', 'official', 'history.json')
LAST = 1977   # Storrs Lore's game data starts with 1977-78
HDR = re.compile(r'^(2026-27 UCONN MEN.S BASKETBALL / HISTORY|NCAA NATIONAL CHAMPIONS:.*)$')
RES = re.compile(r'^([WL]),\s*(\d+)\s*-\s*(\d+)\s*(?:\(?\s*((?:\d)?\s*ot)\s*\)?)?\s*$', re.I)
GLUED = re.compile(r'^(.*?\S)\s+([WL],\s*\d+\s*-\s*\d+.*)$')   # "Rhode Island      W, 58-48" on one line
SEASON = re.compile(r'^(\d{4})-(\d{2}|\d{4})\s*(?:\((\d+)-(\d+)\))?$')
DATE = re.compile(r'^(\d{1,2})/(\d{1,2})$')
TITLE = re.compile(r'Champion|Tournament|NCAA|NIT\b|ECAC|Sweet 16|Elite Eight|Final Four|Round|Runner|Co-Champ', re.I)
FOOT = re.compile(r'^([#*+^@$%!&~]+)\s*(.*[A-Za-z].*)$')


def tokens(doc, pages, columns=False):
    """page text as tokens; columns=True reads the four-column results pages column by column, top to bottom
    (the PDF's own content order jumps between columns and mixes neighbouring seasons)"""
    out = []
    for p in pages:
        page = doc[p - 1]
        if columns:
            blocks = [b for b in page.get_text('blocks') if b[6] == 0]
            col = lambda b: min(3, int(((b[0] + b[2]) / 2) // 153))
            texts = [b[4] for b in sorted(blocks, key=lambda b: (col(b), b[1]))]
        else:
            texts = [page.get_text()]
        page_no = True
        for text in texts:
            for line in text.splitlines():
                for tok in line.split('\t'):
                    tok = tok.strip()
                    if not tok or HDR.match(tok):
                        continue
                    if page_no and tok == str(p):   # the printed page number, once per page
                        page_no = False
                        continue
                    m = GLUED.match(tok)
                    out.extend([m.group(1).strip(), m.group(2).strip()] if m and not RES.match(tok) else [tok])
    return out


def summary(doc):
    """pp. 3-4: one row per season"""
    toks = tokens(doc, [3, 4])
    i = toks.index('Season') + 1 if 'Season' in toks else 0
    rows = {}
    while i < len(toks):
        m = re.fullmatch(r'(\d{4})-(\d{2})', toks[i])
        if not m:
            i += 1
            continue
        y = int(m.group(1)) + 1
        coach = toks[i + 1]
        if toks[i + 2] == 'No Competition':
            rows[y] = {'y': y, 'coach': coach, 'none': True}
            i += 3
            continue
        # the row runs to the next season label: records (W-L or NA), then points for, points against, postseason
        j = i + 2
        while j < len(toks) and not re.fullmatch(r'\d{4}-\d{2}', toks[j]):
            j += 1
        f = toks[i + 2:j]
        wl = lambda s: tuple(int(x) for x in s.split('-')) if re.fullmatch(r'\d+-\d+', s or '') else None
        nums = [k for k, x in enumerate(f) if x.isdigit()]
        recs = f[:nums[0]] if nums else f
        recs += ['NA'] * (5 - len(recs))
        post = ' '.join(f[nums[1] + 1:]) if len(nums) >= 2 else None
        rows[y] = {'y': y, 'coach': coach, 'overall': wl(recs[0]), 'conf': wl(recs[1]), 'home': wl(recs[2]), 'away': wl(recs[3]), 'neutral': wl(recs[4]),
                   'pts': int(f[nums[0]]) if nums else None, 'opp': int(f[nums[1]]) if len(nums) > 1 else None,
                   'post': None if (post or '--').strip('- ') == '' else post, 'raw': f}
        i = j
    return rows


def seasons(doc):
    """pp. 5-21: season blocks, newest first"""
    toks = tokens(doc, range(5, 22), columns=True)
    out, cur, pend = {}, None, {}

    def close():
        if cur:
            out[cur['y']] = cur

    for t in toks:
        m = SEASON.match(t)
        if m and (len(m.group(2)) == 4 or int(m.group(1)) >= 1940):
            close()
            y = int(m.group(1)) + 1
            cur = {'y': y, 'coach': None, 'record': (int(m.group(3)), int(m.group(4))) if m.group(3) else None, 'splits': None,
                   'titles': [], 'games': [], 'notes': {}}
            pend = {}
            continue
        if cur is None:
            continue
        if t.startswith('Head Coach:'):
            cur['coach'] = t[len('Head Coach:'):].strip()
            continue
        if cur['coach'] and cur['coach'].endswith(',') and not cur['record']:
            cur['coach'] += ' ' + t
            continue
        if cur['record'] is None and re.fullmatch(r'\d+-\d+', t):
            cur['record'] = tuple(int(x) for x in t.split('-'))
            continue
        m = re.fullmatch(r'(\d+)-(\d+) home, (\d+)-(\d+) away, (\d+)-(\d+) neutral', t)
        if m:
            g = [int(x) for x in m.groups()]
            cur['splits'] = {'home': g[0:2], 'away': g[2:4], 'neutral': g[4:6]}
            continue
        m = FOOT.match(t)
        if m and not pend.get('opp') and (',' in m.group(2) or 'Tournament' in m.group(2) or 'Classic' in m.group(2)):
            cur['notes'][m.group(1)] = m.group(2).strip()
            continue
        m = DATE.match(t)
        if m:
            pend = {'date': t}
            continue
        m = RES.match(t)
        if m:
            if not pend.get('opp'):
                cur.setdefault('problems', []).append(f'result without opponent: {t}')
                continue
            ot = (m.group(4) or '').replace(' ', '').lower()
            cur['games'].append({**pend, 'res': m.group(1), 'pts': int(m.group(2)), 'opp_pts': int(m.group(3)), 'ot': (ot.upper() if ot not in ('ot', '1ot') else 'OT') if ot else None})
            pend = {}
            continue
        if not cur['games'] and not pend and TITLE.search(t):
            cur['titles'].append(t)
            continue
        # an opponent: site prefix, building code, footnote marks
        o = t
        site, bldg, mark = 'H', None, None
        if re.match(r'^at\s', o):
            site, o = 'A', o[3:]
        elif re.match(r'^vs\.?\s', o):
            site, o = 'N', re.sub(r'^vs\.?\s*', '', o)
        mb = re.search(r'\((HCC|NHC|CMC-NHC|CMC-HCC|NH|FH|WB)\)', o)
        if mb:
            bldg, o = mb.group(1), o.replace(mb.group(0), '')
        mm = re.search(r'\s*([#*+^@$%!&~]+)\s*$', o)
        if mm:
            mark, o = mm.group(1), o[:mm.start()]
        pend = {**pend, 'opp': o.strip(), 'site': site, **({'bldg': bldg} if bldg else {}), **({'mark': mark} if mark else {})}
    close()
    return out


def in_season(c, y, x):
    """does a series entry belong to spring-year season y? (two-digit years are resolved by the season)"""
    if c.get('y'):
        return c['y'] == y
    mo, yy = c['md'][0], c['yy']
    cal = y - 1 if mo >= 8 else y
    return cal % 100 == yy


def series_games(doc):
    """pp. 27-39, results by opponent: [{opp, when (date or season), y (spring year), res, pts, opp_pts, ot, site}]"""
    out, opp = [], None
    toks = []
    for p in range(27, 40):
        page = doc[p - 1]
        blocks = [b for b in page.get_text('blocks') if b[6] == 0]
        page_no = True
        for b in sorted(blocks, key=lambda b: (int((b[0] + 10) // 112), b[1])):
            for line in b[4].splitlines():
                for tok in line.split('\t'):
                    tok = tok.strip()
                    if not tok or HDR.match(tok):
                        continue
                    if page_no and tok == str(p):
                        page_no = False
                        continue
                    toks.append(tok)
    cur = None
    for t in toks:
        m = re.match(r"^(.+?) \((\d+)-(\d+)\)\s*$", t)
        if m and '/' not in t:
            opp, cur = m.group(1).strip(), None
            continue
        md = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{2})\*?', t)
        ms = re.fullmatch(r'(\d{4})-(\d{2})', t)
        if md or ms:
            cur = {'opp': opp, 'when': t.rstrip('*')}
            if ms:
                cur['y'] = int(ms.group(1)) + 1
            else:
                mo, yy = int(md.group(1)), int(md.group(3))
                cur['md'], cur['yy'] = (mo, int(md.group(2))), yy
            out.append(cur)
            continue
        if cur is None:
            continue
        if t in ('W', 'L') and 'res' not in cur:
            cur['res'] = t
            continue
        m = re.fullmatch(r'(\d+)-(\d+)\s*(?:\((\d?ot)\))?', t)
        if m and 'pts' not in cur:
            cur['pts'], cur['opp_pts'] = int(m.group(1)), int(m.group(2))
            cur['ot'] = m.group(3)
            continue
        if re.fullmatch(r'[A-Z]{1,4}(?:-[A-Z]{2,4})?', t) and 'pts' in cur and 'site' not in cur:
            cur['site'] = t
    return [g for g in out if 'pts' in g and 'res' in g]


# season-list spellings -> the results-by-opponent pages' names
ALIAS = {'worcester polytech': 'worcester polytechnic', 'worcester': 'worcester polytechnic', 'amer. international': 'american international',
         'v.m.i.': 'virginia military', 'virginia military inst.': 'virginia military', 'rensselaer polytech': 'rpi',
         'california state-fullerton': 'cal - fullerton', 'n.y. state teachers': 'albany'}


def key(name):
    n = (name or '').replace('’', "'").strip().lower()
    n = ALIAS.get(n, n)
    n = re.sub(r'\(.*?\)', '', n).replace('&', 'and')
    n = re.sub(r'^st\.?\s', 'saint ', n)
    n = re.sub(r'\sst\.?$', ' state', n)
    n = re.sub(r'\b(university|college|the)\b', '', n)
    return re.sub(r'[^a-z]', '', n)


def main():
    doc = pymupdf.open(PDF)
    S = summary(doc)
    G = seasons(doc)
    SG = series_games(doc)
    by_opp = collections.defaultdict(list)
    for g in SG:
        by_opp[key(g['opp'])].append(g)
    print(f'series pages: {len(SG)} games across {len(by_opp)} opponents')
    report, hist = [], []
    for y in sorted(S):
        if y > LAST:
            continue
        s = S[y]
        g = G.get(y) or {}
        games = g.get('games') or []
        row = {'y': y, 'coach': s['coach'], 'none': s.get('none', False), 'overall': s.get('overall'), 'conf': s.get('conf'), 'home': s.get('home'),
               'away': s.get('away'), 'neutral': s.get('neutral'), 'pts': s.get('pts'), 'opp': s.get('opp'), 'post': s.get('post'),
               'coachLine': g.get('coach'), 'titles': g.get('titles') or [], 'notes': g.get('notes') or {}, 'games': games}
        checks, used = [], set()
        for x in games:
            cands = [c for c in by_opp.get(key(x['opp']), []) if id(c) not in used and in_season(c, y, x)]
            exact = [c for c in cands if (c['res'], c['pts'], c['opp_pts']) == (x['res'], x['pts'], x['opp_pts'])]
            c = (exact or [None])[0]
            if c:
                used.add(id(c))
                x['series'] = 'match'
                if c.get('md') and not x.get('date'):
                    x['date'] = f"{c['md'][0]}/{c['md'][1]}"
                if c.get('site'):
                    x['code'] = c['site']
            elif cands:
                x['series'] = 'differs'
                x['seriesSays'] = [f"{c['res']} {c['pts']}-{c['opp_pts']}" for c in cands]
            else:
                x['series'] = 'missing'
        if not s.get('none'):
            w = sum(x['res'] == 'W' for x in games)
            l = len(games) - w
            if not games:
                checks.append('no game list')
            else:
                if s.get('overall') and (w, l) != tuple(s['overall']):
                    checks.append(f"games {w}-{l} vs summary {s['overall'][0]}-{s['overall'][1]}")
                if g.get('record') and tuple(g['record']) != (w, l):
                    checks.append(f"games {w}-{l} vs season header {g['record'][0]}-{g['record'][1]}")
                pf, pa = sum(x['pts'] for x in games), sum(x['opp_pts'] for x in games)
                if s.get('pts') is not None and (pf, pa) != (s['pts'], s['opp']):
                    checks.append(f"points {pf}-{pa} vs summary {s['pts']}-{s['opp']}")
                if g.get('splits'):
                    sp = {k: [sum(1 for x in games if x['site'] == c and x['res'] == r) for r in 'WL'] for k, c in (('home', 'H'), ('away', 'A'), ('neutral', 'N'))}
                    if any(sp[k] != g['splits'][k] for k in sp):
                        checks.append(f"site splits {sp} vs header {g['splits']}")
            for pr in g.get('problems') or []:
                checks.append(pr)
        # full dates (month >= August belongs to the fall of the season's first year) and the event each footnote mark points to
        for x in games:
            if x.get('date'):
                mo, dd = (int(v) for v in x['date'].split('/'))
                x['iso'] = f"{y - 1 if mo >= 8 else y}-{mo:02d}-{dd:02d}"
            if x.get('mark') and row['notes'].get(x['mark']):
                x['event'] = row['notes'][x['mark']].rstrip(',').strip()
        diffs = [f"{x['opp']} {x['res']} {x['pts']}-{x['opp_pts']} (series page: {', '.join(x['seriesSays'])})" for x in games if x.get('series') == 'differs']
        if diffs:
            checks.append('score differs from the series pages: ' + '; '.join(diffs))
        row['seriesMissing'] = [f"{x['opp']} {x['res']} {x['pts']}-{x['opp_pts']}" for x in games if x.get('series') == 'missing']
        row['checks'] = checks
        hist.append(row)
        if checks:
            report.append((y, checks))
    json.dump({'source': 'UConn 2026-27 Record Book, pp. 3-4 and 5-21', 'seasons': hist}, open(OUT, 'w'), indent=1)
    n = sum(1 for h in hist if not h['none'])
    print(f"{len(hist)} seasons ({n} with games, {sum(len(h['games']) for h in hist)} games); clean: {n - len(report)}; with issues: {len(report)}")
    for y, c in report:
        print(' ', y, c)


if __name__ == '__main__':
    main()
