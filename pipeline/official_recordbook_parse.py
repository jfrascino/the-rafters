"""Parse the season-by-season results pages of UConn's 2026-27 Men's Basketball
Record Book (pp. 5-15) into structured games, 1977-78 .. 2025-26.

Input : cache.nosync/official/recordbook_results_cols.txt  (official_recordbook_text.py)
Output: out/official/recordbook_games.json    {"1978": [{date, opp, site, res, pts, opp_pts, ot, note}, ...], ...}
        out/official/recordbook_seasons.json  season header facts + parse self-checks

Conventions
- date: ISO; the book prints M/D only, the year comes from the season (Aug-Dec = fall year).
- site: H / A / N as the record book designates it ("at X" = A, "vs. X" = N unless a UConn
  home venue is given, bare opponent = H unless a footnote puts the game at a neutral site).
  site_raw keeps the printed venue code / footnote venue.
- res/pts/opp_pts: UConn's perspective. The book prints losses either way round
  ("L, 71-67" in 2023-26, "L, 67-71" elsewhere); the UConn score is min() for L, max() for W.
- ot: 0, 1, 2 ... number of overtimes printed.
"""
import json, os, re, collections

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, 'cache.nosync/official/recordbook_results_cols.txt')
OUT_G = os.path.join(BASE, 'out/official/recordbook_games.json')
OUT_S = os.path.join(BASE, 'out/official/recordbook_seasons.json')

FIRST, LAST = 1978, 2026

SEASON_RE = re.compile(r'^((?:19|20)\d\d)-(\d\d)([#*]*)$')
GAME_RE = re.compile(r'^(\d{1,2})/(\d{1,2})\s+(.*)$')
RES_RE = re.compile(r'(?:(?<=\s)|^)([WLV])\s*,?\s*(\d{2,3})\s*-\s*(\d{2,3})\b(.*)$')
NOTPLAYED_RE = re.compile(r'\b(Postponed|Canceled|Cancelled)\b(.*)$', re.I)
OT_RE = re.compile(r'\(?\s*(\d?)\s*ot\s*\)?', re.I)
HOME_CODES = {'GP', 'HCC', 'XL', 'PBA', 'WBA', 'WB', 'FH', 'CMC-HCC', 'CMC-NHC'}
PAREN_RE = re.compile(r'\((GP|HCC|XL|PBA|WBA|WB|FH|MSG|XMA|MSA|CMC-HCC|CMC-NHC|OT)\)')
MARK_CHARS = '^%&*!~+#@$'
FOOT_RE = re.compile(r'^([\^%&*!~+#@$]+)\s*-?\s*(.*)$')
CMC_FOOT_RE = re.compile(r'^CMC-(.*)$')
# home venues named in footnotes (UConn-hosted events / designated home games)
HOME_VENUE_RE = re.compile(r'Gampel|Hartford Civic|Hartford CC|Hartford C\.C|Hartford, CT|Hartford, Conn|XL Center|New Haven Coliseum|Storrs|Civic Ctr', re.I)
NEUTRAL_EVENT_RE = re.compile(r'BIG EAST Tournament|Big East Tournament|NCAA|American Athletic Conference Championship|ECAC Tournament|National Invitation Tournament, Madison|NIT, 1st Round, Gampel', re.I)


def season_of(label):
    m = SEASON_RE.match(label)
    return int(m.group(1)) + 1 if m else None


def iso(season, mo, dy):
    yr = season - 1 if mo >= 8 else season
    return f'{yr:04d}-{mo:02d}-{dy:02d}'


def lines():
    for raw in open(SRC):
        raw = raw.rstrip('\n')
        if raw.startswith('====='):
            yield ('COL', raw)
            continue
        top, _, text = raw.partition('|')
        yield ('L', text.strip())


def split_opp(body):
    """body = text between date and result. Returns (prefix, opp, paren_codes, markers, extra_notes)."""
    notes = []
    b = body.strip()
    vac = False
    if b.startswith('**'):
        vac = True
        b = b[2:].strip()
    prefix = ''
    m = re.match(r'^(vs\.?|at)\s+(.*)$', b)
    if m:
        prefix = 'vs' if m.group(1).startswith('vs') else 'at'
        b = m.group(2)
    codes = PAREN_RE.findall(b)
    b2 = PAREN_RE.sub(' ', b)
    # markers attached anywhere in the name/rank area
    toks = b2.split()
    name = []
    markers = ''
    for i_, t in enumerate(toks):
        if t == '&' and name and i_ + 1 < len(toks) and re.fullmatch(r'[A-Z][a-z].*', toks[i_ + 1]) and toks[i_ + 1] != 'ARV':
            name.append('&')   # "William & Mary"
            continue
        core = t.strip(MARK_CHARS)
        lead = t[:len(t) - len(t.lstrip(MARK_CHARS))]
        trail_ = t[len(t.rstrip(MARK_CHARS)):] if core else ''
        mk = lead + trail_ if core else t  # interior '&' (Texas A&M) is not a marker
        # stop at rank / attendance / tv tokens
        if not core:
            markers += mk
            continue
        if re.fullmatch(r'[\d,.]+|ARV|arv|-+|t\d+|\d+ot', core):
            markers += mk
            break
        name.append(core)
        markers += mk
    # rank typos like "##1 0" leave '#' with digits glued; covered above
    opp = ' '.join(name).strip()
    return prefix, opp, codes, markers, vac


def main():
    seasons = collections.OrderedDict()
    cur = None
    state = None
    foot_buf = None
    for kind, text in lines():
        if kind == 'COL':
            continue
        m = SEASON_RE.match(text)
        if m and season_of(text) is not None:
            y = season_of(text)
            cur = seasons.setdefault(y, {'label': text, 'header': [], 'games': [], 'not_played': [], 'footnotes': {}, 'raw_lines': []})
            state = 'header'
            continue
        if cur is None:
            continue
        if not text:
            continue
        # page furniture
        if re.fullmatch(r'(NCAA NATIONAL( CHAMPIONS:)?|CHAMPIONS:.*|NATIONAL CHAMPIONS:|NCAA|[\d ]+)', text):
            continue
        g = GAME_RE.match(text)
        if g and not text.startswith(('1999 ', '2014 ', '2023 ')):
            state = 'games'
            cur['raw_lines'].append(text)
            mo, dy, rest = int(g.group(1)), int(g.group(2)), g.group(3)
            note = []
            if mo > 12:
                note.append(f'record book prints "{mo}/{dy}"; read as {mo % 10}/{dy}')
                mo = mo % 10
            r = RES_RE.search(rest)
            if not r:
                np_ = NOTPLAYED_RE.search(rest)
                cur['not_played'].append({'date': iso(y, mo, dy), 'text': text, 'status': np_.group(1) if np_ else 'no result'})
                continue
            body = rest[:r.start()]
            letter, a, b_, trail = r.group(1), int(r.group(2)), int(r.group(3)), r.group(4)
            if letter == 'V':
                note.append('record book prints "V" for the result (typo for W)')
                letter = 'W'
            prefix, opp, codes, markers, vac = split_opp(body)
            ot = 0
            mo_ot = OT_RE.search(trail)
            if mo_ot:
                ot = int(mo_ot.group(1) or 1)
            if 'OT' in codes:
                ot = max(ot, 1)
                codes = [c for c in codes if c != 'OT']
                note.append('OT printed as "(OT)" after the opponent name')
            if letter == 'W':
                pts, opp_pts = max(a, b_), min(a, b_)
            else:
                pts, opp_pts = min(a, b_), max(a, b_)
            if letter == 'W' and a < b_:
                note.append(f'printed "W, {a}-{b_}" (UConn lower score)')
            order = 'uconn-first' if a == pts else 'winner-first' if letter == 'L' else 'uconn-first'
            if vac:
                note.append('marked ** (NCAA tournament game vacated)')
            cur['games'].append({'date': iso(y, mo, dy), 'md': f'{mo}/{dy}', 'prefix': prefix, 'opp': opp, 'codes': codes, 'markers': markers,
                                 'res': letter, 'pts': pts, 'opp_pts': opp_pts, 'printed': f'{letter}, {a}-{b_}', 'ot': ot, 'note': note, 'vacated': vac,
                                 'line': text})
            continue
        if text.startswith('3/12-15'):
            cur['not_played'].append({'date': None, 'text': text, 'status': 'Canceled (AAC tournament, COVID-19)'})
            continue
        if state == 'header':
            cur['header'].append(text)
            continue
        # footnotes
        f = FOOT_RE.match(text)
        c = CMC_FOOT_RE.match(text)
        if f and f.group(2):
            key = f.group(1)
            txt = f.group(2)
            # two footnotes printed on one line: "$ Hershey Arena, Hershey, PA + Big Island Invitational, Hilo, HI"
            m2 = re.search(r'\s([\^%*!~+#@$]+)\s(?=[A-Z])', txt)  # not '&' ('First & Second Rounds')
            if m2:
                cur['footnotes'][m2.group(1)] = txt[m2.end():]
                txt = txt[:m2.start()]
            cur['footnotes'][key] = txt
            foot_buf = key
        elif c:
            cur['footnotes']['CMC'] = c.group(1)
            foot_buf = 'CMC'
        elif foot_buf and state == 'games':
            cur['footnotes'][foot_buf] += ' ' + text
    return seasons


def parse_header(h):
    out = {'coach': None, 'overall': None, 'conf': None, 'home': None, 'away': None, 'neutral': None, 'notes': []}
    for t in h:
        m = re.match(r'Head Coach:\s*(.*)$', t)
        if m:
            out['coach'] = m.group(1).strip()
            continue
        m = re.match(r'^(\d+)-(\d+)(\*\*)?(?:\s+overall|\s+Overall)?(?:,\s*(?:in the\s+)?(\d+)-(\d+))?', t)
        if m and out['overall'] is None and 'home' not in t:
            out['overall'] = [int(m.group(1)), int(m.group(2))]
            if m.group(4):
                out['conf'] = [int(m.group(4)), int(m.group(5))]
            continue
        m = re.match(r'^(\d+)-(\d+) home, (\d+)-(\d+) (?:away|road), (\d+)-(\d+) neutral', t)
        if m:
            v = list(map(int, m.groups()))
            out['home'], out['away'], out['neutral'] = v[0:2], v[2:4], v[4:6]
            continue
        if re.fullmatch(r'(AP Rank(ing)?|R ?ank|Date Opponent.*)', t):
            continue
        out['notes'].append(t)
    return out


def site_of(g, footnotes):
    """H/A/N per the record book's own designation."""
    codes = g['codes']
    fnote = None
    for mk in sorted(footnotes, key=len, reverse=True):
        if mk != 'CMC' and mk and g['markers'].startswith(mk) or (mk != 'CMC' and mk == g['markers']):
            fnote = footnotes[mk]
            break
    if any(c.startswith('CMC') for c in codes):
        fnote = footnotes.get('CMC', fnote)
    site_raw = ' '.join(f'({c})' for c in codes)
    if fnote:
        site_raw = (site_raw + ' ' if site_raw else '') + '[' + fnote + ']'
    if g['prefix'] == 'at':
        return 'A', site_raw
    if any(c in HOME_CODES for c in codes):
        return 'H', site_raw
    if g['prefix'] == 'vs':
        return 'N', site_raw
    # bare opponent: home unless a footnote places it at a neutral venue
    if fnote:
        if 'UGame' in fnote:
            return 'N', site_raw          # MassMutual UGame at Hartford CC: book tallies it neutral (2000-01)
        if re.fullmatch(r'\s*National Invitation Tournament\s*', fnote):
            return 'H', site_raw          # NIT games hosted by UConn (book tallies them home)
        if not HOME_VENUE_RE.search(fnote):
            return 'N', site_raw
    return 'H', site_raw


if __name__ == '__main__':
    seasons = main()
    games_out = collections.OrderedDict()
    seasons_out = collections.OrderedDict()
    for y in sorted(seasons):
        if not (FIRST <= y <= LAST):
            continue
        s = seasons[y]
        hdr = parse_header(s['header'])
        glist = []
        prev = None
        for g in sorted(s['games'], key=lambda x: 0):  # keep printed order
            site, site_raw = site_of(g, s['footnotes'])
            note = list(g['note'])
            if prev and g['date'] < prev:
                note.append(f'date {g["md"]} printed out of sequence (previous game {prev})')
            prev = g['date']
            glist.append({'date': g['date'], 'opp': g['opp'], 'site': site, 'res': g['res'], 'pts': g['pts'], 'opp_pts': g['opp_pts'],
                          'ot': g['ot'], 'note': '; '.join(note) or None, 'site_raw': site_raw or None, 'printed': g['printed'],
                          'vacated': g['vacated'] or None, 'line': g['line']})
        games_out[str(y)] = glist
        # self-checks against the header lines
        tally = collections.Counter()
        for g in glist:
            tally[('all', g['res'])] += 1
            tally[(g['site'], g['res'])] += 1
        chk = {
            'games_parsed': len(glist),
            'wl_parsed': [tally[('all', 'W')], tally[('all', 'L')]],
            'home_parsed': [tally[('H', 'W')], tally[('H', 'L')]],
            'away_parsed': [tally[('A', 'W')], tally[('A', 'L')]],
            'neutral_parsed': [tally[('N', 'W')], tally[('N', 'L')]],
        }
        chk['wl_ok'] = chk['wl_parsed'] == hdr['overall']
        chk['han_ok'] = [chk['home_parsed'], chk['away_parsed'], chk['neutral_parsed']] == [hdr['home'], hdr['away'], hdr['neutral']]
        seasons_out[str(y)] = {'label': s['label'], **hdr, 'footnotes': s['footnotes'], 'not_played': s['not_played'], 'check': chk}
    os.makedirs(os.path.dirname(OUT_G), exist_ok=True)
    json.dump({'_source': 'UConn Men\'s Basketball 2026-27 Record Book (Updated for 2026-27), pp. 5-15 "All-Time Results": https://uconnhuskies.com/documents/download/2026/8/13/RECORD_BOOK_26-27_V2_.pdf',
               '_fields': 'date ISO (year inferred from season); site H/A/N as the book designates it; res/pts/opp_pts from UConn perspective; ot = number of overtimes printed; note = parse/typo notes; printed = score exactly as printed; line = raw text line',
               **games_out}, open(OUT_G, 'w'), indent=1, ensure_ascii=False)
    json.dump(seasons_out, open(OUT_S, 'w'), indent=1, ensure_ascii=False)
    n = sum(len(v) for v in games_out.values())
    print('games', n)
    for y, s in seasons_out.items():
        c = s['check']
        flag = '' if c['wl_ok'] and c['han_ok'] else '  <-- CHECK'
        print(y, s['label'], s['coach'], 'hdr', s['overall'], s['conf'], s['home'], s['away'], s['neutral'], '| parsed', c['wl_parsed'], c['home_parsed'], c['away_parsed'], c['neutral_parsed'], len(s['not_played']), flag)
