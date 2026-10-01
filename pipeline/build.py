#!/usr/bin/env python3
"""Merge Sports-Reference, ESPN and media research into the app's data files (site/data/).

Inputs  pipeline/out/{sr,espn,media}/...   (see sr_scrape.py, espn_fetch.py, media_*.py)
Outputs site/data/core.json, games_index.json, media.json, seasons/Y.json, games/Y.json, plays/ID.json, players/PID.json
"""
import json, glob, os, re, math, unicodedata, datetime, urllib.request, urllib.parse, collections, hashlib
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
CACHE = os.path.join(HERE, 'cache.nosync')
SITE = os.path.join(HERE, '..', 'site', 'data')
ET = ZoneInfo('America/New_York')
UCONN_ESPN = '41'
FIRST, = (1978,)   # Dom Perno's first season, 1977-78

ERAS = [
    {'id': 'perno', 'name': 'Dom Perno', 'short': 'Perno', 'from': 1978, 'to': 1986},
    {'id': 'calhoun', 'name': 'Jim Calhoun', 'short': 'Calhoun', 'from': 1987, 'to': 2012},
    {'id': 'ollie', 'name': 'Kevin Ollie', 'short': 'Ollie', 'from': 2013, 'to': 2018},
    {'id': 'hurley', 'name': 'Dan Hurley', 'short': 'Hurley', 'from': 2019, 'to': 9999},
]
# Fallback Most Outstanding Players (NCAA record book); media/legends.json overrides when present.
MOP = {1999: 'Richard Hamilton', 2004: 'Emeka Okafor', 2011: 'Kemba Walker', 2014: 'Shabazz Napier', 2023: 'Adama Sanogo', 2024: 'Tristen Newton'}
ROUND_NAMES = ['First Round', 'Second Round', 'Sweet 16', 'Elite Eight', 'Final Four', 'National Championship']


def jload(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def jdump(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        json.dump(obj, f, separators=(',', ':'), ensure_ascii=False)


def img_url(x):
    """Media records store images as a URL string or a {thumb_url, image_url} dict."""
    if isinstance(x, dict):
        return x.get('thumb_url') or x.get('image_url') or x.get('url')
    return x or None


def et_date(iso):
    if not iso:
        return None
    if len(iso) == 10:
        return iso
    dt = datetime.datetime.fromisoformat(iso.replace('Z', '+00:00'))
    return dt.astimezone(ET).date().isoformat()


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r"[.'`’\-]", '', s)
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def label(y):
    return f"{y - 1}–{str(y)[2:]}"


def num(v):
    if v is None or v == '':
        return None
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return None


# ───────────────────────── Load sources ─────────────────────────
sr_seasons = {}
for f in glob.glob(os.path.join(OUT, 'sr', 'seasons', '*.json')):
    d = jload(f)
    if d:
        sr_seasons[int(d['year'])] = d
sr_boxes = {os.path.basename(f)[:-5]: jload(f) for f in glob.glob(os.path.join(OUT, 'sr', 'boxscores', '*.json'))}
# Games SR counts in the record but omits from the schedule (non-D-I opponents); renumber and recompute running records
MANUAL = jload(os.path.join(HERE, 'manual_games.json'), {}) or {}
for yk, fixes in (MANUAL.get('date_fixes') or {}).items():
    for fx in fixes:
        for g in (sr_seasons.get(int(yk)) or {}).get('schedule', []):
            if g['date'] == fx['sr_date'] and norm(fx['opp']) in norm(g.get('opp_name')):
                g['date'] = fx['date']
for yk, extra in MANUAL.items():
    if yk.startswith('_') or yk == 'date_fixes' or int(yk) not in sr_seasons:
        continue
    sch = sr_seasons[int(yk)]['schedule']
    have = {(g['date'], g.get('opp_name')) for g in sch}
    for g in extra:
        if (g['date'], g['opp_name']) not in have:
            sch.append(dict(g))
    sch.sort(key=lambda g: (g['date'], g.get('g') or 0))
    w = l = 0
    for i, g in enumerate(sch):
        g['g'] = i + 1
        w += g.get('game_result') == 'W'
        l += g.get('game_result') == 'L'
        g['wins'], g['losses'] = w, l

# Rulings on facts where Sports-Reference and UConn's own archive disagree (settled from contemporaneous AP/NCAA sources)
ADJ = jload(os.path.join(OUT, 'official', 'adjudication.json'), {}) or {}
for d in ADJ.get('decisions', []):
    try:
        y_, n_ = map(int, d['game'].split('-'))
    except (KeyError, ValueError):
        continue
    g_ = next((x for x in (sr_seasons.get(y_) or {}).get('schedule', []) if x['g'] == n_), None)
    t = d.get('truth') or ''
    if not g_:
        continue
    if d.get('field') == 'score':
        m = re.match(r'([WL]) (\d+)-(\d+)', t)
        if m:
            g_['game_result'], g_['pts'], g_['opp_pts'] = m.group(1), int(m.group(2)), int(m.group(3))
    elif d.get('field') == 'date' and re.fullmatch(r'\d{4}-\d\d-\d\d', t):
        g_['date'] = t
    elif d.get('field') == 'site' and t.split(' ')[0] in ('home', 'away', 'neutral'):
        g_['site'] = t.split(' ')[0]
# Game facts settled against UConn's record book and independent sources (pipeline/game_rulings.json, built by
# official_game_rulings.py): dates, home/away/neutral, overtime, a misprinted score, the 1979-80 Utah forfeit.
for r_ in (jload(os.path.join(HERE, 'game_rulings.json'), {}) or {}).get('rulings') or []:
    if r_.get('needs_match') or not r_.get('date'):
        continue
    sch_ = (sr_seasons.get(int(r_['season'])) or {}).get('schedule', [])
    on_ = norm(r_['opp'])
    day_ = [x for x in sch_ if r_['date'] in (x['date'], x.get('_orig_date'))]   # an earlier ruling may already have moved the date
    g_ = next((x for x in day_ if on_ in norm(x.get('opp_name')) or norm(x.get('opp_name')) in on_), None) or (day_[0] if len(day_) == 1 else None)
    if not g_:
        print(f"  !! game ruling matched no game: {r_['season']} {r_['date']} {r_['opp']} {r_['set']}")
        continue
    st_ = r_['set']
    if 'date' in st_:
        g_.setdefault('_orig_date', g_['date'])
    for k_, sk_ in (('date', 'date'), ('site', 'site'), ('arena', 'arena'), ('ot', 'overtimes'), ('res', 'game_result'), ('pts', 'pts'), ('opp_pts', 'opp_pts')):
        if k_ in st_:
            g_[sk_] = st_[k_]
    if 'arena' in st_:
        g_['arena_verified'] = True
    if st_.get('forfeit'):
        g_['forfeit'] = st_.get('note') or True
for y_, sd_ in sr_seasons.items():   # a corrected date can reorder a season: keep game numbers and running records in date order
    sch_ = sd_.get('schedule') or []
    if [g.get('g') for g in sch_] != [g.get('g') for g in sorted(sch_, key=lambda g: (g['date'], g.get('g') or 0))]:
        sch_.sort(key=lambda g: (g['date'], g.get('g') or 0))
        print(f"  {y_}: a corrected date reordered the schedule; renumbering")
        for i_, g in enumerate(sch_):
            g['g'] = i_ + 1
    w_ = l_ = 0
    for g in sch_:
        w_ += g.get('game_result') == 'W'
        l_ += g.get('game_result') == 'L'
        if g.get('game_result'):
            g['wins'], g['losses'] = w_, l_
FORCE_PLAYED = set()   # (game id, player name) the official box shows appearing though Sports-Reference omits them
EXCLUDED_APPEARANCES = collections.defaultdict(list)   # (pid, season) -> game ids where ESPN's box lists him but Sports-Reference's doesn't
for st in ADJ.get('stats', []):
    if 'appearance' in (st.get('stat') or '') and st.get('winner') == 'espn':
        FORCE_PLAYED.add((st['game'], norm(st.get('player'))))
# NCAA-vacated games (NCAA Records Book, "Vacated and Forfeited Games")
VACATED = {
    1996: {'official': '30–2', 'note': 'The NCAA later vacated all three 1996 NCAA Tournament games (Colgate, Eastern Michigan, Mississippi State).', 'test': lambda g: g['type'] == 'NCAA'},
    2017: {'official': '0–0', 'note': 'The NCAA vacated the entire 2016–17 season (16 wins, 17 losses) in 2019.', 'test': lambda g: True},
    2018: {'official': '0–1', 'note': 'The NCAA vacated every 2017–18 game except the March 8 AAC tournament loss to SMU.', 'test': lambda g: g['date'][:10] != '2018-03-08'},
}
OFFICIAL_NUMS = {int(k): {norm(n): v for n, v in d.items()} for k, d in (jload(os.path.join(OUT, 'official', 'numbers.json'), {}) or {}).items()}
ROSTER_SHIFTED = {2018}   # uconnhuskies.com's "2017-18" roster page carries the 2018-19 roster (every class a year ahead)
for _y in ROSTER_SHIFTED:
    OFFICIAL_NUMS.pop(_y, None)
# UConn's official season rosters (2003-04 on): listed height, weight, class and hometown (pipeline/official_rosters_bio.py)
ROSTER_BIOS = {int(k): v for k, v in (jload(os.path.join(OUT, 'official', 'roster_bios.json'), {}) or {}).items() if int(k) not in ROSTER_SHIFTED}
AP_STATES = {'Ala.': 'AL', 'Alaska': 'AK', 'Ariz.': 'AZ', 'Ark.': 'AR', 'Calif.': 'CA', 'Colo.': 'CO', 'Conn.': 'CT', 'Del.': 'DE', 'D.C.': 'DC', 'Fla.': 'FL', 'Ga.': 'GA',
             'Hawaii': 'HI', 'Idaho': 'ID', 'Ill.': 'IL', 'Ind.': 'IN', 'Iowa': 'IA', 'Kan.': 'KS', 'Kans.': 'KS', 'Ky.': 'KY', 'La.': 'LA', 'Maine': 'ME', 'Md.': 'MD',
             'Mass.': 'MA', 'Mich.': 'MI', 'Minn.': 'MN', 'Miss.': 'MS', 'Mo.': 'MO', 'Mont.': 'MT', 'Neb.': 'NE', 'Nev.': 'NV', 'N.H.': 'NH', 'N.J.': 'NJ', 'N.M.': 'NM',
             'N.Y.': 'NY', 'N.C.': 'NC', 'N.D.': 'ND', 'Ohio': 'OH', 'Okla.': 'OK', 'Ore.': 'OR', 'Pa.': 'PA', 'R.I.': 'RI', 'S.C.': 'SC', 'S.D.': 'SD', 'Tenn.': 'TN',
             'Texas': 'TX', 'Utah': 'UT', 'Vt.': 'VT', 'Va.': 'VA', 'Wash.': 'WA', 'W.Va.': 'WV', 'Wis.': 'WI', 'Wyo.': 'WY'}


def official_bio(y, name):
    cards = [c for c in ROSTER_BIOS.get(y, []) if c.get('cls') or c.get('ht')]
    c = next((c for c in cards if norm(c['name']) == norm(name)), None)
    if not c:
        alt = [c for c in cards if norm(c['name']).split()[-1:] == norm(name).split()[-1:] and norm(c['name'])[:1] == norm(name)[:1]]
        c = alt[0] if len(alt) == 1 else None
    if not c:
        return {}
    out = {}
    m = re.match(r"\s*(\d)\s*'\s*(\d{1,2})", c.get('ht') or '')
    if m:
        out['ht'] = f'{m.group(1)}-{m.group(2)}'
    m = re.match(r'(\d{3})', c.get('wt') or '')
    if m:
        out['wt'] = int(m.group(1))
    home = c.get('home') or ''
    if ',' not in home and re.search(r'^[A-Za-z .]+?[a-z]\. [A-Z]\.', home):   # "Raleigh. N.C." (a typo on the roster page), not "Mt. Airy, Md."
        home = re.sub(r'([a-z])\. (?=[A-Z]\.)', r'\1, ', home, count=1)
    if home:
        city_, _, st_ = home.rpartition(', ')
        out['home'] = f'{city_}, {AP_STATES.get(st_.strip(), st_.strip())}' if city_ else home
    cl = re.sub(r'\s+', '', (c.get('cls') or '').lower())
    red = cl.startswith('r-') or cl.startswith('redshirt')
    base = {'fr': 'FR', 'so': 'SO', 'jr': 'JR', 'sr': 'SR', 'gr': 'GR', 'grad': 'GR', '5th': 'GR', 'gs': 'GR'}.get(re.sub(r'^(r-|redshirt)', '', cl).rstrip('.'))
    if base:
        out['cls'] = base
    return out
# The record book's ALL-TIME UNIFORM NUMBERS list (pipeline/official_uniforms.py): every number every letterwinner wore,
# by season. It outranks the roster archive and Sports-Reference (SR had 23 wrong numbers 2004-26 alone).
UNIFORMS = {int(k): v for k, v in ((jload(os.path.join(OUT, 'official', 'uniforms.json'), {}) or {}).get('by_year') or {}).items()}
NUM_DISAGREE = []
PBP_DROPPED = []   # games whose ESPN play-by-play doesn't end at the final score
BIO_CHANGES = []
# Honors where Sports-Reference's tally disagrees with UConn's record book honor lists (pp. 57-58), verified by dev/check_honors.py
RB_DRAFT = ((jload(os.path.join(OUT, 'official', 'draft.json'), {}) or {}).get('picks') or [])   # record book: the team each draftee went to
DRAFT_TEAM_FIX = {'shabazz-napier-1': 'Charlotte Hornets', 'emeka-okafor-1': 'Charlotte Bobcats'}   # Sports-Reference leaves the picking team blank
HONOR_FIX = {'khalid-el-amin-1': {'3x All-Big East': '2x All-Big East'}}   # record book: 2nd team 1998-99, 1st team 1999-00 (All-Rookie only in 1997-98)


def uniform_for(y, name):
    parts = norm(name).split()
    if not parts:
        return None
    last, first = parts[-1], (parts[0] if len(parts) > 1 else '')
    hits = []
    for e in UNIFORMS.get(y, []):
        ep = norm(e['name']).split()
        if not ep or ep[-1] != last:
            continue
        ef = ep[0] if len(ep) > 1 else ''
        short, long_ = sorted((first, ef), key=len)
        # same first name, a short form of it (Joe/Joey, Al/Alvin, Cliff/Clifford), a nickname (Jim/James) or a spelling
        # variant (Javon/Jevon, Keifer/Kiefer) -- never just a shared initial (Jacob/Jayden Ross)
        from official_stats import NICK as _NICK
        import difflib as _dl
        if (first == ef or (len(short) >= 2 and long_.startswith(short)) or _NICK.get(first, first) == _NICK.get(ef, ef)
                or (min(len(first), len(ef)) >= 5 and _dl.SequenceMatcher(None, first, ef).ratio() >= 0.8)):
            hits.append(e['num'])
    return hits[0] if len(set(hits)) == 1 else None
from official_stats import Official   # UConn's record book + season-final stat sheets settle every player stat (see official_stats.py)
OFFICIAL_STATS = Official()
_rej = jload(os.path.join(HERE, 'photo_rejects.json'), {}) or {}
REJECT_HASHES = set((_rej.get('hashes') or {}).keys())
sr_players = {os.path.basename(f)[:-5]: jload(f) for f in glob.glob(os.path.join(OUT, 'sr', 'players', '*.json'))}
school_index = {r['season']: r for r in (jload(os.path.join(OUT, 'sr', 'school_index.json'), {}) or {}).get('seasons', [])}

# Box scores transcribed from contemporary newspapers for games no other source covers; only from fact-checked Moments
NEWSPAPER_BOXES = {}
for _f in glob.glob(os.path.join(OUT, 'moments', 'verified', '*.json')):
    _m = jload(_f) or {}
    if _m.get('gameId') and isinstance(_m.get('box'), dict) and len(_m['box'].get('teams') or []) == 2:
        NEWSPAPER_BOXES[_m['gameId']] = _m


def newspaper_det(g, m, opp):
    box = m['box']
    src = box.get('source') if isinstance(box.get('source'), dict) else {'paper': box.get('source')}
    teams = []
    for k, t in enumerate(box['teams'][:2]):
        isU = k == 0
        st = t.get('stats') or {}
        pct = lambda a, b: round(100 * st[a] / st[b], 1) if st.get(b) else None
        players = [{'name': p['name'], 'pid': p.get('pid') if isU else None, 'starter': bool(p.get('starter')), 'photo': photo_for.get(p.get('pid')) if isU else None,
                    **{k2: p.get(k2) for k2 in ('min', 'pts', 'fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'reb', 'ast')}} for p in t.get('players') or []]
        base = {'name': 'UConn', 'abbr': 'CONN', 'logo': 'https://a.espncdn.com/i/teamlogos/ncaa/500/41.png'} if isU else {k2: opp.get(k2) for k2 in ('name', 'abbr', 'logo')}
        teams.append({**base, 'score': t.get('score'), 'line': t.get('line'), 'boxSource': 'newspaper', 'players': players,
                      'stats': {'fg_pct': pct('fgm', 'fga'), 'tp_pct': pct('tpm', 'tpa'), 'ft_pct': pct('ftm', 'fta'), 'reb': st.get('reb'), 'ast': st.get('ast')}})
    return {'venue': {'name': m.get('venue') or g.get('arena'), 'city': m.get('city') or g.get('city')}, 'att': box.get('att'), 'officials': [], 'teams': teams,
            'source': 'newspaper', 'boxNote': f"Box score transcribed from {src.get('paper') or 'a contemporary newspaper'}{', ' + src['date'] if src.get('date') else ''}.",
            'boxSrc': src.get('page_url')}


espn_games = {}
for f in glob.glob(os.path.join(OUT, 'espn', 'games', '*.json')):
    d = jload(f)
    if d:
        espn_games[str(d['id'])] = d
espn_sched = {int(os.path.basename(f)[:-5]): jload(f) for f in glob.glob(os.path.join(OUT, 'espn', 'schedules', '*.json'))}
athletes = jload(os.path.join(OUT, 'espn', 'athletes.json'), {}) or {}
espn_current = jload(os.path.join(OUT, 'espn', 'current.json'), {}) or {}
espn_teams = jload(os.path.join(OUT, 'espn', 'teams.json'), {}) or {}

M = os.path.join(OUT, 'media')
media_seasons = jload(os.path.join(M, 'seasons.json'), []) or []
media_images = jload(os.path.join(M, 'images.json'), {}) or {}
media_videos = (jload(os.path.join(M, 'videos.json'), {}) or {})
media_videos = media_videos.get('videos', media_videos) if isinstance(media_videos, dict) else media_videos
legends = jload(os.path.join(M, 'legends.json'), {}) or {}
# Venue truth table: the true building for every game and its name on that date (Hartford Civic Center → XL Center → PeoplesBank Arena, etc.)
_ven = jload(os.path.join(OUT, 'official', 'venues.json'), {}) or {}
BUILDING_CITY = {b['key']: b.get('city') for b in _ven.get('renames') or []}
VENUE_ERA = {x['id']: x for x in _ven.get('game_venue_era') or []}


def json_path_get(root, path):
    """'coaches[0].bio[2]' → (parent, key) so the caller can read/replace/remove."""
    toks = re.findall(r'\["([^"]+)"\]|([^.\[\]"]+)|\[(\d+)\]', path)
    cur, parent, key = root, None, None
    for qname, name, idx in toks:
        parent, key = cur, (int(idx) if idx else (qname or name))
        try:
            cur = cur[key]
        except (KeyError, IndexError, TypeError):
            return None, None
    return parent, key


def apply_legends_ledger(led):
    ok = bad = 0
    removals = []
    for it in (led or {}).get('items', []):
        st, path = it.get('status'), it.get('path') or ''
        if st not in ('FIX', 'REMOVE', 'ADD'):
            continue
        parent, key = json_path_get(legends, path)
        if parent is None and st == 'ADD':
            ppath, _, last = path.rpartition('[')
            pp, pk = json_path_get(legends, ppath)
            k2 = last.rstrip(']').strip('"')
            if pp is not None and isinstance(pp[pk], dict):
                pp[pk][k2] = []
                parent, key = pp[pk], k2
        if parent is None:
            bad += 1
            continue
        cur = parent[key]
        old, new = it.get('old'), it.get('new')
        if st == 'ADD':
            if isinstance(cur, list) and new is not None and new not in cur:
                cur.append(new)
                ok += 1
            else:
                bad += 1
        elif st == 'FIX':
            if isinstance(cur, str) and isinstance(old, str) and old and old != cur:
                if cur.count(old) == 1:
                    parent[key] = cur.replace(old, str(new))
                    ok += 1
                else:
                    bad += 1
            else:
                parent[key] = new
                ok += 1
        elif st == 'REMOVE':
            if isinstance(cur, str) and isinstance(old, str) and old and old != cur and cur.count(old) == 1:
                parent[key] = re.sub(r'\s{2,}', ' ', cur.replace(old, '')).strip()
                ok += 1
            else:
                removals.append((parent, key))
                ok += 1
    for parent, key in sorted(removals, key=lambda pk: -pk[1] if isinstance(pk[1], int) else 0):
        try:
            if isinstance(parent, list):
                parent.pop(key)
            else:
                parent.pop(key, None)
        except (IndexError, KeyError):
            pass
    if led:
        print(f'legends ledger: applied {ok}, skipped {bad}')


apply_legends_ledger(jload(os.path.join(M, 'verify_legends.json')))
_cp = jload(os.path.join(M, 'coach_perno.json'))
if isinstance(_cp, dict) and _cp.get('name') and not any(norm(c.get('name')) == norm(_cp['name']) for c in legends.get('coaches') or []):
    legends.setdefault('coaches', []).insert(0, _cp)
# The Husky logo UConn used each season (for player cards without a photo)
_lg = jload(os.path.join(M, 'logos.json'), {}) or {}
LOGOS = {'by_season': {str(k): v for k, v in (_lg.get('by_season') or {}).items()},
         'files': {l['key']: l['file'] for l in (_lg.get('logos') or []) if l.get('key') and l.get('file') and os.path.exists(os.path.join(HERE, '..', 'site', l['file']))}}
if isinstance(media_seasons, dict):
    media_seasons = media_seasons.get('seasons', list(media_seasons.values()))
_perno = jload(os.path.join(M, 'seasons_perno.json'), []) or []
media_seasons = list(media_seasons) + [m for m in (_perno.get('seasons', _perno) if isinstance(_perno, dict) else _perno) if isinstance(m, dict)]
media_by_year = {int(m['year']): m for m in media_seasons if isinstance(m, dict) and m.get('year')}

# Apply the independent fact-check ledger (FIX = replace exact substring, REMOVE = drop it)
def apply_ledger(path):
    led = jload(path, {}) or {}
    ok = bad = 0
    for it in led.get('items', []):
        if it.get('status') not in ('FIX', 'REMOVE'):
            continue
        m = media_by_year.get(int(it.get('year') or 0))
        field = it.get('field') or ''
        mm = re.match(r'(\w+)(?:\[(\d+)\](?:\.(\w+))?)?$', field)
        if not m or not mm:
            bad += 1
            continue
        key, idx, sub = mm.group(1), mm.group(2), mm.group(3)
        holder, hkey = m, key
        if idx is not None:
            lst = m.get(key) or []
            i = int(idx)
            if i >= len(lst):
                bad += 1
                continue
            if sub:
                holder, hkey = lst[i], sub
            else:
                holder, hkey = lst, i
        cur = holder[hkey] if (isinstance(holder, list) or hkey in holder) else None
        old, new = it.get('old') or '', it.get('new') or ''
        if not isinstance(cur, str) or (old and cur.count(old) != 1):
            bad += 1
            continue
        if it['status'] == 'REMOVE' and (not old or old.strip() == cur.strip()):
            holder[hkey] = None
        else:
            holder[hkey] = cur.replace(old, new if it['status'] == 'FIX' else '').replace('  ', ' ').strip() if old else new
        ok += 1
    for m in media_by_year.values():  # drop removed list entries
        for k in ('key_moments', 'honors'):
            if isinstance(m.get(k), list):
                m[k] = [x for x in m[k] if x and (not isinstance(x, dict) or x.get('text') is not None or x.get('title'))]
    if led:
        print(f'fact-check ledger: applied {ok}, skipped {bad}')


apply_ledger(os.path.join(M, 'verify_seasons.json'))


# All D-I teams from ESPN, for logos of opponents we only met before 2003.
def espn_all_teams():
    p = os.path.join(CACHE, 'espn_all_teams.json')
    d = jload(p)
    if not d:
        try:
            url = 'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams?limit=1000'
            raw = json.load(urllib.request.urlopen(url, timeout=30))
            d = [t['team'] for t in raw['sports'][0]['leagues'][0]['teams']]
            jdump(p, d)
        except Exception as e:  # offline is fine
            print('! could not fetch ESPN team list:', e)
            d = []
    return d


ALL_TEAMS = espn_all_teams()
teams_by_id = {}
for t in ALL_TEAMS:
    teams_by_id[str(t['id'])] = {'id': str(t['id']), 'name': t.get('location') or t.get('shortDisplayName'), 'abbr': t.get('abbreviation'), 'color': t.get('color'),
                                  'logo': (t.get('logos') or [{}])[0].get('href')}
for tid, t in (espn_teams.items() if isinstance(espn_teams, dict) else []):
    cur = teams_by_id.setdefault(str(tid), {'id': str(tid)})
    for k_src, k_dst in (('location', 'name'), ('abbr', 'abbr'), ('color', 'color'), ('logo', 'logo')):
        if t.get(k_src) and not cur.get(k_dst):
            cur[k_dst] = t[k_src]
    if not cur.get('name'):
        cur['name'] = t.get('name')

ALIASES = {'miami (fl)': 'miami', 'st johns (ny)': 'st johns', 'saint marys (ca)': 'saint marys', 'miami (oh)': 'miami (oh)', 'texas christian': 'tcu',
           'southern methodist': 'smu', 'central florida': 'ucf', 'louisiana state': 'lsu', 'brigham young': 'byu', 'virginia commonwealth': 'vcu',
           'nevada-las vegas': 'unlv', 'nevadalas vegas': 'unlv', 'massachusetts': 'umass', 'pittsburgh': 'pittsburgh', 'southern california': 'usc', 'north carolina state': 'nc state',
           'mississippi': 'ole miss', 'albany (ny)': 'ualbany', 'maryland-baltimore county': 'umbc', 'marylandbaltimore county': 'umbc', 'texas-el paso': 'utep', 'california': 'california',
           'long island university': 'liu', 'st francis (ny)': 'st francis brooklyn', 'loyola (md)': 'loyola maryland', 'loyola (il)': 'loyola chicago', 'illinoischicago': 'uic',
           'mount st marys': 'mount st marys', 'fairleigh dickinson': 'fairleigh dickinson', 'central connecticut state': 'central connecticut', 'st peters': 'saint peters',
           'penn': 'pennsylvania', 'ucla': 'ucla', 'uc santa barbara': 'uc santa barbara', 'florida international': 'fiu', 'detroit mercy': 'detroit mercy', 'detroit': 'detroit mercy',
           'southwest texas state': 'texas state', 'texas-rio grande valley': 'ut rio grande valley', 'bethunecookman': 'bethunecookman', 'college of charleston': 'charleston',
           'north carolina-wilmington': 'unc wilmington', 'north carolinawilmington': 'unc wilmington', 'north carolinaasheville': 'unc asheville', 'north carolinagreensboro': 'unc greensboro',
           'arkansas-little rock': 'little rock', 'arkansaslittle rock': 'little rock', 'louisiana-monroe': 'ul monroe', 'hawaii': 'hawaii', 'grambling': 'grambling', 'texas-arlington': 'ut arlington',
           'texasarlington': 'ut arlington', 'texassan antonio': 'utsa', 'wisconsinmilwaukee': 'milwaukee', 'wisconsingreen bay': 'green bay', 'tennesseemartin': 'ut martin', 'missourikansas city': 'kansas city',
           'purdue fort wayne': 'purdue fort wayne', 'iupui': 'iu indianapolis', 'southeastern louisiana': 'se louisiana', 'md-eastern shore': 'maryland eastern shore', 'mdeastern shore': 'maryland eastern shore',
           'prairie view': 'prairie view am', 'alabama am': 'alabama am', 'central michigan': 'central michigan', 'saint josephs': 'saint josephs', 'st josephs': 'saint josephs', 'st bonaventure': 'st bonaventure',
           'massachusetts-lowell': 'umass lowell', 'massachusettslowell': 'umass lowell', 'maryland-eastern shore': 'maryland eastern shore', 'new jersey tech': 'njit', 'njit': 'njit'}
name_to_tid = {}
for tid, t in teams_by_id.items():
    for n in {t.get('name'), t.get('abbr')}:
        if n:
            name_to_tid.setdefault(norm(n), tid)


def tid_for_name(n):
    k = norm(n)
    k2 = re.sub(r'\s*\(.*?\)', '', k).strip()
    for cand in (ALIASES.get(k), k, ALIASES.get(k2), k2, k.replace('saint', 'st'), k.replace('st ', 'saint ')):
        if cand and cand in name_to_tid:
            return name_to_tid[cand]
    return None


# ───────────────────────── Match SR games ↔ ESPN events ─────────────────────────
espn_by_date = collections.defaultdict(list)
for g in espn_games.values():
    espn_by_date[et_date(g['date'])].append(g)


def uc_opp(g):
    """(uconn_team, opp_team) from an ESPN game."""
    ts = g.get('teams') or []
    u = next((t for t in ts if str(t.get('id')) == UCONN_ESPN), None)
    o = next((t for t in ts if str(t.get('id')) != UCONN_ESPN), None)
    return u, o


sr2tid = {}          # SR opponent slug → ESPN team id
sr_game_espn = {}    # (year, g) → espn game
for y, s in sr_seasons.items():
    for g in s.get('schedule', []):
        cands = espn_by_date.get(g.get('date'), [])
        if not cands:
            # ESPN sometimes files late tips on the next UTC day already handled by ET; try ±1 day
            d0 = datetime.date.fromisoformat(g['date'])
            for dd in (-1, 1):
                cands = espn_by_date.get((d0 + datetime.timedelta(days=dd)).isoformat(), [])
                cands = [c for c in cands if c.get('status') == 'final' and (uc_opp(c)[0] or {}).get('score') is not None and int(float(uc_opp(c)[0]['score'])) == g.get('pts')]
                if cands:
                    break
        if len(cands) >= 1:
            e = cands[0]
            if len(cands) > 1:
                e = next((c for c in cands if (uc_opp(c)[0] or {}).get('score') is not None and int(float(uc_opp(c)[0]['score'])) == g.get('pts')), cands[0])
            sr_game_espn[(y, g['g'])] = e
            o = uc_opp(e)[1]
            if o and g.get('opp_slug'):
                sr2tid.setdefault(g['opp_slug'], str(o['id']))
tid2sr = {v: k for k, v in sr2tid.items()}

# ───────────────────────── Team registry ─────────────────────────
TEAMS = {}  # key → {key,name,abbr,logo,color}


def team_for_sr(slug, name):
    if slug in TEAMS:
        return TEAMS[slug]
    tid = sr2tid.get(slug) or tid_for_name(name)
    et = teams_by_id.get(tid or '', {})
    disp = et.get('name') or re.sub(r'\s*\((NY|FL|CA|OH|PA|MD|IL|IN)\)$', '', name or slug)
    TEAMS[slug] = {'key': slug, 'name': disp, 'abbr': et.get('abbr') or (name or '')[:4].upper(), 'logo': et.get('logo') or (f'https://a.espncdn.com/i/teamlogos/ncaa/500/{tid}.png' if tid else None), 'color': et.get('color')}
    return TEAMS[slug]


def team_for_espn(t):
    tid = str(t.get('id'))
    slug = tid2sr.get(tid)
    if not slug:
        # an opponent we have never met in SR data: name-match SR slugs we know, else ESPN-keyed
        slug = f'e{tid}'
    if slug in TEAMS:
        return TEAMS[slug]
    et = teams_by_id.get(tid, {})
    TEAMS[slug] = {'key': slug, 'name': et.get('name') or t.get('location') or t.get('shortName') or t.get('name'), 'abbr': t.get('abbr') or et.get('abbr'),
                   'logo': t.get('logo') or et.get('logo'), 'color': t.get('color') or et.get('color')}
    return TEAMS[slug]


def opp_ref(team, rank=None, seed=None):
    r = {'key': team['key'], 'name': team['name'], 'abbr': team.get('abbr'), 'logo': team.get('logo')}
    if rank:
        r['rank'] = rank
    if seed:
        r['seed'] = seed
    return r


# ───────────────────────── Player identity ─────────────────────────
# SR id is canonical. ESPN athlete ids map to SR ids by name within the same season.
roster_names = collections.defaultdict(dict)  # year → norm name → sr_id
for y, s in sr_seasons.items():
    for r in s.get('roster', []):
        if r.get('sr_id'):
            roster_names[y][norm(r['player'])] = r['sr_id']
    for r in s.get('stats', {}).get('per_game', []):
        if r.get('sr_id'):
            roster_names[y].setdefault(norm(r['name_display']), r['sr_id'])
espn2sr = {}


def pid_for_espn(aid, name, y):
    if aid and aid in espn2sr:
        return espn2sr[aid]
    k = norm(name)
    last = k.split(' ')[-1] if k else ''
    pid = None
    # same season first, then neighbours (transfers, a season SR hasn't posted yet)
    for yy in (y, y - 1, y + 1, y - 2, y + 2):
        names = roster_names.get(yy, {})
        pid = names.get(k)
        if not pid:
            hits = [v for n, v in names.items() if n.split(' ')[-1] == last and n[:1] == k[:1]]
            pid = hits[0] if len(hits) == 1 else None
        if pid:
            break
    if pid and aid:
        espn2sr[aid] = pid
    return pid or (f'espn-{aid}' if aid else None)


# ───────────────────────── Player photos ─────────────────────────
# Every source adds candidates; the best rank wins:
#   0 Jason's drop folder (restored real photos) · 1 ESPN college headshot (cutout, UConn uniform)
#   2 UConn-era portrait · 3 UConn-era action/team shot · 4 NBA/pro headshot · 5 other pro/later photo · 6 Sports-Reference thumb
PHOTO_CANDS = collections.defaultdict(list)   # pid → [(rank, url, wide, meta)]


def add_photo(pid, rank, url, wide, **meta):
    if pid and url:
        PHOTO_CANDS[pid].append((rank, url, wide, {k: v for k, v in meta.items() if v}))


for aid, a in athletes.items():
    if a.get('headshot'):
        pid = pid_for_espn(aid, a.get('name'), (a.get('seasons') or [0])[-1])
        add_photo(pid, 1, a['headshot'], False, credit='ESPN', kind='headshot')
# Current-roster headshots also cover returning players' earlier seasons (e.g. "Solo" vs "Solomon" Ball)
for r in (espn_current.get('roster') or []):
    if r.get('headshot'):
        for yy in (r.get('priorSeasons') or []):
            pid = pid_for_espn(str(r.get('id')), r.get('name'), yy)
            if pid and not pid.startswith('espn-'):
                add_photo(pid, 1, r['headshot'], False, credit='ESPN', kind='headshot')
                break

known_pids = {pid for yy in roster_names for pid in roster_names[yy].values()}
name_to_pid_all = {n: pid for yy in roster_names for n, pid in roster_names[yy].items()}

# Jason's photo drop
DROP = os.path.join(HERE, '..', 'photos-drop')
ASSETS = os.path.join(HERE, '..', 'site', 'assets', 'players')
os.makedirs(ASSETS, exist_ok=True)
drop_credit = {}
if os.path.exists(os.path.join(DROP, 'credits.txt')):
    for line in open(os.path.join(DROP, 'credits.txt')).read().splitlines():
        if '|' in line:
            k, *rest = [x.strip() for x in line.split('|')]
            drop_credit[name_to_pid_all.get(norm(k), k)] = ' · '.join(rest)
skip_drop = set()
if os.path.exists(os.path.join(DROP, '_skip.txt')):
    for line in open(os.path.join(DROP, '_skip.txt')).read().splitlines():
        if line.strip() and not line.startswith('#'):
            skip_drop.add(line.split('|')[0].strip())
# match names loosely: "Khalid El Amin" = "Khalid El-Amin", "Johnny Selvie" = "Johnnie Selvie", case and accents ignored
compact = lambda n: re.sub(r'[^a-z]', '', norm(n))
compact_to_pid = {compact(n): pid for n, pid in name_to_pid_all.items()}
NICK = {'johnny': 'johnnie', 'johnnie': 'johnny', 'mike': 'michael', 'chris': 'christopher', 'cliff': 'clifford', 'rip': 'richard', 'tony': 'anthony', 'rob': 'robert', 'jim': 'james'}


def drop_pid(stem):
    if stem in known_pids:
        return stem
    pid = name_to_pid_all.get(norm(stem)) or compact_to_pid.get(compact(stem))
    if pid:
        return pid
    first, _, rest = norm(stem).partition(' ')
    if first in NICK:
        pid = compact_to_pid.get(compact(NICK[first] + ' ' + rest))
        if pid:
            return pid
    # forgive small typos ("Donyell Beverly" → Donnell Beverly): same last name, close first name, only one such player
    import difflib
    k = norm(stem)
    last = k.split(' ')[-1] if k else ''
    close = {pid_ for n, pid_ in name_to_pid_all.items()
             if n.split(' ')[-1] == last and difflib.SequenceMatcher(None, n, k).ratio() >= .8}
    if len(close) == 1:
        pid = close.pop()
        print(f'photos-drop: treating "{stem}" as {pid} (closest name)')
        return pid
    return None


dropped_hashes = {}
SRC_MAP = os.path.join(ASSETS, '_sources.json')   # pid → md5 of the file Jason dropped, so a replaced photo is always re-converted
src_md5 = jload(SRC_MAP, {}) or {}


def date_added(path):
    """When the file landed in the folder (Finder keeps a copied file's old modified date, so that can't be trusted)."""
    try:
        import subprocess
        out = subprocess.run(['mdls', '-raw', '-name', 'kMDItemDateAdded', path], capture_output=True, text=True).stdout.strip()
        if out and out != '(null)':
            return out
    except Exception:
        pass
    st = os.stat(path)
    return datetime.datetime.fromtimestamp(getattr(st, 'st_birthtime', st.st_mtime)).isoformat()


if os.path.isdir(DROP):
    import shutil, subprocess
    per_pid = collections.defaultdict(list)
    for fn in sorted(os.listdir(DROP)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.tif', '.tiff') or fn in skip_drop:
            continue
        pid = drop_pid(stem)
        if not pid:
            print(f'! photos-drop: no player matches "{fn}"')
            continue
        per_pid[pid].append(fn)
    for pid, fns in per_pid.items():
        fn = max(fns, key=lambda f: date_added(os.path.join(DROP, f)))   # newest arrival wins
        if len(fns) > 1:
            print(f'photos-drop: {pid} has {len(fns)} files; using the most recently added "{fn}"')
        src = os.path.join(DROP, fn)
        digest = hashlib.md5(open(src, 'rb').read()).hexdigest()
        dst = os.path.join(ASSETS, f'{pid}.jpg')
        if src_md5.get(pid) != digest or not os.path.exists(dst):
            if shutil.which('sips'):
                subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '85', '-Z', '900', src, '--out', dst], check=True, capture_output=True)
            else:
                shutil.copy(src, dst)
            src_md5[pid] = digest
            print(f'photos-drop: {fn} → {pid}')
    json.dump(src_md5, open(SRC_MAP, 'w'), indent=1, sort_keys=True)
# Small thumbnails of Jason's photos for the home-page wall (kept in sync with site/assets/players)
import subprocess as _sp
WALL = os.path.join(HERE, '..', 'site', 'assets', 'wall')
os.makedirs(WALL, exist_ok=True)
_have = set()
for fn in os.listdir(ASSETS):
    if not fn.endswith('.jpg'):
        continue
    _have.add(fn)
    src, dst = os.path.join(ASSETS, fn), os.path.join(WALL, fn)
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        _sp.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '60', '-Z', '300', src, '--out', dst], check=True, capture_output=True)
for fn in os.listdir(WALL):
    if fn not in _have:
        os.remove(os.path.join(WALL, fn))
for fn in os.listdir(ASSETS):
    if not fn.endswith('.jpg'):
        continue
    pid = os.path.splitext(fn)[0]
    ver = hashlib.md5(open(os.path.join(ASSETS, fn), 'rb').read()).hexdigest()[:8]  # new photo → new URL, so browsers never show a stale one
    add_photo(pid, 0, f'assets/players/{fn}?v={ver}', True, credit=drop_credit.get(pid) or 'Archival photo, restored', kind='restored')

# Photo agent: UConn-era portraits/action shots, pro headshots
RANK_KIND = {'uconn-headshot': 2, 'uconn-action': 3, 'uconn-team': 3, 'nba-headshot': 4, 'pro-other': 5, 'other': 5}
_pp = dict(((jload(os.path.join(M, 'player_photos.json'), {}) or {}).get('players') or {}))
# Perno-era finds (1977-86): listed best-first by a researcher who looked at every image; UConn-era shots beat later pro photos
for _k, _v in ((jload(os.path.join(M, 'player_photos_perno.json'), {}) or {}).get('players') or {}).items():
    for _i, _ph in enumerate(_v or []):
        if _ph.get('url'):
            add_photo(_k, 1.8 + _i * 0.01, _ph['url'], not _ph.get('cutout'), credit=_ph.get('credit'), license=_ph.get('license'),
                      source=_ph.get('source'), caption=_ph.get('caption'), kind=_ph.get('kind'), crop=_ph.get('crop'))
for pid, lst in _pp.items():
    for ph in lst or []:
        if ph.get('url'):
            add_photo(pid, RANK_KIND.get(ph.get('kind'), 5), ph['url'], not ph.get('cutout'), credit=ph.get('credit'), license=ph.get('license'),
                      source=ph.get('source'), caption=ph.get('caption'), kind=ph.get('kind'), crop=ph.get('crop'))

wiki_players = []
if isinstance(media_images, dict):
    wiki_players = media_images.get('players', [])
all_sr_names = {}
for y in roster_names:
    for n, pid in roster_names[y].items():
        all_sr_names.setdefault(n, pid)
wiki_by_pid = {}
for w in wiki_players:
    pid = all_sr_names.get(norm(w.get('player_name', '')))
    if pid:
        prev = wiki_by_pid.get(pid)
        if not prev or (w.get('context') == 'uconn' and prev.get('context') != 'uconn'):
            wiki_by_pid[pid] = w
for pid, w in wiki_by_pid.items():
    add_photo(pid, 3 if w.get('context') == 'uconn' else 5, w.get('thumb_url') or w.get('image_url'), True,
              credit=w.get('author'), license=w.get('license'), source=w.get('file_page'), kind='commons')
for pid, sp in sr_players.items():
    if sp and sp.get('photo_url'):
        add_photo(pid, 6, sp['photo_url'], True, credit='Sports-Reference', source=sp.get('url'), kind='sr')

# Photos on big CDNs are hotlinked; anything else (archives, blogs, listings) is copied locally once so it can't vanish or rate-limit
STABLE_HOSTS = ('a.espncdn.com', 'images.sidearmdev.com', 'upload.wikimedia.org', 'thumb.wikimedia.org', 'dxbhsrqyrr690.cloudfront.net')
REMOTE_DIR = os.path.join(HERE, '..', 'site', 'assets', 'players-remote')
os.makedirs(REMOTE_DIR, exist_ok=True)
_localize_memo = {}


def localize(url, crop=None, force=False):
    """copy a photo from a non-CDN host into site/assets/players-remote/; crop = {x, y, w, h} in source pixels (team photos);
    force = copy even from a CDN (small images shown everywhere, e.g. the coaches on the home page)"""
    if not url or url.startswith('assets/') or (urllib.parse.urlparse(url).netloc in STABLE_HOSTS and not crop and not force):
        return url
    mkey = (url, json.dumps(crop, sort_keys=True) if crop else None)
    if mkey in _localize_memo:
        return _localize_memo[mkey]
    import subprocess, time as _t
    key = hashlib.sha1((url + (mkey[1] or '')).encode()).hexdigest()[:14]
    for ext in ('.png', '.jpg'):
        if os.path.exists(os.path.join(REMOTE_DIR, key + ext)):
            _localize_memo[mkey] = f'assets/players-remote/{key}{ext}'
            return _localize_memo[mkey]
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36'})
        r = urllib.request.urlopen(req, timeout=25)
        ct = r.headers.get('Content-Type', '')
        data = r.read()
        if not ct.startswith('image') or len(data) < 1500:
            raise ValueError(f'not an image ({ct}, {len(data)} bytes)')
        ext = '.png' if 'png' in ct else '.jpg'
        tmp = os.path.join(REMOTE_DIR, key + '.src')
        open(tmp, 'wb').write(data)
        out = os.path.join(REMOTE_DIR, key + ext)
        fmt = 'png' if ext == '.png' else 'jpeg'
        if crop:   # sips: -c height width, --cropOffset y x
            cut = tmp + '.crop'
            subprocess.run(['sips', '-c', str(int(crop['h'])), str(int(crop['w'])), '--cropOffset', str(int(crop['y'])), str(int(crop['x'])), tmp, '--out', cut], check=True, capture_output=True)
            os.replace(cut, tmp)
        subprocess.run(['sips', '-s', 'format', fmt, '-Z', '700', tmp, '--out', out], check=True, capture_output=True)
        os.remove(tmp)
        _t.sleep(1.2 if 'archive.org' in url else 0.3)
        _localize_memo[mkey] = f'assets/players-remote/{key}{ext}'
    except Exception as e:
        print(f'! photo not reachable, trying next source: {url[:90]} ({e})')
        _localize_memo[mkey] = None
    return _localize_memo[mkey]


LOGO_ONLY = set((_rej.get('logo_only') or {}).keys())   # Jason asked for the Husky logo instead of any found photo
photo_for, photo_wide, photo_meta = {}, set(), {}
for pid, cands in PHOTO_CANDS.items():
    if pid in LOGO_ONLY:
        continue
    for rank, url, wide, meta in sorted(cands, key=lambda c: c[0]):
        u2 = localize(url, meta.get('crop') if isinstance(meta.get('crop'), dict) else None)
        if not u2 or (u2.startswith('assets/') and hashlib.md5(open(os.path.join(SITE, '..', u2.split('?')[0]), 'rb').read()).hexdigest() in REJECT_HASHES):
            continue
        photo_for[pid] = u2
        photo_meta[pid] = meta
        if wide:
            photo_wide.add(pid)
        break


CROP_POS = {'left-third': '22% 18%', 'left': '28% 18%', 'center': '50% 18%', 'right': '72% 18%', 'right-third': '78% 18%', 'top': '50% 0%'}


def photo_studio(pid):
    return (photo_meta.get(pid) or {}).get('kind') in ('headshot', 'uconn-headshot') or None


def photo_pos(pid):
    c = (photo_meta.get(pid) or {}).get('crop')
    return CROP_POS.get(c) if isinstance(c, str) else None   # a dict crop is already cut out of the source image


# ───────────────────────── Commons photos ─────────────────────────
COMMONS = []
if isinstance(media_images, dict):
    for ph in media_images.get('photos', []) or []:
        url = ph.get('image_url') or ph.get('url')
        if not url or ph.get('context') not in (None, 'uconn'):
            continue
        d0 = ' '.join([ph.get('description') or '', ph.get('file') or ''])
        blob = d0 + ' ' + ' '.join(ph.get('categories') or [])
        if re.search(r"taurasi|auriemma|rebecca lobo|breanna|stewie|bueckers|wnba|lady huskies|softball|hockey|baseball|soccer|volleyball", blob, re.I):
            continue
        if re.search(r"women", blob, re.I) and not re.search(r"(?<!wo)men's", d0, re.I):
            continue
        desc = ph.get('description') or ''
        if re.fullmatch(r'[\w\-. ]{0,24}', desc or ''):  # camera filenames like "10002-3-XL" say nothing
            gm = ph.get('game') or {}
            desc = f"UConn vs. {gm['opponent']}, {gm.get('date')}" if gm.get('opponent') else (ph.get('file') or '').replace('File:', '').rsplit('.', 1)[0]
        COMMONS.append({'url': url, 'thumb': ph.get('thumb_url') or url, 'caption': desc, 'credit': ph.get('author'), 'license': ph.get('license'),
                        'page': ph.get('file_page'), 'w': ph.get('width'), 'h': ph.get('height'), 'season': ph.get('season'), 'date': (ph.get('game') or {}).get('date') or (ph.get('date') or '')[:10],
                        'subjects': ph.get('subjects') or [], 'kind': ph.get('kind')})
COMMONS_BY_SEASON = collections.defaultdict(list)
for ph in COMMONS:
    if ph.get('season'):
        COMMONS_BY_SEASON[int(ph['season'])].append(ph)


# ───────────────────────── Videos ─────────────────────────
VIDS = []
_extra = []
for _fn in ('videos_extra.json', 'videos_perno.json'):
    _x = jload(os.path.join(M, _fn), {}) or {}
    _extra += list(_x.get('videos', _x) if isinstance(_x, dict) else _x)
_vled = {}
for it in (jload(os.path.join(M, 'verify_videos.json'), {}) or {}).get('items', []):
    _vled.setdefault(it.get('id'), []).append(it)
for v in list(media_videos or []) + list(_extra or []):
    if isinstance(v, dict) and v.get('verify'):
        continue  # researcher wasn't sure it's the right game: leave it out until checked
    if isinstance(v, dict) and v.get('id') in _vled:
        fixes = _vled[v['id']]
        if any(f.get('status') == 'REMOVE' for f in fixes):
            continue
        v = dict(v)
        for f in fixes:
            if f.get('status') == 'FIX' and f.get('field'):
                v[f['field']] = f.get('new')
    if not isinstance(v, dict) or not v.get('id'):
        continue
    kind_ = {'full-game': 'full_game', 'feature': 'documentary'}.get(v.get('kind'), v.get('kind'))
    if re.search(r'\bWHUS\b|radio broadcast|audio only', v.get('description') or '', re.I):
        kind_ = 'radio'   # student-radio calls (audio only) are not game video
    VIDS.append({k: v_ for k, v_ in {**{k: v.get(k) for k in ('id', 'title', 'channel', 'season', 'date', 'opponent', 'round', 'players', 'description')}, 'kind': kind_}.items() if v_ is not None})
seen = set()
VIDS = [v for v in VIDS if not (v['id'] in seen or seen.add(v['id']))]
for v in VIDS:
    try:
        v['season'] = int(v['season']) if v.get('season') else None
    except (TypeError, ValueError):
        v['season'] = None
    if not v.get('season') and v.get('date'):
        d = v['date'][:10]
        yy, mm = int(d[:4]), int(d[5:7])
        v['season'] = yy + 1 if mm >= 7 else yy
    v['sub'] = ' · '.join(str(x) for x in [v.get('round'), v.get('channel')] if x)
    v['featured'] = bool(v.get('kind') in ('moment', 'highlights', 'full_game') and (v.get('round') and re.search(r'final|championship|elite|regional', str(v.get('round')), re.I)))


def vids_for_game(y, date, opp_name):
    out = []
    on = norm(opp_name)
    for v in VIDS:
        if v.get('season') != y:
            continue
        vd = (v.get('date') or '')[:10]
        vo = norm(v.get('opponent') or '')
        if (vd and vd == date) or (vo and on and (vo in on or on in vo) and not vd):
            out.append(v)
    return out


# ───────────────────────── Box score normalizers ─────────────────────────
STATMAP = {'Field Goal %': 'fg_pct', 'Three Point %': 'tp_pct', 'Free Throw %': 'ft_pct', 'Rebounds': 'reb', 'Offensive Rebounds': 'oreb', 'Assists': 'ast',
           'Steals': 'stl', 'Blocks': 'blk', 'Total Turnovers': 'to', 'Points in Paint': 'paint', 'Fast Break Points': 'fast', 'Points Off Turnovers': 'pot', 'Largest Lead': 'lead', 'Fouls': 'pf'}


def espn_team_block(t, y, is_uc, sr_row=None):
    stats = {}
    for k, v in (t.get('stats') or {}).items():
        if k in STATMAP and num(v) is not None:
            stats[STATMAP[k]] = num(v)
    if 'to' not in stats and num((t.get('stats') or {}).get('Turnovers')) is not None:
        stats['to'] = num(t['stats']['Turnovers'])
    players = []
    for p in t.get('players') or []:
        q = {k: p.get(k) for k in ('name', 'pos', 'starter', 'dnp', 'min', 'pts', 'fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'oreb', 'dreb', 'reb', 'ast', 'stl', 'blk', 'to', 'pf')}
        q['num'] = p.get('jersey')
        if is_uc:
            pid = pid_for_espn(str(p.get('id')), p.get('name'), y)
            q['pid'] = pid
            q['photo'] = photo_for.get(pid) or p.get('headshot')
        else:
            q['photo'] = p.get('headshot')
        players.append({k: v for k, v in q.items() if v is not None and v != ''})
    bench = sum((p.get('pts') or 0) for p in players if not p.get('starter'))
    if players:
        stats['bench'] = bench
    team = team_for_espn(t) if not is_uc else {'name': 'UConn', 'abbr': 'CONN', 'logo': 'https://a.espncdn.com/i/teamlogos/ncaa/500/41.png', 'color': '0c2340'}
    return {'name': team['name'], 'abbr': team.get('abbr'), 'logo': team.get('logo'), 'color': team.get('color'), 'rank': t.get('rank') if t.get('rank') and t.get('rank') < 99 else None,
            'record': t.get('record'), 'score': num(t.get('score')), 'line': [num(x) for x in (t.get('linescores') or [])], 'stats': stats, 'players': players}


def sr_team_block(t, is_uc, opp_team=None):
    players = []
    for p in t.get('players') or []:
        q = {'name': p.get('player'), 'starter': p.get('starter'), 'min': p.get('mp'), 'pts': p.get('pts'), 'fgm': p.get('fg'), 'fga': p.get('fga'), 'tpm': p.get('fg3'), 'tpa': p.get('fg3a'),
             'ftm': p.get('ft'), 'fta': p.get('fta'), 'oreb': p.get('orb'), 'dreb': p.get('drb'), 'reb': p.get('trb'), 'ast': p.get('ast'), 'stl': p.get('stl'), 'blk': p.get('blk'), 'to': p.get('tov'), 'pf': p.get('pf')}
        if is_uc and p.get('sr_id'):
            q['pid'] = p['sr_id']
            q['photo'] = photo_for.get(p['sr_id'])
        players.append({k: v for k, v in q.items() if v is not None})
    tot = t.get('totals') or {}
    pc = lambda m, a: round(100 * tot[m] / tot[a], 1) if tot.get(a) else None
    stats = {k: v for k, v in {'fg_pct': pc('fg', 'fga'), 'tp_pct': pc('fg3', 'fg3a'), 'ft_pct': pc('ft', 'fta'), 'reb': tot.get('trb'), 'oreb': tot.get('orb'), 'ast': tot.get('ast'),
                                'stl': tot.get('stl'), 'blk': tot.get('blk'), 'to': tot.get('tov'), 'pf': tot.get('pf')}.items() if v is not None}
    if players and any('starter' in p for p in players):
        stats['bench'] = sum(p.get('pts') or 0 for p in players if not p.get('starter'))
    base = {'name': 'UConn', 'abbr': 'CONN', 'logo': 'https://a.espncdn.com/i/teamlogos/ncaa/500/41.png'} if is_uc else opp_team
    return {'name': base['name'], 'abbr': base.get('abbr'), 'logo': base.get('logo'), 'score': num(t.get('score')),
            'line': [num(x.get('pts')) for x in (t.get('linescore') or [])], 'stats': stats, 'players': players}


def plays_for(e, uc_home):
    fields = e.get('playFields') or []
    ix = {f: i for i, f in enumerate(fields)}
    rows = []
    for p in e.get('plays') or []:
        g = lambda k: p[ix[k]] if k in ix and ix[k] < len(p) else None
        team = str(g('teamId')) if g('teamId') else None
        side = 'u' if team == UCONN_ESPN else ('o' if team else None)
        a, h = num(g('awayScore')) or 0, num(g('homeScore')) or 0
        us, os_ = (h, a) if uc_home else (a, h)
        x = y = None
        if g('shootingPlay') and g('x') is not None and g('y') is not None and not re.search(r'free throw', g('text') or '', re.I):
            x, y = num(g('x')), num(g('y'))
            if not (x == 25 and y == 0):
                y = round(y + 5.25, 2)  # ESPN y is feet from the rim; court y is feet from the baseline
            else:
                x = y = None
        rows.append([num(g('period')), g('clock'), side, us, os_, 1 if g('scoringPlay') else 0, num(g('scoreValue')) or 0, g('text') or '', x, y])
    wp = []
    for w in e.get('wp') or []:
        if isinstance(w, (list, tuple)) and len(w) >= 2 and w[1] is not None:
            hp = float(w[1])
            wp.append([w[0], round(hp if uc_home else 1 - hp, 4)])
    return rows, wp


CLIP_ACT = [('made', ('made', 'makes')), ('missed', ('missed', 'misses')), ('block', ('block',)), ('steal', ('steal',)), ('turnover', ('turnover',)),
            ('foul', ('foul',)), ('rebound', ('rebound',))]


def clip_index(e, rows):
    """Match ESPN per-play clips ("1H (15:36) ..." / headline "2H CONN J. Adams made Jumper.") to play rows.
    Several plays often share one clock second (a block and its rebound), so a clip goes to the play, within 4 seconds,
    whose player is named in the clip's headline, preferring the same action and the closest clock.
    No confident match = no clip: a wrong clip is worse than none."""
    out = {}
    secs = lambda c: int(c.split(':')[0]) * 60 + int(c.split(':')[1].split('.')[0])

    def player(t):
        m = re.match(r"^\s*(?:Foul on\s+)?([A-Z][\w.'\-]*(?:\s+[A-Z][\w.'\-]*){0,3})\s+(?:made|missed|makes|misses|Block|Steal|Turnover|Offensive|Defensive|Foul|Jumpball|blocked|Technical|\.)", t or '')
        if not m and (t or '').startswith('Foul on '):
            m = re.match(r'^Foul on\s+(.+?)\.?$', t)
        return re.sub(r'[^a-z\- ]', '', m.group(1).lower()).split()[-1] if m else None

    for v in e.get('videos') or []:
        m = re.match(r'\s*(\d)H \((\d+:\d\d)\)|\s*OT(\d?) \((\d+:\d\d)\)', v.get('description') or '')
        if not m or not (v.get('links') or {}).get('mp4'):
            continue
        per = int(m.group(1)) if m.group(1) else 2 + int(m.group(3) or 1)
        clk = secs(m.group(2) or m.group(4))
        title = v.get('headline') or ''
        tl = title.lower()
        act = next((alts for k, alts in CLIP_ACT if k in tl), None)
        cands = sorted((i for i, r in enumerate(rows) if r[0] == per and r[1] and abs(secs(r[1]) - clk) <= 4), key=lambda i: abs(secs(rows[i][1]) - clk))
        named = [i for i in cands if (lambda n: n and len(n) >= 3 and re.search(r'\b' + re.escape(n) + r'\b', tl))(player(rows[i][7]))]
        both = [i for i in named if act and any(a in (rows[i][7] or '').lower() for a in act)]
        pool = both if act else named   # when the headline names an action, the play must show that action too
        hit = pool[0] if pool else None
        if hit is not None and hit not in out:
            out[hit] = {'src': v['links']['mp4'], 'thumb': v.get('thumbnail'), 'title': re.sub(r'^\s*(?:\dH|OT\d?)\s+[A-Z]{2,5}\s+', '', title)}
    return out


def espn_videos(e):
    out = []
    for v in e.get('videos') or []:
        if re.match(r'\s*(\d)H \(|\s*OT\d? \(', v.get('description') or ''):
            continue  # per-play clips live in the play-by-play
        mp4 = (v.get('links') or {}).get('mp4')
        if not mp4:
            continue
        out.append({'id': f"espn{v.get('id')}", 'title': v.get('headline'), 'kind': 'espn', 'src': mp4, 'thumb': v.get('thumbnail'), 'web': (v.get('links') or {}).get('web'), 'sub': 'ESPN'})
    return out


# ───────────────────────── Seasons ─────────────────────────
def round_label(g, r):
    reg = re.match(r'(\w+) (?:First|Second|Third|Regional)', g.get('round') or '')
    base = ROUND_NAMES[r] if 0 <= r < 6 else (g.get('round') or 'NCAA Tournament')
    return f"NCAA {base}{' · ' + reg.group(1) if reg and r <= 3 else ''}"


def ncaa_round(name, y, order):
    """0 = round of 64 (or first round), 1 = round of 32 ... 5 = title game, from the official round name.
    Early brackets gave byes (1979: UConn's first game was a second-round game); 2011-15 called the round of 64
    the "second round" and the round of 32 the "third round" (First Four era naming)."""
    n = (name or '').lower()
    if 'national final' in n or 'championship' in n:
        return 5
    if 'national semifinal' in n or 'final four' in n:
        return 4
    if 'regional final' in n:
        return 3
    if 'regional semifinal' in n:
        return 2
    first_four_era = 2011 <= y <= 2015
    if 'third round' in n:
        return 1
    if 'second round' in n:
        return 0 if first_four_era else 1
    if 'first round' in n:
        return 0
    return order


def finish_for(games):
    ncaa = [g for g in games if g['type'] == 'NCAA' and g.get('res')]
    if ncaa:
        last = ncaa[-1]
        r = last.get('r', len(ncaa) - 1)
        if r == 5:
            return 'champ' if last['res'] == 'W' else 'runner'
        return ['r64', 'r32', 'sweet16', 'elite8', 'final4'][r] if last['res'] == 'L' else ['r64', 'r32', 'sweet16', 'elite8', 'final4'][r]
    if any(g['type'] == 'NIT' for g in games):
        return 'nit'
    return 'none'


PLAYER_SEASONS = collections.defaultdict(list)   # pid → [season rows]
SEASON_PHOTOS = collections.defaultdict(list)    # year → ESPN game-story photos (credited, hotlinked)
EXHIBITIONS = {}                                   # year → exhibition games (never counted in records)
SEEN_PHOTOS = set()
PLAYER_GAMES = collections.defaultdict(list)     # pid → [game log rows]
SEASON_SUM = []
GAMES_INDEX = []
MARCH = []
os.makedirs(os.path.join(SITE, 'plays'), exist_ok=True)

years = sorted(set(sr_seasons) | set(espn_sched))
years = [y for y in years if y >= FIRST]
current_season = max(years)


def conf_short(c):
    return {'Big East': 'Big East', 'American Athletic Conference': 'AAC', 'AAC': 'AAC', 'The American': 'AAC', 'Big East MBB': 'Big East'}.get(c, c)


def espn_only_games(y):
    sched = espn_sched.get(y) or {}
    out = []
    for i, e0 in enumerate(sorted(sched.get('games', []), key=lambda x: x['date'])):
        e = espn_games.get(str(e0['id'])) or {}
        u, o = uc_opp(e) if e else (None, None)
        opp_t = team_for_espn(o) if o else team_for_espn({'id': e0.get('oppId') or (e0.get('opponent') or {}).get('id'), 'location': (e0.get('opponent') or {}).get('name'), 'abbr': (e0.get('opponent') or {}).get('abbr'), 'logo': (e0.get('opponent') or {}).get('logo')})
        ha = 'N' if e0.get('neutral') or e.get('neutral') else ('H' if (e0.get('homeAway') or (u or {}).get('homeAway')) == 'home' else 'A')
        note = e0.get('note') or e.get('note') or ''
        typ = 'NCAA' if re.search(r"Men's Basketball Championship|NCAA", note, re.I) else 'CTOURN' if re.search(r'tournament|championship', note, re.I) else 'NIT' if 'NIT' in note else 'REG'
        final = (e.get('status') or e0.get('status')) == 'final'
        g = {'g': i + 1, 'date': et_date(e0['date']), 'iso': e0['date'], 'type': typ, 'ha': ha, 'opp': opp_t, 'opp_rank': (o or {}).get('rank') if o and (o.get('rank') or 99) < 99 else (e0.get('opponent') or {}).get('rank'),
             'arena': (e.get('venue') or {}).get('name') or (e0.get('venue') or {}).get('name') if isinstance(e0.get('venue'), dict) else e0.get('venue'), 'round': note or None, 'espn': e or None,
             'tv': ', '.join(e.get('broadcasts') or []) or e0.get('broadcast') or None, 'timeTBD': e0.get('timeTBD') or e.get('timeTBD'), 'eid': str(e0['id'])}
        if final and u and o:
            g.update({'res': 'W' if num(u['score']) > num(o['score']) else 'L', 'pts': num(u['score']), 'opp_pts': num(o['score']), 'ot': (f"{e.get('ot')}OT" if (e.get('ot') or 0) > 1 else 'OT') if e.get('ot') else None})
        out.append(g)
    # Official UConn schedule details (tip times, TV, venue, event) beat ESPN's placeholders
    offs = (jload(os.path.join(M, 'verify_current.json'), {}) or {}).get('official_schedule') or [] if y == max(espn_sched) else []
    used_off = set()
    for g in out:
        on = norm(g['opp']['name'])
        o_ = next((o for i, o in enumerate(offs) if not o.get('exhibition') and o.get('date') == g['date'] and
                   (norm(o.get('opponent')) in on or on in norm(o.get('opponent')) or norm(o.get('opponent')).split(' ')[0] == on.split(' ')[0])), None)
        if not o_:
            continue
        used_off.add(id(o_))
        if o_.get('utc') and not g.get('res'):
            g['iso'] = o_['utc']
            g['timeTBD'] = False
        if o_.get('tv'):
            g['tv'] = o_['tv']
        if o_.get('venue'):
            g['arena'] = o_['venue']
            g['city'] = o_.get('city')
        if o_.get('event') and not g.get('round'):
            g['round'] = o_['event']
    EXHIBITIONS[y] = [{'date': o['date'], 'iso': o.get('utc'), 'opp': o.get('opponent'), 'ha': o.get('site'), 'arena': ', '.join(x for x in [o.get('venue'), o.get('city')] if x),
                       'tv': o.get('tv'), 'event': o.get('event'), 'time': o.get('local_time')} for o in offs if o.get('exhibition')]
    w = 0
    l = 0
    for g in out:
        if g.get('res') == 'W':
            w += 1
        elif g.get('res') == 'L':
            l += 1
        if g.get('res'):
            g['rec'] = f'{w}-{l}'
    return out


for y in years:
    s = sr_seasons.get(y)
    meta = (s or {}).get('meta', {})
    si = school_index.get(label(y).replace('–', '-'), {})
    games_out = []
    details = {}
    raw_games = []
    if s:
        for g in s.get('schedule', []):
            opp_t = team_for_sr(g.get('opp_slug') or norm(g.get('opp_name')), g.get('opp_name'))
            raw_games.append({'g': g['g'], 'date': g['date'], 'iso': None, 'type': g.get('game_type') or 'REG', 'ha': {'home': 'H', 'away': 'A', 'neutral': 'N'}.get(g.get('site'), 'H' if not g.get('game_location') else ('A' if g['game_location'] == '@' else 'N')),
                              'opp': opp_t, 'opp_rank': g.get('opp_rank'), 'opp_seed': g.get('opp_seed'), 'arena': g.get('arena'), 'round': g.get('round'), 'res': g.get('game_result'),
                              'pts': g.get('pts'), 'opp_pts': g.get('opp_pts'), 'ot': g.get('overtimes'), 'rec': f"{g.get('wins')}-{g.get('losses')}" if g.get('wins') is not None else None,
                              'espn': sr_game_espn.get((y, g['g'])), 'box_slug': g.get('box_slug'), 'forfeit': g.get('forfeit'), 'arena_ok': g.get('arena_verified')})
    else:
        raw_games = espn_only_games(y)

    ncaa_i = 0
    ct_i = 0
    for g in raw_games:
        gid = f"{y}-{g['g']}"
        e = g.get('espn')
        opp = opp_ref(g['opp'], g.get('opp_rank'), g.get('opp_seed'))
        rnd = g.get('round')
        r_idx = None
        if g['type'] == 'NCAA':
            r_idx = ncaa_round(g.get('round'), y, ncaa_i)
            ncaa_i += 1
            rnd = round_label(g, r_idx)
        elif g['type'] == 'CTOURN' and not rnd and e and e.get('note'):
            rnd = e['note'].title().replace("Men'S", "Men's")
        elif g['type'] == 'NIT':
            rnd = rnd or 'NIT'
        if g['type'] == 'CTOURN':   # one clean label: the tournament UConn actually played in that year + the round when known
            rl_ = (rnd or '').lower()
            # ESPN abbreviates ("Qtrfinals", "Semis"), so "final" must be a whole word, and a conference final is always on a weekend
            stage_ = ('quarterfinal' if re.search(r'quarter|qtr', rl_) else 'semifinal' if 'semi' in rl_ else 'final' if re.search(r'\bfinals?\b', rl_) or 'championship game' in rl_
                      else 'first round' if re.search(r'\b(1st|first)\b', rl_) else 'second round' if re.search(r'\b(2nd|second)\b', rl_) else None)
            if stage_ == 'final' and datetime.date.fromisoformat(g['date'][:10]).weekday() < 5:
                print(f"  !! {gid}: '{rnd}' says final but {g['date'][:10]} is a weekday; round dropped")
                stage_ = None
            rnd = ('ECAC New England tournament' if y <= 1979 else 'AAC tournament' if 2014 <= y <= 2020 else 'Big East tournament') + (f' {stage_}' if stage_ else '')
        ha = g['ha']
        if g['type'] in ('NCAA', 'CTOURN'):
            ha = 'N'  # tournament games are neutral-site, even at MSG or in Hartford (sources disagree game to game)
        row = {'id': gid, 'date': (g.get('iso') or (e or {}).get('date') or g['date']) if not g.get('res') else g['date'], 'type': g['type'], 'ha': ha, 'opp': opp}
        for k in ('res', 'pts', 'opp_pts', 'ot', 'rec', 'arena', 'city', 'forfeit'):
            if g.get(k) is not None:
                row[k] = g[k]
        if row.get('arena'):
            row['arena'] = re.sub(r'\s*\((?:I|II|III|IV|V)\)$', '', row['arena'])   # Sports-Reference's "Madison Square Garden (IV)" = the current Garden
        if y < 2001 and g['type'] in ('REG', 'CTOURN') and not e and not g.get('arena_ok'):
            row.pop('arena', None)  # Sports-Reference arena names before ~2001 are unreliable (fact-check 2026-09-30)
        if rnd:
            row['round'] = rnd
        if r_idx is not None:
            row['r'] = r_idx
        if e and not row.get('arena') and (e.get('venue') or {}).get('name'):
            row['arena'] = e['venue']['name']
        if g.get('tv'):
            row['tv'] = g['tv'] if isinstance(g['tv'], str) else ', '.join(g['tv'])
        elif e and e.get('broadcasts'):
            row['tv'] = ', '.join(e['broadcasts'])
        if g.get('eid'):
            row['eid'] = g['eid']
        # ── detail
        det = None
        if e and e.get('teams') and any(pl.get('pts') is not None for t in e['teams'] for pl in (t.get('players') or [])):
            u, o = uc_opp(e)
            uc_home = (u or {}).get('homeAway') == 'home'
            U = espn_team_block(u, y, True)
            O = espn_team_block(o, y, False)
            # ESPN sometimes drops players from a box; if a team's players don't add up to its score, use Sports-Reference's box for that team
            sb = sr_boxes.get(g.get('box_slug') or '') if g.get('box_slug') else None
            if sb:
                for blk, is_uc in ((U, True), (O, False)):
                    if blk.get('score') is not None and sum((q.get('pts') or 0) for q in blk['players'] if not q.get('dnp')) != blk['score']:
                        st = next((t for t in sb.get('teams') or [] if (t.get('sr_slug') == 'connecticut') == is_uc), None)
                        if st and sum((q.get('pts') or 0) for q in st.get('players') or []) == blk['score']:
                            blk['players'] = sr_team_block(st, is_uc, g['opp'])['players']
                            blk['boxSource'] = 'sr'
            O.update({'name': g['opp']['name'], 'abbr': O.get('abbr') or g['opp'].get('abbr'), 'logo': O.get('logo') or g['opp'].get('logo')})
            if g.get('opp_seed'):
                O['seed'] = g['opp_seed']
            det = {'venue': {'name': (e.get('venue') or {}).get('name'), 'city': ', '.join(x for x in [(e.get('venue') or {}).get('city'), (e.get('venue') or {}).get('state')] if x)},
                   'att': e.get('attendance'), 'officials': e.get('officials') or [], 'tv': ', '.join(e.get('broadcasts') or []) or None, 'teams': [U, O],
                   'odds': e.get('odds'), 'espnId': e.get('id')}
            if e.get('article') and e['article'].get('story'):
                a = e['article']
                det['article'] = {'headline': a.get('headline'), 'story': a.get('story'), 'byline': a.get('source'),
                                  'images': [im for im in (a.get('images') or []) if im.get('url')][:3]}
            det['videos'] = espn_videos(e)
            for im in (e.get('article') or {}).get('images') or []:
                if im.get('url') and not re.search(r'/i/teamlogos/', im['url']) and im['url'] not in SEEN_PHOTOS:
                    SEEN_PHOTOS.add(im['url'])
                    SEASON_PHOTOS[y].append({'url': im['url'], 'thumb': im['url'], 'caption': im.get('caption') or f"UConn vs. {g['opp']['name']}, {g['date']}", 'credit': im.get('credit'),
                                             'w': im.get('width'), 'h': im.get('height'), 'gid': gid})
            if e.get('plays'):
                rows, wp = plays_for(e, uc_home)
                clips = clip_index(e, rows)
                fin_ = (row.get('pts'), row.get('opp_pts'))
                end_ = (rows[-1][3], rows[-1][4]) if rows else None
                if rows and fin_[0] is not None and end_ != fin_:
                    # ESPN's feed skips or garbles plays (or belongs to another game): a scoring chart that ends at the wrong score is wrong
                    det['pbpNote'] = f"ESPN's play-by-play for this game ends at {end_[0]}–{end_[1]}, not the {fin_[0]}–{fin_[1]} final, so it isn't shown."
                    PBP_DROPPED.append((gid, end_, fin_))
                    rows, clips = [], (type(clips)())
                pf_ = os.path.join(SITE, 'plays', f'{gid}.json')
                if rows or wp:
                    jdump(pf_, {'plays': rows, 'wp': wp, 'clips': clips})
                    det['hasPlays'] = True
                elif os.path.exists(pf_):
                    os.remove(pf_)
            row['box'] = 'espn'
        elif g.get('box_slug') and g['box_slug'] in sr_boxes and sr_boxes[g['box_slug']]:
            b = sr_boxes[g['box_slug']]
            ts = b.get('teams') or []
            ut = next((t for t in ts if t.get('sr_slug') == 'connecticut'), None)
            ot = next((t for t in ts if t.get('sr_slug') != 'connecticut'), None)
            if ut and ot:
                U = sr_team_block(ut, True)
                O = sr_team_block(ot, False, g['opp'])
                if g.get('opp_seed'):
                    O['seed'] = g['opp_seed']
                arena = b.get('arena') or ''
                det = {'venue': {'name': arena.split(',')[0] if arena else g.get('arena'), 'city': ', '.join(arena.split(',')[1:]).strip()}, 'att': b.get('attendance'),
                       'officials': b.get('officials') or [], 'teams': [U, O], 'source': 'sr'}
                row['box'] = 'sr'
        if not det and gid in NEWSPAPER_BOXES:
            det = newspaper_det(g, NEWSPAPER_BOXES[gid], opp)
            row['box'] = 'newspaper'
        if det:
            det['teams'][0]['rank'] = det['teams'][0].get('rank')
            det['teams'][1]['rank'] = det['teams'][1].get('rank') or g.get('opp_rank')
            vids = vids_for_game(y, g['date'], g['opp']['name'])
            det['videos'] = vids + det.get('videos', [])
            details[gid] = det
            ups = [p for p in det['teams'][0]['players'] if p.get('pts') is not None]
            if ups:
                top = max(ups, key=lambda p: (p.get('pts') or 0, p.get('reb') or 0))
                row['top'] = f"{top['name']} {top['pts']} pts" + (f", {top['reb']} reb" if (top.get('reb') or 0) >= 10 else '')
            # game logs
            sr_played = None
            sbx = sr_boxes.get(g.get('box_slug') or '') if g.get('box_slug') else None
            if sbx:
                ut_ = next((t for t in sbx.get('teams') or [] if t.get('sr_slug') == 'connecticut'), None)
                if ut_:
                    sr_played = {q.get('sr_id') for q in ut_.get('players') or []}  # SR lists only players who got in (even for seconds)
            for p in det['teams'][0]['players']:
                if not p.get('pid') or p.get('dnp'):
                    continue
                entry_ = None
                if sr_played is not None:
                    if p['pid'] not in sr_played and (gid, norm(p.get('name'))) not in FORCE_PLAYED:
                        EXCLUDED_APPEARANCES[(p['pid'], y)].append(gid)   # kept aside: the official games count may say he did get in
                        continue  # Sports-Reference's box (which decides games played) says he didn't get in

                PLAYER_GAMES[p['pid']].append({'id': gid, 'y': y, 'date': g['date'], 'opp': {k: opp[k] for k in ('name', 'abbr', 'logo') if opp.get(k)}, 'ha': ha, 'res': g.get('res'),
                                               'score': f"{g.get('pts')}-{g.get('opp_pts')}", 'type': g['type'], 'round': rnd, **{k: p.get(k) for k in ('min', 'pts', 'reb', 'ast', 'stl', 'blk', 'to', 'fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'oreb')}})
        else:
            vids = vids_for_game(y, g['date'], g['opp']['name'])
            if vids:
                row['videos'] = vids
        games_out.append(row)
        if row.get('res'):
            GAMES_INDEX.append({'id': gid, 'y': y, 'date': g['date'], 'type': g['type'], 'ha': ha, 'opp': {k: opp[k] for k in ('key', 'name', 'abbr', 'logo') if opp.get(k)},
                                'res': row['res'], 'pts': row['pts'], 'opp_pts': row['opp_pts'], 'ot': row.get('ot'), 'round': rnd if g['type'] in ('NCAA', 'NIT', 'CTOURN') else None,
                                'top': row.get('top'), 'big': 2 if g['type'] == 'NCAA' else 1 if g.get('opp_rank') else 0, **({'forfeit': True} if row.get('forfeit') else {})})

    # ── venues: era-correct names; single-source Sports-Reference labels before 2001 stay hidden (unreliable)
    for row in games_out:
        v = VENUE_ERA.get(row['id'])
        day = row['date'][:10] if row.get('res') else et_date(row['date'])
        if not row.get('res'):
            row['day'] = day
        if not v:
            continue
        try:
            if abs((datetime.date.fromisoformat(v['date']) - datetime.date.fromisoformat(day)).days) > 1:
                continue
        except (KeyError, ValueError, TypeError):
            continue
        if not v.get('era_name'):
            continue
        basis = v.get('basis') or ''
        if y < 2001 and basis.startswith('label->') and not v.get('espn_venue'):
            continue
        row['arena'] = v['era_name']
        if BUILDING_CITY.get(v.get('building_key')):
            row['city'] = BUILDING_CITY[v['building_key']]
        det = details.get(row['id'])
        if det is not None:
            det['venue'] = {'name': v['era_name'], 'city': BUILDING_CITY.get(v.get('building_key')) or (det.get('venue') or {}).get('city')}

    # ── stat corrections from official box scores
    for st in ADJ.get('stats', []):
        det = details.get(st.get('game'))
        if not det or int(st['game'].split('-')[0]) != y:
            continue
        if st.get('iona_box') or any(k.endswith('_box') for k in st):
            box = next(v for k, v in st.items() if k.endswith('_box'))
            spl = lambda x: [int(v) for v in str(x).split('-')] if x and '-' in str(x) else [None, None]
            det['teams'][1]['players'] = [{'name': b['player'], 'starter': b.get('gs'), 'min': b.get('min'), 'pts': b.get('pts'), 'fgm': spl(b.get('fg'))[0], 'fga': spl(b.get('fg'))[1],
                                           'tpm': spl(b.get('3pt'))[0], 'tpa': spl(b.get('3pt'))[1], 'ftm': spl(b.get('ft'))[0], 'fta': spl(b.get('ft'))[1], 'oreb': b.get('orb'), 'dreb': b.get('drb'),
                                           'reb': b.get('reb'), 'ast': b.get('ast'), 'stl': b.get('stl'), 'blk': b.get('blk'), 'to': b.get('to'), 'pf': b.get('pf')}
                                          for b in box if b.get('player') not in ('TEAM', 'Team', 'Totals', 'TOTALS')]
            det['teams'][1]['boxSource'] = 'official'
            continue
        pl = next((q for q in det['teams'][0]['players'] if norm(q.get('name')) == norm(st.get('player'))), None)
        if not pl or not str(st.get('truth', '')).split(' ')[0].isdigit():
            continue
        v_ = int(str(st['truth']).split(' ')[0])
        if st.get('stat') == 'rebounds':
            pl['reb'] = v_
            if pl.get('oreb') is not None:
                pl['dreb'] = v_ - pl['oreb']
        elif st.get('stat') == 'assists':
            pl['ast'] = v_
    # ── NCAA-vacated games: still shown (they happened), clearly marked
    vac = VACATED.get(y)
    if vac:
        for row in games_out:
            if row.get('res') and vac['test'](row):
                row['vacated'] = True

    # ── roster + stats
    roster = []
    pg = {r['sr_id']: r for r in (s or {}).get('stats', {}).get('per_game', []) if r.get('sr_id')}
    tot = {r['sr_id']: r for r in (s or {}).get('stats', {}).get('totals', []) if r.get('sr_id')}
    adv = {r['sr_id']: r for r in (s or {}).get('stats', {}).get('advanced', []) if r.get('sr_id')}
    poss = {r['sr_id']: r for r in (s or {}).get('stats', {}).get('per_poss', []) if r.get('sr_id')}
    if s:
        seen_ids = set()
        for r in s.get('roster', []) + [{'player': v['name_display'], 'sr_id': k, 'pos': v.get('pos')} for k, v in pg.items() if k not in {x.get('sr_id') for x in s.get('roster', [])}]:
            pid = r.get('sr_id') or f"n-{norm(r['player']).replace(' ', '-')}"
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            p = pg.get(pid, {})
            t = tot.get(pid, {})
            a = adv.get(pid, {})
            ps = poss.get(pid, {})
            rbnum_ = uniform_for(y, r['player'])
            rosternum_ = OFFICIAL_NUMS.get(y, {}).get(norm(r['player']))
            if rbnum_ is not None and rosternum_ is not None and str(rbnum_).lstrip('0') != str(rosternum_).lstrip('0'):
                NUM_DISAGREE.append((y, r['player'], rbnum_, rosternum_))
            num_ = rbnum_ if rbnum_ is not None else rosternum_ if rosternum_ is not None else r.get('number')  # record book > UConn roster archive > SR
            item = {'pid': pid, 'name': r['player'], 'num': num_, 'numOfficial': (rbnum_ is not None or rosternum_ is not None) or None, 'cls': r.get('class'), 'pos': r.get('pos'), 'ht': r.get('height'), 'wt': r.get('weight'),
                    'home': r.get('hometown'), 'hs': (r.get('high_school') or '').split(';')[0] or None, 'rsci': r.get('rsci'), 'photo': photo_for.get(pid)}
            for k_, v_ in official_bio(y, r['player']).items():   # UConn's own roster listing beats Sports-Reference's
                if item.get(k_) != v_:
                    BIO_CHANGES.append((y, r['player'], k_, item.get(k_), v_))
                item[k_] = v_
            if pid in photo_wide:
                item['photoWide'] = True
            if photo_pos(pid):
                item['photoPos'] = photo_pos(pid)
            if photo_studio(pid):
                item['photoStudio'] = True
            if p:
                item['pg'] = {'g': p.get('games'), 'gs': p.get('games_started'), 'mp': p.get('mp_per_g'), 'pts': p.get('pts_per_g'), 'trb': p.get('trb_per_g'), 'ast': p.get('ast_per_g'),
                              'stl': p.get('stl_per_g'), 'blk': p.get('blk_per_g'), 'tov': p.get('tov_per_g'), 'fg_pct': p.get('fg_pct'), 'fg3_pct': p.get('fg3_pct'), 'ft_pct': p.get('ft_pct'),
                              'orb': p.get('orb_per_g'), 'pf': p.get('pf_per_g')}
            if t:
                item['tot'] = {k: t.get(k) for k in ('games', 'mp', 'fg', 'fga', 'fg3', 'fg3a', 'ft', 'fta', 'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf', 'pts')}
                item['tot']['g'] = item['tot'].pop('games')
            if a:
                item['adv'] = {k: a.get(k) for k in ('per', 'ts_pct', 'efg_pct', 'usg_pct', 'ast_pct', 'trb_pct', 'stl_pct', 'blk_pct', 'ws', 'ws_per_40', 'bpm', 'obpm', 'dbpm')}
                if item['adv'].get('efg_pct') is None and p.get('efg_pct') is not None:
                    item['adv']['efg_pct'] = p['efg_pct']
                if ps:
                    item['adv']['off_rtg'] = ps.get('off_rtg')
                    item['adv']['def_rtg'] = ps.get('def_rtg')
            item = {k: v for k, v in item.items() if v not in (None, '', {})}
            roster.append(item)
        # two players can't share a number in one season: if one is confirmed by UConn's roster, blank the other rather than show a wrong number
        by_num = collections.defaultdict(list)
        for it in roster:
            if it.get('num') not in (None, ''):
                by_num[str(it['num'])].append(it)
        for n_, its in by_num.items():
            if len(its) > 1:
                confirmed = any(it.get('numOfficial') for it in its)
                for it in its:
                    if not it.get('numOfficial'):
                        it.pop('num', None)  # conflicting and unconfirmed: show no number rather than a wrong one
        for it in roster:
            it.pop('numOfficial', None)
        played_ = [r_ for r_ in games_out if r_.get('res')]
        box_sums = None
        if played_ and all(r_['id'] in details for r_ in played_):   # every game has a box score: sum them as a tie-breaker
            box_sums = collections.defaultdict(collections.Counter)
            for pid_, gl_ in PLAYER_GAMES.items():
                for e_ in gl_:
                    if e_['y'] == y:
                        bs_ = box_sums[pid_]
                        bs_['g'] += 1
                        for kb_, k_ in (('min', 'mp'), ('pts', 'pts'), ('reb', 'trb'), ('ast', 'ast'), ('stl', 'stl'), ('blk', 'blk'), ('to', 'tov'), ('fgm', 'fg'), ('fga', 'fga'),
                                        ('tpm', 'fg3'), ('tpa', 'fg3a'), ('ftm', 'ft'), ('fta', 'fta'), ('oreb', 'orb')):
                            bs_[k_] += e_.get(kb_) or 0
        OFFICIAL_STATS.apply(y, roster, box_sums)
        # game logs follow the settled games count: restore appearances Sports-Reference's box missed (seconds-long
        # cameos ESPN's box shows), and drop zero-minute lines the official count doesn't include
        rows_by_id_ = {r_['id']: r_ for r_ in games_out}
        for it in roster:
            g_off = (it.get('tot') or {}).get('g')
            gl_ = [e_ for e_ in PLAYER_GAMES.get(it['pid'], []) if e_['y'] == y]
            if not g_off:
                continue
            if g_off > len(gl_):
                for gid_ in EXCLUDED_APPEARANCES.get((it['pid'], y), [])[: g_off - len(gl_)]:
                    row_, det_ = rows_by_id_.get(gid_), details.get(gid_)
                    pl_ = next((q for q in (det_ or {}).get('teams', [{}])[0].get('players', []) if q.get('pid') == it['pid']), None)
                    if not row_ or not pl_:
                        continue
                    PLAYER_GAMES[it['pid']].append({'id': gid_, 'y': y, 'date': row_['date'], 'opp': {k: row_['opp'][k] for k in ('name', 'abbr', 'logo') if row_['opp'].get(k)}, 'ha': row_.get('ha'),
                                                    'res': row_.get('res'), 'score': f"{row_.get('pts')}-{row_.get('opp_pts')}", 'type': row_['type'], 'round': row_.get('round'),
                                                    **{k: pl_.get(k) for k in ('min', 'pts', 'reb', 'ast', 'stl', 'blk', 'to', 'fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'oreb')}})
                PLAYER_GAMES[it['pid']].sort(key=lambda e_: e_['date'])
            elif g_off < len(gl_):
                idle_ = [e_ for e_ in gl_ if not e_.get('min') and not any(e_.get(k) for k in ('pts', 'reb', 'ast', 'stl', 'blk', 'fga', 'fta', 'to'))]
                for e_ in idle_[: len(gl_) - g_off]:
                    PLAYER_GAMES[it['pid']].remove(e_)
    else:
        # current season from ESPN: roster from current.json, stats aggregated from box scores
        agg = collections.defaultdict(lambda: collections.Counter())
        gcount = collections.Counter()
        for gid, det in details.items():
            for p in det['teams'][0]['players']:
                if p.get('dnp') or not p.get('pid'):
                    continue
                gcount[p['pid']] += 1
                for k in ('min', 'pts', 'reb', 'ast', 'stl', 'blk', 'to', 'fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'oreb', 'pf'):
                    agg[p['pid']][k] += p.get(k) or 0
                agg[p['pid']]['gs'] += 1 if p.get('starter') else 0
        # ESPN's college roster lags a season; UConn's official roster (bio details + headshots) is the source of truth
        vc = jload(os.path.join(M, 'verify_current.json'), {}) or {}
        orc = {norm(p_['name']): p_ for p_ in (jload(os.path.join(OUT, 'official', 'roster_current.json'), {}) or {}).get('players', [])}
        official = vc.get('official_roster') or []
        espn_by_name = {norm(r.get('name')): r for r in (espn_current.get('roster') or [])}
        cur_roster = []
        for r in official:
            e_ = espn_by_name.get(norm(r['name'])) or next((v for k, v in espn_by_name.items() if k.split(' ')[-1] == norm(r['name']).split(' ')[-1] and k[:1] == norm(r['name'])[:1]), None)
            cls_ = r.get('cls') or ''
            cls_ = {'freshman': 'FR', 'sophomore': 'SO', 'junior': 'JR', 'senior': 'SR', 'graduate': 'GR', 'graduate student': 'GR'}.get(cls_.lower().replace('redshirt ', ''), cls_)
            if (r.get('cls') or '').lower().startswith('redshirt'):
                cls_ = 'R-' + cls_
            cur_roster.append({'id': (e_ or {}).get('id'), 'name': r['name'], 'jersey': r.get('num'), 'class': cls_, 'position': r.get('posShort') or r.get('pos'),
                               'height': (r.get('ht') or '').replace("' ", '-').replace('"', '').replace("'", '-'), 'weight': r.get('wt'), 'hometown': r.get('home'), 'hs': r.get('hs'), 'prev': r.get('prev'),
                               'headshot': (e_ or {}).get('headshot'), 'official_headshot': (orc.get(norm(r['name'])) or {}).get('headshot'), 'bio': r.get('url')})
        if not cur_roster:
            cur_roster = espn_current.get('roster') or []
        for r in cur_roster:
            aid = str(r.get('id')) if r.get('id') else None
            pid = pid_for_espn(aid, r.get('name'), y) if aid else None
            if not pid or pid.startswith('espn-'):
                k_ = norm(r.get('name'))
                pid = next((roster_names.get(yy, {}).get(k_) for yy in (y - 1, y - 2, y - 3) if roster_names.get(yy, {}).get(k_)), None) or pid or ('n-' + k_.replace(' ', '-'))
                if aid:
                    espn2sr[aid] = pid
            if r.get('headshot'):
                add_photo(pid, 1, r['headshot'], False, credit='ESPN', kind='headshot')
            if r.get('official_headshot'):
                add_photo(pid, 1.5, 'https://images.sidearmdev.com/resize?url=' + urllib.parse.quote(r['official_headshot'], safe='') + '&width=520&type=webp', True,
                          credit='UConn Athletics', kind='uconn-headshot', source=r.get('bio'))
            for rank_, url_, wide_, meta_ in sorted(PHOTO_CANDS.get(pid, []), key=lambda c: c[0]):
                u2 = localize(url_)
                if u2 and (u2.startswith('assets/') and hashlib.md5(open(os.path.join(SITE, '..', u2.split('?')[0]), 'rb').read()).hexdigest() in REJECT_HASHES):
                    u2 = None
                if u2:
                    photo_for[pid] = u2
                    (photo_wide.add(pid) if wide_ else photo_wide.discard(pid))
                    photo_meta[pid] = meta_
                    break
            item = {'pid': pid, 'name': r.get('name'), 'num': r.get('jersey'), 'cls': r.get('class') or r.get('experience'), 'pos': r.get('position'), 'ht': r.get('height'),
                    'wt': r.get('weight'), 'home': r.get('hometown'), 'hs': r.get('hs'), 'prev': r.get('prev'), 'photo': photo_for.get(pid), 'photoWide': pid in photo_wide or None,
                    'photoStudio': photo_studio(pid), 'espn': aid}
            n = gcount.get(pid)
            if n:
                A = agg[pid]
                item['pg'] = {'g': n, 'gs': A['gs'], 'mp': A['min'] / n, 'pts': A['pts'] / n, 'trb': A['reb'] / n, 'ast': A['ast'] / n, 'stl': A['stl'] / n, 'blk': A['blk'] / n, 'tov': A['to'] / n,
                              'fg_pct': A['fgm'] / A['fga'] if A['fga'] else None, 'fg3_pct': A['tpm'] / A['tpa'] if A['tpa'] else None, 'ft_pct': A['ftm'] / A['fta'] if A['fta'] else None,
                              'orb': A['oreb'] / n, 'pf': A['pf'] / n}
                item['pg'] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in item['pg'].items()}
                item['tot'] = {'g': n, 'mp': A['min'], 'pts': A['pts'], 'fg': A['fgm'], 'fga': A['fga'], 'fg3': A['tpm'], 'fg3a': A['tpa'], 'ft': A['ftm'], 'fta': A['fta'], 'orb': A['oreb'],
                               'trb': A['reb'], 'ast': A['ast'], 'stl': A['stl'], 'blk': A['blk'], 'tov': A['to'], 'pf': A['pf']}
            roster.append({k: v for k, v in item.items() if v not in (None, '')})
        if OFFICIAL_STATS.cume.get(y):   # the season in progress: UConn's official stat page settles ESPN's box-score sums
            OFFICIAL_STATS.apply(y, roster, None)

    for r in roster:
        if r.get('pg') or not s:
            PLAYER_SEASONS[r['pid']].append({'y': y, **r})

    # ── team stats
    team = {}
    ts = (s or {}).get('stats', {}).get('team', {})
    os_ = (s or {}).get('stats', {}).get('opponent', {})
    if ts.get('per_game'):
        tp = ts['per_game']
        op = os_.get('per_game', {})
        team['pg'] = {'pts': tp.get('pts_per_g'), 'fg_pct': tp.get('fg_pct'), 'fg3_pct': tp.get('fg3_pct'), 'fg3': tp.get('fg3_per_g'), 'ft_pct': tp.get('ft_pct'), 'ft': tp.get('ft_per_g'),
                      'trb': tp.get('trb_per_g'), 'orb': tp.get('orb_per_g'), 'ast': tp.get('ast_per_g'), 'stl': tp.get('stl_per_g'), 'blk': tp.get('blk_per_g'), 'tov': tp.get('tov_per_g'), 'pf': tp.get('pf_per_g')}
        team['opp'] = {'pts': op.get('opp_pts_per_g'), 'fg_pct': op.get('opp_fg_pct'), 'fg3_pct': op.get('opp_fg3_pct'), 'fg3': op.get('opp_fg3_per_g'), 'ft_pct': op.get('opp_ft_pct'), 'ft': op.get('opp_ft_per_g'),
                       'trb': op.get('opp_trb_per_g'), 'orb': op.get('opp_orb_per_g'), 'ast': op.get('opp_ast_per_g'), 'stl': op.get('opp_stl_per_g'), 'blk': op.get('opp_blk_per_g'), 'tov': op.get('opp_tov_per_g'), 'pf': op.get('opp_pf_per_g')}
        # UConn's shooting and counting stats = the sum of its (officially settled) player lines. Sports-Reference's team row
        # can disagree with its own players (2004-05 shows .317 from three-point attempts no player has).
        gp_ = sum(1 for g_ in games_out if g_.get("res"))   # games played (the W-L is tallied further down)
        if gp_ and roster and all(it.get('tot') for it in roster if (it.get('pg') or {}).get('g')):
            sums_ = {k: [((it.get('tot') or {}).get(k)) for it in roster if (it.get('pg') or {}).get('g')] for k in ('pts', 'fg', 'fga', 'fg3', 'fg3a', 'ft', 'fta', 'ast', 'stl', 'blk')}
            S_ = {k: (sum(v) if v and all(x is not None for x in v) else None) for k, v in sums_.items()}
            fixed_ = {'pts': S_['pts'] / gp_ if S_['pts'] is not None else None, 'fg_pct': S_['fg'] / S_['fga'] if S_['fga'] else None,
                      'fg3_pct': S_['fg3'] / S_['fg3a'] if S_['fg3a'] else None, 'fg3': S_['fg3'] / gp_ if S_['fg3'] is not None and S_['fg3a'] else None,
                      'ft_pct': S_['ft'] / S_['fta'] if S_['fta'] else None, 'ft': S_['ft'] / gp_ if S_['ft'] is not None else None,
                      'ast': S_['ast'] / gp_ if S_['ast'] is not None else None, 'stl': S_['stl'] / gp_ if S_['stl'] is not None else None, 'blk': S_['blk'] / gp_ if S_['blk'] is not None else None}
            for k_, v_ in fixed_.items():
                if v_ is None:
                    continue
                v_ = round(v_, 3) if k_.endswith('pct') else round(v_, 1)
                if team['pg'].get(k_) is not None and abs(team['pg'][k_] - v_) > (0.0015 if k_.endswith('pct') else 0.051):
                    OFFICIAL_STATS.report.setdefault('team_fixed', []).append({'y': y, 'stat': k_, 'was': team['pg'][k_], 'now': v_})
                team['pg'][k_] = v_
        tt_ = (OFFICIAL_STATS.cume.get(y) or {}).get('total') or {}
        if tt_.get('g'):   # the season-final sheet's team line also carries team rebounds and turnovers
            for k_, src_ in (('trb', 'trb'), ('orb', 'orb'), ('tov', 'tov'), ('pf', 'pf')):
                if tt_.get(src_) is not None:
                    v_ = round(tt_[src_] / tt_['g'], 1)
                    if team['pg'].get(k_) is not None and abs(team['pg'][k_] - v_) > 0.051:
                        OFFICIAL_STATS.report.setdefault('team_fixed', []).append({'y': y, 'stat': k_, 'was': team['pg'][k_], 'now': v_})
                    team['pg'][k_] = v_

    # ── polls
    polls = []
    for p in (s or {}).get('polls', []) or []:
        if (p.get('poll') or 'AP') != 'AP':
            continue
        wk = p.get('week')
        polls.append({'wk': wk, 'short': 'PRE' if wk == 'Pre' else 'FINAL' if str(wk).lower() == 'final' else wk, 'label': 'Preseason' if wk == 'Pre' else 'Final poll' if str(wk).lower() == 'final' else f'Week of {wk}', 'date': p.get('date'), 'rank': p.get('rank') if isinstance(p.get('rank'), int) else None})

    played = [g for g in games_out if g.get('res')]
    w = sum(1 for g in played if g['res'] == 'W')
    l = sum(1 for g in played if g['res'] == 'L')
    if s:
        w, l = meta.get('wins', w), meta.get('losses', l)
    finish = finish_for(games_out)
    ncaa_games = [g for g in games_out if g['type'] == 'NCAA']
    seed = None
    region = None
    for pst in meta.get('postseason', []) or []:
        m = re.search(r'#(\d+) seed in (\w+)', pst.get('text') or '')
        if m and 'NCAA' in (pst.get('label') or ''):
            seed, region = int(m.group(1)), m.group(2)
    seed = seed or si.get('seed')
    coach = ', '.join(c['name'] for c in meta.get('coaches', [])) or meta.get('coach_text') or next((e['name'] for e in ERAS if e['from'] <= y <= e['to']), '')
    ms = media_by_year.get(y, {})
    rec_cw = meta.get('conf_wins')
    rec_cl = meta.get('conf_losses')
    confname = meta.get('conference') or (si.get('conf_abbr'))
    if not s and y == current_season:
        confname = 'Big East'
    # SR names division years "Big East MBB Big East 6" (1996-98) and "Big East MBB East" (2001-03): keep the league, file the division
    confdiv = None
    mdiv = re.match(r'^Big East(?: MBB)?\s+(.+)$', confname or '')
    if mdiv:
        confname, confdiv = 'Big East', mdiv.group(1).strip()
    ap_final = si.get('rank_final') or meta.get('ap_final_meta')
    story = {'headline': ms.get('headline'), 'text': ms.get('story'), 'moments': ms.get('key_moments') or [], 'honors': ms.get('honors') or [], 'sources': ms.get('sources') or []}
    story = {k: v for k, v in story.items() if v}
    photos = (COMMONS_BY_SEASON.get(y, [])[:48] + SEASON_PHOTOS.get(y, []))[:90]
    season_obj = {
        'y': y, 'label': label(y), 'coach': coach, 'conf': confname, 'confDiv': confdiv, 'confShort': conf_short(confname), 'w': w, 'l': l, 'cw': rec_cw, 'cl': rec_cl,
        'confFinish': f"{meta.get('conf_finish')} in {conf_short(confname)}" if meta.get('conf_finish') else None,
        'finish': finish, 'seed': seed, 'region': region, 'apPre': si.get('rank_pre'), 'apHigh': si.get('rank_min'), 'apFinal': ap_final,
        'srs': (meta.get('srs') or {}).get('value'), 'sos': (meta.get('sos') or {}).get('value'), 'ortg': (meta.get('off_rtg') or {}).get('value'), 'drtg': (meta.get('def_rtg') or {}).get('value'),
        'pace': (meta.get('pace') or {}).get('value') if isinstance(meta.get('pace'), dict) else meta.get('pace'),
        'ppg': (meta.get('pts_per_g') or {}).get('value') or si.get('pts_per_g'), 'oppg': (meta.get('opp_pts_per_g') or {}).get('value') or si.get('opp_pts_per_g'),
        'story': story, 'roster': roster, 'team': team, 'games': games_out, 'polls': polls,
        'videos': [v for v in VIDS if v.get('season') == y], 'photos': photos, 'exhibitions': EXHIBITIONS.get(y) or None,
        'vacated': {'official': vac['official'], 'note': vac['note']} if vac else None,
    }
    # Efficiency for seasons SR doesn't rate: estimate possessions from team and opponent totals
    if s and not season_obj['ortg']:
        tt = ts.get('totals') or {}
        ot = os_.get('totals') or {}
        def poss(t, pre=''):
            g = lambda k: t.get(pre + k)
            if None in (g('fga'), g('fta'), g('tov'), g('fg')):
                return None
            orb = g('orb') if g('orb') is not None else 0.33 * (g('fga') - g('fg'))  # no OREB recorded: league-typical 33% of misses
            return g('fga') - orb + g('tov') + 0.475 * g('fta')
        pu, po = poss(tt), poss(ot, 'opp_')
        if pu and tt.get('pts') and ot.get('opp_pts'):
            p = (pu + po) / 2 if po else pu
            season_obj['ortg'] = round(100 * tt['pts'] / p, 1)
            season_obj['drtg'] = round(100 * ot['opp_pts'] / p, 1)
            season_obj['effEst'] = True
    if not s and played:
        season_obj['ppg'] = round(sum(g['pts'] for g in played) / len(played), 1)
        season_obj['oppg'] = round(sum(g['opp_pts'] for g in played) / len(played), 1)
    jdump(os.path.join(SITE, 'seasons', f'{y}.json'), {k: v for k, v in season_obj.items() if v is not None})
    jdump(os.path.join(SITE, 'games', f'{y}.json'), details)

    ncaaW = sum(1 for g in ncaa_games if g.get('res') == 'W')
    ncaaL = sum(1 for g in ncaa_games if g.get('res') == 'L')
    lead = {}
    for k, pk in (('pts', 'pts'), ('reb', 'trb'), ('ast', 'ast')):
        best = max((r for r in roster if r.get('pg') and (r['pg'].get('g') or 0) >= 10), key=lambda r: r['pg'].get(pk) or 0, default=None)
        if best:
            lead[k] = {'pid': best['pid'], 'name': best['name'], 'v': best['pg'].get(pk)}
    SEASON_SUM.append({k: v for k, v in {
        'y': y, 'label': label(y), 'coach': coach, 'w': w, 'l': l, 'cw': rec_cw, 'cl': rec_cl, 'conf': confname, 'confDiv': confdiv, 'confShort': conf_short(confname), 'finish': finish, 'seed': seed,
        'apPre': season_obj['apPre'], 'apHigh': season_obj['apHigh'], 'apFinal': ap_final, 'srs': season_obj['srs'], 'sos': season_obj['sos'], 'ortg': season_obj['ortg'], 'drtg': season_obj['drtg'],
        'effEst': season_obj.get('effEst'), 'pace': season_obj['pace'], 'ppg': season_obj['ppg'], 'oppg': season_obj['oppg'], 'headline': story.get('headline'), 'ncaaW': ncaaW, 'ncaaL': ncaaL, 'leaders': lead,
        'spark': [g['pts'] - g['opp_pts'] for g in played], 'mop': (legends.get('mop') or {}).get(str(y)) or MOP.get(y) if finish == 'champ' else None,
        'future': not played, 'officialRec': vac['official'] if vac else None,
    }.items() if v is not None and v != {}})
    if ncaa_games:
        MARCH.append({'y': y, 'seed': seed, 'region': region, 'coach': coach, 'rec': f'{w}–{l}', 'games': [
            {'id': g['id'], 'r': g.get('r'), 'round': g.get('round'), 'date': g['date'], 'opp': g['opp'], 'res': g.get('res'), 'pts': g.get('pts'), 'opp_pts': g.get('opp_pts'), 'ot': g.get('ot'), 'arena': g.get('arena')}
            for g in ncaa_games if g.get('res')]})
    print(f"{y} {label(y)}: {w}-{l} {finish:7s} games={len(games_out)} boxes={len(details)} roster={len(roster)}")

# ───────────────────────── Players ─────────────────────────
ranks_src = []
PLAYERS = []
os.makedirs(os.path.join(SITE, 'players'), exist_ok=True)
season_finish = {s['y']: s['finish'] for s in SEASON_SUM}
for pid, rows in PLAYER_SEASONS.items():
    rows.sort(key=lambda r: r['y'])
    srp = sr_players.get(pid) or {}
    name = rows[-1]['name']
    uc_rows = []
    for r in rows:
        p = r.get('pg') or {}
        uc_rows.append({'y': r['y'], 'label': label(r['y']), 'school': 'UConn', 'uconn': True, 'cls': r.get('cls'), 'num': r.get('num'), 'g': p.get('g'), 'gs': p.get('gs'), 'mp': p.get('mp'),
                        'pts': p.get('pts'), 'trb': p.get('trb'), 'ast': p.get('ast'), 'stl': p.get('stl'), 'blk': p.get('blk'), 'fg_pct': p.get('fg_pct'), 'fg3_pct': p.get('fg3_pct'),
                        'ft_pct': p.get('ft_pct'), 'adv': r.get('adv'), 'finish': season_finish.get(r['y']), 'tot': r.get('tot')})
    # other schools from the SR player page (transfers in/out)
    other = []
    for tr in ((srp.get('tables') or {}).get('players_per_game') or {}).get('rows', []) or []:
        team = tr.get('team_name_abbr') or ''
        yid = tr.get('year_id') or ''
        m = re.match(r'(\d{4})-(\d{2})', yid)
        if not m or 'uconn' in team.lower() or 'connecticut' in team.lower():
            continue
        yy = int(m.group(1)) + 1
        other.append({'y': yy, 'label': label(yy), 'school': team, 'uconn': False, 'cls': tr.get('class'), 'g': tr.get('games'), 'gs': tr.get('games_started'), 'mp': tr.get('mp_per_g'),
                      'pts': tr.get('pts_per_g'), 'trb': tr.get('trb_per_g'), 'ast': tr.get('ast_per_g'), 'stl': tr.get('stl_per_g'), 'blk': tr.get('blk_per_g'), 'fg_pct': tr.get('fg_pct'),
                      'fg3_pct': tr.get('fg3_pct'), 'ft_pct': tr.get('ft_pct')})
    all_rows = sorted([dict(r) for r in uc_rows] + other, key=lambda r: (r['y'], r['uconn']))   # copies: uc_rows keep 'tot' for the leaderboards
    T = collections.Counter()
    for r in uc_rows:
        for k, v in (r.get('tot') or {}).items():
            if isinstance(v, (int, float)):
                T[k] += v
    G = T.get('g') or sum((r.get('g') or 0) for r in uc_rows)
    career = {'g': G, 'gs': sum((r.get('gs') or 0) for r in uc_rows), 'pts': T.get('pts'), 'trb': T.get('trb'), 'ast': T.get('ast'), 'stl': T.get('stl'), 'blk': T.get('blk'), 'fg3': T.get('fg3'),
              'ws': round(sum(((r.get('adv') or {}).get('ws') or 0) for r in uc_rows), 1) or None}
    if not T.get('pts') and G:
        # no totals (current season from ESPN): rebuild from per-game
        for k in ('pts', 'trb', 'ast', 'stl', 'blk'):
            career[k] = round(sum((r.get(k) or 0) * (r.get('g') or 0) for r in uc_rows))
    if G:
        career.update({'mp_pg': (T.get('mp') or 0) / G if T.get('mp') else None, 'pts_pg': (career['pts'] or 0) / G, 'trb_pg': (career['trb'] or 0) / G, 'ast_pg': (career['ast'] or 0) / G,
                       'stl_pg': (career['stl'] or 0) / G, 'blk_pg': (career['blk'] or 0) / G,
                       'fg_pct': T['fg'] / T['fga'] if T.get('fga') else None, 'fg3_pct': T['fg3'] / T['fg3a'] if T.get('fg3a') else None, 'ft_pct': T['ft'] / T['fta'] if T.get('fta') else None})
        # Stats the record keepers didn't track in every season (steals/blocks before the mid-'80s, minutes and starts in the
        # late '70s): the career total covers only the seasons they were kept, and the average divides by those seasons' games
        # (dividing by every game would understate it). 'partial' names the seasons without the stat so pages can say so.
        partial = {}
        played = [r for r in uc_rows if (r.get('g') or 0) > 0]
        for k, pg in (('mp', 'mp_pg'), ('stl', 'stl_pg'), ('blk', 'blk_pg'), ('gs', None)):
            def season_val(r, k=k):   # a season's total for k, or None when it wasn't kept
                if k == 'gs':
                    return r.get('gs')
                if r.get('tot'):
                    return r['tot'].get(k)
                return r[k] * (r.get('g') or 0) if r.get(k) is not None else None   # current season from ESPN: per-game only
            kept = [r for r in played if season_val(r) is not None]
            if not kept:
                career[k] = None
                if pg:
                    career[pg] = None
            elif len(kept) < len(played):
                partial[k] = [r['y'] for r in played if season_val(r) is None]
                if pg:
                    gk = sum(r.get('g') or 0 for r in kept)
                    career[pg] = sum(season_val(r) for r in kept) / gk if gk else None
        if partial:
            career['partial'] = partial
    career = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in career.items() if v is not None}
    for r in all_rows:
        r.pop('tot', None)
    yrs = [r['y'] for r in uc_rows]
    span = f"{yrs[0] - 1}–{str(yrs[-1])[2:]}" if len(yrs) > 1 else label(yrs[0])
    bio = srp.get('bio') or {}
    bl = srp.get('bling') or []
    honors = [HONOR_FIX.get(pid, {}).get(b, b) for b in bl if not re.match(r'HS ', b)]
    # an honor from a season he spent at another school says so ("2014-15 All-Big East (Seton Hall)")
    other_school = {r['y']: r.get('school') for r in all_rows if r.get('uconn') is False and r.get('school')}
    uc_years = {r['y'] for r in uc_rows}
    def _school(h):
        m = re.match(r'^(\d{4})-(\d{2}) ', h)
        y_ = int(m.group(1)) + 1 if m else None
        if y_ and y_ <= 2011:
            h = h.replace('Pac-12', 'Pac-10')   # the league's name that season
        if y_ and y_ not in uc_years and other_school.get(y_) and 'NCAA Champion' not in h:
            return f"{h} ({other_school[y_]})"
        return h
    honors = [_school(h) for h in honors]
    draft = None
    if srp.get('draft') and srp['draft'].get('year'):
        dd = srp['draft']
        team_ = dd.get('team') or DRAFT_TEAM_FIX.get(pid)
        rbd_ = next((e for e in RB_DRAFT if norm(e['name']).split()[-1:] == norm(name).split()[-1:] and e['pick'] == dd.get('overall') and abs(e['year'] - int(dd['year'])) <= 1), None)
        went_ = rbd_ and rbd_['team']
        same_ = lambda a, b: bool(a and b) and (norm(a).split()[-1] in norm(b) or norm(b).split()[-1] in norm(a))
        draft = f"{dd['year']}, round {dd.get('round')}, pick {dd.get('overall')} · {team_ or went_}" + (f" (rights traded to {went_})" if team_ and went_ and not same_(team_, went_) else '')
    last = rows[-1]
    gl = sorted(PLAYER_GAMES.get(pid, []), key=lambda g: g['date'])
    pos_full = bio.get('Position') or last.get('pos')
    player = {'photoCredit': photo_meta.get(pid), 'id': pid, 'name': name, 'pos': pos_full, 'num': last.get('num'), 'ht': last.get('ht'), 'wt': last.get('wt'), 'home': last.get('home') or bio.get('Hometown'), 'hs': last.get('hs'),
              'born': bio.get('Born') or None, 'photo': photo_for.get(pid), 'photoWide': pid in photo_wide or None, 'photoPos': photo_pos(pid), 'photoStudio': photo_studio(pid), 'span': span, 'seasons': all_rows, 'career': career,
              'honors': honors, 'draft': draft, 'nba_url': srp.get('nba_url'), 'gamelog': gl, 'nick': bio.get('nicknames'),
              'videos': [v for v in VIDS if any(norm(name) == norm(x) for x in (v.get('players') or []))],
              'photos': []}
    for ph in COMMONS:
        if any(norm(x) == norm(name) for x in ph['subjects']) and len(player['photos']) < 24:
            player['photos'].append(ph)
    for yy in {r['y'] for r in uc_rows}:
        for ph in SEASON_PHOTOS.get(yy, []):
            if ph.get('caption') and norm(name) in norm(ph['caption']) and len(player['photos']) < 24:
                player['photos'].append(ph)
    w = wiki_by_pid.get(pid)
    if w and (w.get('image_url') or w.get('thumb_url')):
        player['photos'].append({'url': w.get('image_url') or w.get('thumb_url'), 'thumb': w.get('thumb_url') or w.get('image_url'), 'caption': w.get('caption_or_description') or name,
                                 'credit': w.get('author'), 'license': w.get('license'), 'page': w.get('file_page')})
    PLAYERS.append((player, uc_rows))

# ranks since 1987
def rank_map(key):
    vals = sorted(((p['career'].get(key) or 0, p['id']) for p, _ in PLAYERS), reverse=True)
    return {pid: i + 1 for i, (v, pid) in enumerate(vals) if v}


RANKS = {k: rank_map(k) for k in ('pts', 'trb', 'ast', 'blk', 'stl')}
core_players = []
for player, uc_rows in PLAYERS:
    part = player['career'].get('partial') or {}   # a partial total is only a floor, so it gets no rank of its own
    player['ranks'] = {k: RANKS[k].get(player['id']) for k in RANKS if RANKS[k].get(player['id']) and k not in part}
    jdump(os.path.join(SITE, 'players', f"{player['id']}.json"), {k: v for k, v in player.items() if v not in (None, [], '')})
    c = player['career']
    first, last_n = player['name'].split(' ', 1) if ' ' in player['name'] else ('', player['name'])
    core_players.append({k: v for k, v in {
        'id': player['id'], 'name': player['name'], 'last': last_n, 'span': player['span'], 'years': [r['y'] for r in uc_rows], 'pos': (uc_rows[-1].get('cls') and player['pos']) or player['pos'],
        'num': player['num'], 'photo': player['photo'], 'photoWide': player.get('photoWide'), 'photoPos': photo_pos(player['id']), 'photoStudio': photo_studio(player['id']), 'home': player['home'], 'ht': player['ht'],
        'g': c.get('g'), 'pts': c.get('pts'), 'trb': c.get('trb'), 'ast': c.get('ast'), 'blk': c.get('blk'), 'stl': c.get('stl'),
        'ppg': round(c['pts_pg'], 1) if c.get('pts_pg') is not None else None, 'rpg': round(c['trb_pg'], 1) if c.get('trb_pg') is not None else None,
        'apg': round(c['ast_pg'], 1) if c.get('ast_pg') is not None else None, 'spg': c.get('stl_pg'), 'bpg': c.get('blk_pg'), 'mpg': c.get('mp_pg'),
        'fg_pct': c.get('fg_pct'), 'fg3_pct': c.get('fg3_pct'), 'ft_pct': c.get('ft_pct'),
        'champ': any(r.get('finish') == 'champ' for r in uc_rows), 'draft': player['draft'], 'honors': [h for h in player['honors'] if re.search(r'\bAA\b|All-America|POY|MOP', h)],
    }.items() if v not in (None, [], '')})

# ───────────────────────── Leaders ─────────────────────────
def board(rows, key, n=10, sub=None, minv=None):
    out = []
    for r in sorted(rows, key=lambda r: r.get(key) or 0, reverse=True):
        if not r.get(key) or (minv and r.get(key) < minv):
            continue
        out.append({'pid': r['pid'], 'name': r['name'], 'photo': photo_for.get(r['pid']), 'v': r[key], 'sub': sub(r) if sub else None, **({'gid': r['gid']} if r.get('gid') else {})})
        if len(out) >= n:
            break
    return out


career_rows = [{'pid': p['id'], 'name': p['name'], 'span': p['span'], 'partial': p['career'].get('partial') or {}, **{k: p['career'].get(k) for k in ('pts', 'trb', 'ast', 'blk', 'stl', 'fg3')}} for p, _ in PLAYERS]
def career_sub(k):
    def sub(r):
        miss = r['partial'].get(k)
        return f"{r['span']} · not kept {', '.join(label(y) for y in miss)}" if miss else r['span']
    return sub
season_rows = []
for p, uc in PLAYERS:
    for r in uc:
        t = r.get('tot') or {}
        season_rows.append({'pid': p['id'], 'name': p['name'], 'y': r['y'], 'pts': t.get('pts'), 'trb': t.get('trb'), 'ast': t.get('ast'), 'blk': t.get('blk'), 'fg3': t.get('fg3'),
                            'ppg': r.get('pts') if (r.get('g') or 0) >= 20 else None})
game_rows = []
for pid, gl in PLAYER_GAMES.items():
    nm = next((p['name'] for p, _ in PLAYERS if p['id'] == pid), pid)
    for g in gl:
        game_rows.append({'pid': pid, 'name': nm, 'gid': g['id'], 'y': g['y'], 'opp': g['opp']['name'], 'date': g['date'], **{k: g.get(k) for k in ('pts', 'reb', 'ast', 'blk', 'tpm', 'stl')}})
sy = lambda r: label(r['y'])
LEADERS = {
    'career': {k: board(career_rows, k, sub=career_sub(k)) for k in ('pts', 'trb', 'ast', 'blk', 'stl', 'fg3')},
    'season': {**{k: board(season_rows, k, sub=sy) for k in ('pts', 'trb', 'ast', 'blk', 'fg3')}, 'ppg': board(season_rows, 'ppg', sub=sy)},
    'game': {k: board(game_rows, k, sub=lambda r: f"vs. {r['opp']} · {r['date'][:4]}") for k in ('pts', 'reb', 'ast', 'blk', 'tpm', 'stl')},
    'gameNote': f"From {len({g['gid'] for g in game_rows})} box scores on file: every game since 2002–03, plus NCAA Tournament games before that.",
}

# ───────────────────────── Opponents ─────────────────────────
OPP = {}
for g in GAMES_INDEX:
    k = g['opp']['key']
    o = OPP.setdefault(k, {'key': k, 'name': g['opp']['name'], 'abbr': g['opp'].get('abbr'), 'logo': g['opp'].get('logo'), 'w': 0, 'l': 0, 'ncaa': 0, 'ncaaW': 0, 'last': None})
    o['w' if g['res'] == 'W' else 'l'] += 1
    if g['type'] == 'NCAA':
        o['ncaa'] += 1
        o['ncaaW'] += g['res'] == 'W'
    o['last'] = max(o['last'] or '', g['date'])

# UConn's official all-time series record vs each opponent (record book series pages, through last season)
SERIES = (jload(os.path.join(OUT, 'official', 'series_records.json'), {}) or {}).get('series') or {}
SERIES_N = {re.sub(r'[^a-z]', '', norm(k)): v for k, v in SERIES.items()}
SERIES_ALIAS = {'TCU': 'Texas Christian', 'VCU': 'Virginia Commonwealth', 'LSU': 'Louisiana State', 'UCLA': 'Cal - Los Angeles (UCLA)', 'NC State': 'North Carolina State',
                'Miami': 'Miami (Fla.)', 'BYU': 'Brigham Young', 'UCF': 'Central Florida', 'UMBC': 'Maryland-Balt. County', 'SMU': 'Southern Methodist',
                'USC': 'Southern California', 'UAB': 'Alabama-Birmingham', 'Charlotte': 'UNC-Charlotte', 'Charleston': 'College of Charleston', 'Ohio': 'Ohio University',
                'McNeese': 'McNeese State', 'Towson': 'Towson State', 'UT Arlington': 'Texas-Arlington', 'Texas State': 'Southwest Texas State', 'UTSA': 'Texas-San Antonio',
                'UAlbany': 'Albany (NY St. Teachers*)', 'Ole Miss': 'Mississippi', "Saint Mary's": "Saint Mary's (Calif.)", 'Loyola Maryland': 'Loyola (Md.)',
                'Kansas City': 'Missouri-Kansas City', 'Grambling': 'Grambling State', 'St. Francis Brooklyn': 'St. Francis (NY)', 'Saint Francis': 'St. Francis (PA)',
                'Long Island University': 'Long Island', 'Brooklyn': 'Brooklyn College'}
for o in OPP.values():
    rec_ = SERIES_N.get(re.sub(r'[^a-z]', '', norm(SERIES_ALIAS.get(o['name'], o['name']))))
    if rec_:
        o['allW'], o['allL'] = rec_['w'], rec_['l']

# ───────────────────────── Eras, banners, current ─────────────────────────
coach_media = {}
for c in (legends.get('coaches') or []):
    if isinstance(c, dict) and c.get('name'):
        coach_media[norm(c['name'])] = c
# Jason's coach photos (photos-drop/coaches/<Coach Name>.png|jpg) always win; a committed copy in site/assets/coaches keeps them on deploys
COACH_PHOTO = {}
for e in ERAS:
    _drop = [f for f in glob.glob(os.path.join(HERE, '..', 'photos-drop', 'coaches', '*')) if norm(os.path.splitext(os.path.basename(f))[0]) == norm(e['name'])]
    _dst_dir = os.path.join(HERE, '..', 'site', 'assets', 'coaches')
    if _drop:
        _src = max(_drop, key=os.path.getmtime)
        _ext = os.path.splitext(_src)[1].lower()
        _dst = os.path.join(_dst_dir, e['id'] + _ext)
        os.makedirs(_dst_dir, exist_ok=True)
        if not os.path.exists(_dst) or open(_src, 'rb').read() != open(_dst, 'rb').read():
            for _old in glob.glob(os.path.join(_dst_dir, e['id'] + '.*')):
                os.remove(_old)
            open(_dst, 'wb').write(open(_src, 'rb').read())
    _have = glob.glob(os.path.join(_dst_dir, e['id'] + '.*'))
    if _have:
        COACH_PHOTO[norm(e['name'])] = 'assets/coaches/' + os.path.basename(_have[0])
for c in (legends.get('coaches') or []):
    if isinstance(c, dict) and COACH_PHOTO.get(norm(c.get('name'))):
        c['image'] = {'image_url': COACH_PHOTO[norm(c['name'])], 'thumb_url': COACH_PHOTO[norm(c['name'])], 'supplied': 'Jason'}
COACH_OFFICIAL = (jload(os.path.join(HERE, 'coach_records.json'), {}) or {}).get('coaches') or {}
eras_out = []
for e in ERAS:
    ss = [s for s in SEASON_SUM if e['from'] <= s['y'] <= e['to'] and not s.get('future')]
    cm = coach_media.get(norm(e['name']), {})
    w_court, l_court = sum(s['w'] for s in ss), sum(s['l'] for s in ss)
    off = COACH_OFFICIAL.get(e['name'])
    if off and off.get('through') and ss and ss[-1]['y'] > off['through']:   # seasons since the record book went to print
        extra = [s for s in ss if s['y'] > off['through']]
        off = {**off, 'w': off['w'] + sum(s['w'] for s in extra), 'l': off['l'] + sum(s['l'] for s in extra)}
    if off and (off['w'], off['l']) != (w_court, l_court) and not off.get('why'):
        print(f"  !! {e['name']}: record book {off['w']}-{off['l']} vs games {w_court}-{l_court} (no explanation on file)")
    wo, lo = (off['w'], off['l']) if off else (w_court, l_court)
    eras_out.append({**e, 'w': wo, 'l': lo, 'courtW': w_court if (wo, lo) != (w_court, l_court) else None, 'courtL': l_court if (wo, lo) != (w_court, l_court) else None,
                     'recordNote': (off or {}).get('why') if (wo, lo) != (w_court, l_court) else None, 'titles': [s['y'] for s in ss if s['finish'] == 'champ'],
                     'ff': sum(1 for s in ss if s['finish'] in ('champ', 'runner', 'final4')), 'ncaa': sum(1 for s in ss if s['finish'] not in ('none', 'nit')),
                     'photo': COACH_PHOTO.get(norm(e['name'])) or localize(img_url(cm.get('image') or cm.get('image_url') or cm.get('photo')), force=True) or img_url(cm.get('image') or cm.get('image_url') or cm.get('photo')),
                     'blurb': cm.get('summary') or cm.get('blurb')})
secondary = [{'y': s['y'], 'label': 'NCAA\nFinal Four' if s['finish'] == 'final4' else 'National\nRunner-Up', 'kind': 'ff'} for s in SEASON_SUM if s['finish'] in ('final4', 'runner')]

cur_games = [g for g in json.load(open(os.path.join(SITE, 'seasons', f'{current_season}.json')))['games']]
nxt = next((g for g in cur_games if not g.get('res')), None)
lst = next((g for g in reversed(cur_games) if g.get('res')), None)
cur_sum = next(s for s in SEASON_SUM if s['y'] == current_season)
CURRENT = {'season': current_season, 'label': label(current_season), 'record': f"{cur_sum['w']}-{cur_sum['l']}" if (cur_sum['w'] + cur_sum['l']) else None,
           'rank': ((espn_current.get('polls') or {}).get('ap') or {}).get('uconn', {}).get('rank') if ((espn_current.get('polls') or {}).get('ap') or {}).get('season') == current_season else None}
if nxt:
    CURRENT['next'] = {'id': nxt['id'], 'eid': nxt.get('eid'), 'date': nxt['date'], 'day': nxt.get('day'), 'ha': nxt['ha'], 'opp': nxt['opp'], 'venue': nxt.get('arena'), 'tv': nxt.get('tv'), 'note': nxt.get('round')}
if lst:
    CURRENT['last'] = {k: lst.get(k) for k in ('id', 'date', 'ha', 'opp', 'res', 'pts', 'opp_pts', 'top')}

# ───────────────────────── Season hub (live: pipeline/season_hub.py) ─────────────────────────
def ord_(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"

def _hub(name):
    return jload(os.path.join(OUT, 'hub', f'{name}.json'), {}) or {}
H_ST, H_PO, H_NET, H_BR, H_NO, H_PH = (_hub(n) for n in ('standings', 'polls', 'net', 'bracket', 'next_opp', 'polls_history'))
played_now = [g for g in cur_games if g.get('res')]
HUB = {'season': current_season, 'label': label(current_season)}
if H_ST.get('rows'):
    HUB['standings'] = {'label': H_ST.get('seasonLabel'), 'final': H_ST.get('season') != current_season, 'rows': H_ST['rows'], 'fetched': H_ST.get('fetched')}
for key_ in ('ap', 'coaches'):
    p_ = H_PO.get(key_)
    if p_:
        u_ = next((r for r in p_['ranks'] if r['id'] == '41'), None)
        HUB.setdefault('polls', {})[key_] = {'date': p_['date'], 'label': p_.get('seasonLabel'), 'final': p_.get('season') != current_season,
                                            'rank': u_ and u_['rank'], 'prev': u_ and u_['prev'], 'record': u_ and u_.get('record'),
                                            'votes': next((r['pts'] for r in p_['others'] if r['id'] == '41'), None), 'top': p_['ranks'][:10]}
if H_PH.get(str(current_season)):
    HUB['pollHistory'] = H_PH[str(current_season)]
u_ = next((r for r in H_NET.get('rows') or [] if r.get('School') in ('UConn', 'Connecticut')), None)
if u_:
    HUB['net'] = {'rank': int(u_['Rank']), 'record': u_.get('Record'), 'prev': u_.get('Prev'), 'quads': [u_.get(f'Quad {i}') for i in (1, 2, 3, 4)],
                  'through': H_NET.get('through'), 'final': not played_now}   # until UConn plays, ncaa.com still shows last season's final NET
if H_BR:
    HUB['bracket'] = {**{k: H_BR.get(k) for k in ('seed', 'avg', 'brackets', 'updated')}, 'final': (H_BR.get('updated') or '') < f'{current_season - 1}-11-01'}
# next opponent: their season (ESPN), our history with them (every meeting on the site)
if CURRENT.get('next'):
    o_ = CURRENT['next']['opp']
    meet_ = [g for g in GAMES_INDEX if g['opp'].get('key') == o_.get('key') and g.get('res')]
    HUB['preview'] = {'opp': o_, 'game': CURRENT['next']['id'],
                      'record': H_NO.get('record') if H_NO.get('game') == CURRENT['next']['id'] else None,
                      'standing': H_NO.get('standing') if H_NO.get('game') == CURRENT['next']['id'] else None,
                      'leaders': (H_NO.get('leaders') or []) if H_NO.get('game') == CURRENT['next']['id'] else [],
                      'series': {'w': sum(g['res'] == 'W' for g in meet_), 'l': sum(g['res'] == 'L' for g in meet_), 'first': meet_[0]['date'][:4] if meet_ else None,
                                 **({'allW': OPP[o_['key']]['allW'], 'allL': OPP[o_['key']]['allL']} if o_.get('key') in OPP and 'allW' in OPP[o_['key']] else {})},
                      'last': {k: meet_[-1].get(k) for k in ('id', 'date', 'res', 'pts', 'opp_pts', 'ha', 'ot')} if meet_ else None}
# milestone watch
MILES = []
hur_ = next((e for e in eras_out if e['name'] == 'Dan Hurley'), None)
if hur_:
    nxt_ = (hur_['w'] // 50 + 1) * 50
    MILES.append({'who': 'Dan Hurley', 'kind': 'coach', 'text': f"{hur_['w']} wins at UConn. Win No. {nxt_} is {nxt_ - hur_['w']} away.", 'left': nxt_ - hur_['w']})
_rbt = re.search(r'^Totals\s+(\d{3,4})\s+(\d{3,4})\s+\.\d{3}', open(os.path.join(HERE, 'cache.nosync', 'official', 'recordbook_pypdf.txt'), errors='ignore').read(), re.M) \
    if os.path.exists(os.path.join(HERE, 'cache.nosync', 'official', 'recordbook_pypdf.txt')) else None
if _rbt:   # the record book's all-time total runs through last season
    allw_ = int(_rbt.group(1)) + sum(g['res'] == 'W' for g in played_now)
    alll_ = int(_rbt.group(2)) + sum(g['res'] == 'L' for g in played_now)
    nxt_ = (allw_ // 50 + 1) * 50
    MILES.append({'who': 'UConn', 'kind': 'program', 'text': f"All-time record {allw_:,}–{alll_:,}. Win No. {nxt_:,} is {nxt_ - allw_} away.", 'left': nxt_ - allw_})
THRESH = {'pts': ('points', (1000, 1500, 2000)), 'trb': ('rebounds', (500, 750, 1000)), 'ast': ('assists', (300, 400, 500, 600)), 'blk': ('blocks', (100, 150, 200, 300)),
          'stl': ('steals', (100, 150, 200)), 'fg3': ('3-pointers', (100, 150, 200, 250))}
cur_ids_ = {r['pid'] for r in json.load(open(os.path.join(SITE, 'seasons', f'{current_season}.json'))).get('roster') or []}
for player_, uc_ in PLAYERS:
    if player_['id'] not in cur_ids_:
        continue
    c_ = player_['career']
    gp_ = c_.get('g') or 0
    if gp_ < 10:
        continue
    for k_, (word_, marks_) in THRESH.items():
        v_ = c_.get(k_) or 0
        pace_ = v_ / gp_ * 35   # about a season's worth at his career rate
        nxt_ = next((m for m in marks_ if m > v_), None)
        if nxt_ and nxt_ - v_ <= max(pace_, 1):
            MILES.append({'who': player_['name'], 'pid': player_['id'], 'kind': 'player', 'text': f"{v_:,} career {word_} at UConn. {nxt_:,} is {nxt_ - v_} away.", 'left': nxt_ - v_})
# all-time scoring list: the record book's 1,000-point club (every era), with current players' live totals
_rbtxt = open(os.path.join(HERE, 'cache.nosync', 'official', 'recordbook_pypdf.txt'), errors='ignore').read() if os.path.exists(os.path.join(HERE, 'cache.nosync', 'official', 'recordbook_pypdf.txt')) else ''
CLUB = [(m.group(1).strip().title(), int(m.group(2).replace(',', ''))) for m in re.finditer(r"^\s*\d+\.\)\s+([A-Z][A-Za-z.'’ \-]+?)\s+\(\d years?,[^)]*\),?\s+([\d,]+)\s+p", _rbtxt, re.M)]
CLUB = [(re.sub(r'\bMc([a-z])', lambda m_: 'Mc' + m_.group(1).upper(), n_), v_) for n_, v_ in CLUB]
for player_, uc_ in PLAYERS:
    if player_['id'] not in cur_ids_ or (player_['career'].get('pts') or 0) < 900 or not CLUB:
        continue
    me_, pts_ = norm(player_['name']), player_['career']['pts']
    others_ = [(n_, v_) for n_, v_ in CLUB if norm(n_) != me_]
    rank_ = 1 + sum(1 for _, v_ in others_ if v_ > pts_)
    above_ = min([(v_, n_) for n_, v_ in others_ if v_ > pts_] or [None], key=lambda x: x[0] if x else 0)
    if above_:
        MILES.append({'who': player_['name'], 'pid': player_['id'], 'kind': 'player',
                      'text': f"{pts_:,} career points, {ord_(rank_)} in UConn history. {above_[0] - pts_ + 1} more passes {above_[1]} ({above_[0]:,}).", 'left': above_[0] - pts_ + 1})
# streaks (all seasons, newest games last)
_all = sorted(GAMES_INDEX, key=lambda g: g['date'])
for label_, pick_ in (('home', lambda g: g['ha'] == 'H'), ('overall', lambda g: True)):
    n_, r_ = 0, None
    for g in reversed([g for g in _all if g.get('res') and pick_(g)]):
        if r_ is None:
            r_ = g['res']
        if g['res'] != r_:
            break
        n_ += 1
    if r_ == 'W' and n_ >= 5:
        MILES.append({'who': 'UConn', 'kind': 'streak', 'text': f"{n_} straight {'home ' if label_ == 'home' else ''}wins.", 'left': 0})
HUB['milestones'] = MILES
# recap of the latest game this season
if played_now:
    lg_ = played_now[-1]
    det_ = (jload(os.path.join(SITE, 'games', f'{current_season}.json'), {}) or {}).get(lg_['id']) or {}
    tm_ = det_.get('teams') or []
    if tm_:
        def gs_(p):
            return (p.get('pts') or 0) + 0.4 * (p.get('fgm') or 0) - 0.7 * (p.get('fga') or 0) - 0.4 * ((p.get('fta') or 0) - (p.get('ftm') or 0)) + 0.7 * (p.get('oreb') or 0) \
                + 0.3 * ((p.get('reb') or 0) - (p.get('oreb') or 0)) + (p.get('stl') or 0) + 0.7 * (p.get('ast') or 0) + 0.7 * (p.get('blk') or 0) - 0.4 * (p.get('pf') or 0) - (p.get('to') or 0)
        ups_ = sorted([p for p in tm_[0].get('players') or [] if not p.get('dnp') and p.get('pts') is not None], key=gs_, reverse=True)[:3]
        tops_ = []
        for p in ups_:
            prev_hi_ = max([e.get('pts') or 0 for e in PLAYER_GAMES.get(p.get('pid'), []) if e['y'] == current_season and e['id'] != lg_['id']] or [0])
            tops_.append({'name': p['name'], 'pid': p.get('pid'), 'line': f"{p.get('pts')} pts, {p.get('reb')} reb, {p.get('ast')} ast",
                          'seasonHigh': bool(p.get('pts')) and p.get('pts') > prev_hi_ and len([e for e in PLAYER_GAMES.get(p.get('pid'), []) if e['y'] == current_season]) > 1})
        HUB['recap'] = {'id': lg_['id'], 'date': lg_['date'], 'opp': lg_['opp'], 'res': lg_['res'], 'pts': lg_['pts'], 'opp_pts': lg_['opp_pts'], 'ot': lg_.get('ot'),
                        'record': lg_.get('rec'), 'tops': tops_}

titles = []
for m in MARCH:
    if len(m['games']) == 6 and m['games'][-1]['res'] == 'W':
        titles.append({**m, 'mop': (legends.get('mop') or {}).get(str(m['y'])) or MOP.get(m['y'])})
nit = []
for s in SEASON_SUM:
    if s['finish'] == 'nit':
        ss = jload(os.path.join(SITE, 'seasons', f"{s['y']}.json"))
        ng = [g for g in ss['games'] if g['type'] == 'NIT' and g.get('res')]
        nit.append({'y': s['y'], 'w': sum(g['res'] == 'W' for g in ng), 'l': sum(g['res'] == 'L' for g in ng), 'champ': len(ng) >= 4 and all(g['res'] == 'W' for g in ng)})

featured = [v for v in VIDS if v.get('featured')]
core = {
    'updated': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
    'seasons': SEASON_SUM, 'eras': eras_out, 'players': sorted(core_players, key=lambda p: -(p.get('pts') or 0)),
    'opponents': OPP, 'leaders': LEADERS, 'march': {'years': MARCH, 'titles': titles, 'nit': nit},
    'banners': {'secondary': secondary}, 'current': CURRENT, 'hub': HUB, 'logos': LOGOS if LOGOS['files'] else None,
    'videos': [dict(v) for v in (featured[:40] + [v for v in VIDS if v.get('round') and v not in featured][:60])],
}
jdump(os.path.join(SITE, 'core.json'), core)
jdump(os.path.join(SITE, 'games_index.json'), GAMES_INDEX)
if legends:
    # every assistant coach since 1946-47 and every head coach since 1900-01, from the record book (p. 2)
    _as = jload(os.path.join(OUT, 'official', 'assistants.json'), {}) or {}
    if _as.get('assistants'):
        legends['assistants'] = {'source': _as.get('source'), 'list': _as['assistants'], 'heads': _as.get('head_coaches') or []}
    by_date = collections.defaultdict(list)
    for g in GAMES_INDEX:
        by_date[g['date']].append(g)
    fixed = 0
    for r in legends.get('rivalries') or []:
        on = norm(r.get('opponent'))
        for ng in r.get('notable_games') or []:
            hit = next((g for g in by_date.get(ng.get('date'), []) if on and (on in norm(g['opp']['name']) or norm(g['opp']['name']) in on)), None)
            if hit:
                sc = f"{hit['pts']}–{hit['opp_pts']}" + (f" ({hit['ot']})" if hit.get('ot') else '')
                if ng.get('score') != sc or ng.get('result') != hit['res']:
                    fixed += 1
                ng.update({'score': sc, 'result': hit['res'], 'gid': hit['id']})
    print(f'rivalry games reconciled with SR results: {fixed} changed')
    jdump(os.path.join(SITE, 'legends.json'), legends)
media_photos = COMMONS
jdump(os.path.join(SITE, 'media.json'), {'videos': VIDS, 'photos': media_photos})
import moments   # long-form Moments pages, built from the fact-checked drafts + the game data written above
moments.main()
import venues_build   # Home floors: record book lines + every game since 1986-87 in its true building
venues_build.main()
import history_build   # the early years (1900-01 to 1976-77) from the record book (out/official/history.json)
history_build.main()
sizes = sum(os.path.getsize(f) for f in glob.glob(os.path.join(SITE, '**', '*.json'), recursive=True))
jdump(os.path.join(OUT, 'official', 'stats_validation.json'), OFFICIAL_STATS.report)
print(f'jersey numbers: record book and roster archive disagree on {len(NUM_DISAGREE)}: {NUM_DISAGREE}')
print(f'play-by-play hidden for {len(PBP_DROPPED)} games that do not end at the final score')
print(f'player bios: {len(BIO_CHANGES)} values set from UConn official rosters', dict(collections.Counter(c[2] for c in BIO_CHANGES)))
print(OFFICIAL_STATS.summary())
print(f"\nplayers={len(PLAYERS)} games_indexed={len(GAMES_INDEX)} opponents={len(OPP)} videos={len(VIDS)} data={sizes / 1e6:.1f} MB")
