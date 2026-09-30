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
FIRST, = (1987,)

ERAS = [
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
sr_players = {os.path.basename(f)[:-5]: jload(f) for f in glob.glob(os.path.join(OUT, 'sr', 'players', '*.json'))}
school_index = {r['season']: r for r in (jload(os.path.join(OUT, 'sr', 'school_index.json'), {}) or {}).get('seasons', [])}

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
if isinstance(media_seasons, dict):
    media_seasons = media_seasons.get('seasons', list(media_seasons.values()))
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
if os.path.isdir(DROP):
    import shutil, subprocess
    for fn in sorted(os.listdir(DROP)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.tif', '.tiff'):
            continue
        pid = stem if stem in known_pids else name_to_pid_all.get(norm(stem))
        if not pid:
            print(f'! photos-drop: no player matches "{fn}"')
            continue
        dst = os.path.join(ASSETS, f'{pid}.jpg')
        src = os.path.join(DROP, fn)
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
            if shutil.which('sips'):
                subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '82', '-Z', '900', src, '--out', dst], check=True, capture_output=True)
            else:
                shutil.copy(src, dst)
            print(f'photos-drop: {fn} → {pid}')
for fn in os.listdir(ASSETS):
    pid = os.path.splitext(fn)[0]
    add_photo(pid, 0, f'assets/players/{fn}', True, credit=drop_credit.get(pid) or 'Archival photo, restored', kind='restored')

# Photo agent: UConn-era portraits/action shots, pro headshots
RANK_KIND = {'uconn-headshot': 2, 'uconn-action': 3, 'uconn-team': 3, 'nba-headshot': 4, 'pro-other': 5, 'other': 5}
for pid, lst in ((jload(os.path.join(M, 'player_photos.json'), {}) or {}).get('players') or {}).items():
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

photo_for, photo_wide, photo_meta = {}, set(), {}
for pid, cands in PHOTO_CANDS.items():
    rank, url, wide, meta = sorted(cands, key=lambda c: c[0])[0]
    photo_for[pid] = url
    photo_meta[pid] = meta
    if wide:
        photo_wide.add(pid)


CROP_POS = {'left-third': '22% 18%', 'left': '28% 18%', 'center': '50% 18%', 'right': '72% 18%', 'right-third': '78% 18%', 'top': '50% 0%'}


def photo_pos(pid):
    c = (photo_meta.get(pid) or {}).get('crop')
    return CROP_POS.get(c) if c else None


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
_extra = jload(os.path.join(M, 'videos_extra.json'), {}) or {}
_extra = _extra.get('videos', _extra) if isinstance(_extra, dict) else _extra
_vled = {}
for it in (jload(os.path.join(M, 'verify_videos.json'), {}) or {}).get('items', []):
    _vled.setdefault(it.get('id'), []).append(it)
for v in list(media_videos or []) + list(_extra or []):
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
    VIDS.append({k: v.get(k) for k in ('id', 'title', 'channel', 'kind', 'season', 'date', 'opponent', 'round', 'players', 'description') if v.get(k) is not None})
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


def clip_index(e, rows):
    """Match ESPN per-play clips ("1H (15:36) ...") to play rows."""
    out = {}
    by = collections.defaultdict(list)
    for i, r in enumerate(rows):
        by[(r[0], r[1])].append(i)
    for v in e.get('videos') or []:
        m = re.match(r'\s*(\d)H \((\d+:\d\d)\)|\s*OT(\d?) \((\d+:\d\d)\)', v.get('description') or '')
        if not m or not (v.get('links') or {}).get('mp4'):
            continue
        per = int(m.group(1)) if m.group(1) else 2 + int(m.group(3) or 1)
        clk = m.group(2) or m.group(4)
        cands = by.get((per, clk)) or by.get((per, clk.lstrip('0')))
        if cands:
            out[cands[-1]] = {'src': v['links']['mp4'], 'thumb': v.get('thumbnail'), 'title': v.get('headline')}
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


def finish_for(games):
    ncaa = [g for g in games if g['type'] == 'NCAA' and g.get('res')]
    if ncaa:
        r = len(ncaa) - 1
        last = ncaa[-1]
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
            g['arena'] = o_['venue'] + (f", {o_['city']}" if o_.get('city') else '')
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
                              'espn': sr_game_espn.get((y, g['g'])), 'box_slug': g.get('box_slug')})
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
            r_idx = ncaa_i
            ncaa_i += 1
            rnd = round_label(g, r_idx)
        elif g['type'] == 'CTOURN' and not rnd and e and e.get('note'):
            rnd = e['note'].title().replace("Men'S", "Men's")
        elif g['type'] == 'NIT':
            rnd = rnd or 'NIT'
        if g['type'] == 'CTOURN' and not rnd:
            rnd = 'Conference tournament'
        ha = g['ha']
        if g['type'] in ('NCAA', 'CTOURN'):
            ha = 'N'  # tournament games are neutral-site, even at MSG or in Hartford (sources disagree game to game)
        row = {'id': gid, 'date': (g.get('iso') or (e or {}).get('date') or g['date']) if not g.get('res') else g['date'], 'type': g['type'], 'ha': ha, 'opp': opp}
        for k in ('res', 'pts', 'opp_pts', 'ot', 'rec', 'arena'):
            if g.get(k) is not None:
                row[k] = g[k]
        if y < 2001 and g['type'] in ('REG', 'CTOURN') and not e:
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
                jdump(os.path.join(SITE, 'plays', f'{gid}.json'), {'plays': rows, 'wp': wp, 'clips': clips})
                det['hasPlays'] = True
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
                if sr_played is not None:
                    if p['pid'] not in sr_played:
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
                                'top': row.get('top'), 'big': 2 if g['type'] == 'NCAA' else 1 if g.get('opp_rank') else 0})

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
            item = {'pid': pid, 'name': r['player'], 'num': r.get('number'), 'cls': r.get('class'), 'pos': r.get('pos'), 'ht': r.get('height'), 'wt': r.get('weight'),
                    'home': r.get('hometown'), 'hs': (r.get('high_school') or '').split(';')[0] or None, 'rsci': r.get('rsci'), 'photo': photo_for.get(pid)}
            if pid in photo_wide:
                item['photoWide'] = True
            if photo_pos(pid):
                item['photoPos'] = photo_pos(pid)
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
            cur_roster.append({'id': (e_ or {}).get('id'), 'name': r['name'], 'jersey': r.get('num'), 'class': r.get('cls'), 'position': r.get('posShort') or r.get('pos'),
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
            best = sorted(PHOTO_CANDS.get(pid, []), key=lambda c: c[0])
            if best:
                photo_for[pid] = best[0][1]
                (photo_wide.add(pid) if best[0][2] else photo_wide.discard(pid))
                photo_meta[pid] = best[0][3]
            item = {'pid': pid, 'name': r.get('name'), 'num': r.get('jersey'), 'cls': r.get('class') or r.get('experience'), 'pos': r.get('position'), 'ht': r.get('height'),
                    'wt': r.get('weight'), 'home': r.get('hometown'), 'hs': r.get('hs'), 'prev': r.get('prev'), 'photo': photo_for.get(pid), 'photoWide': pid in photo_wide or None, 'espn': aid}
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
    ap_final = si.get('rank_final') or meta.get('ap_final_meta')
    story = {'headline': ms.get('headline'), 'text': ms.get('story'), 'moments': ms.get('key_moments') or [], 'honors': ms.get('honors') or [], 'sources': ms.get('sources') or []}
    story = {k: v for k, v in story.items() if v}
    photos = (COMMONS_BY_SEASON.get(y, [])[:48] + SEASON_PHOTOS.get(y, []))[:90]
    season_obj = {
        'y': y, 'label': label(y), 'coach': coach, 'conf': confname, 'confShort': conf_short(confname), 'w': w, 'l': l, 'cw': rec_cw, 'cl': rec_cl,
        'confFinish': f"{meta.get('conf_finish')} in {conf_short(confname)}" if meta.get('conf_finish') else None,
        'finish': finish, 'seed': seed, 'region': region, 'apPre': si.get('rank_pre'), 'apHigh': si.get('rank_min'), 'apFinal': ap_final,
        'srs': (meta.get('srs') or {}).get('value'), 'sos': (meta.get('sos') or {}).get('value'), 'ortg': (meta.get('off_rtg') or {}).get('value'), 'drtg': (meta.get('def_rtg') or {}).get('value'),
        'pace': (meta.get('pace') or {}).get('value') if isinstance(meta.get('pace'), dict) else meta.get('pace'),
        'ppg': (meta.get('pts_per_g') or {}).get('value') or si.get('pts_per_g'), 'oppg': (meta.get('opp_pts_per_g') or {}).get('value') or si.get('opp_pts_per_g'),
        'story': story, 'roster': roster, 'team': team, 'games': games_out, 'polls': polls,
        'videos': [v for v in VIDS if v.get('season') == y], 'photos': photos, 'exhibitions': EXHIBITIONS.get(y) or None,
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
        'y': y, 'label': label(y), 'coach': coach, 'w': w, 'l': l, 'cw': rec_cw, 'cl': rec_cl, 'conf': confname, 'confShort': conf_short(confname), 'finish': finish, 'seed': seed,
        'apPre': season_obj['apPre'], 'apHigh': season_obj['apHigh'], 'apFinal': ap_final, 'srs': season_obj['srs'], 'sos': season_obj['sos'], 'ortg': season_obj['ortg'], 'drtg': season_obj['drtg'],
        'effEst': season_obj.get('effEst'), 'pace': season_obj['pace'], 'ppg': season_obj['ppg'], 'oppg': season_obj['oppg'], 'headline': story.get('headline'), 'ncaaW': ncaaW, 'ncaaL': ncaaL, 'leaders': lead,
        'spark': [g['pts'] - g['opp_pts'] for g in played], 'mop': (legends.get('mop') or {}).get(str(y)) or MOP.get(y) if finish == 'champ' else None,
        'future': not played,
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
    all_rows = sorted(uc_rows + other, key=lambda r: (r['y'], r['uconn']))
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
    career = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in career.items() if v is not None}
    for r in all_rows:
        r.pop('tot', None)
    yrs = [r['y'] for r in uc_rows]
    span = f"{yrs[0] - 1}–{str(yrs[-1])[2:]}" if len(yrs) > 1 else label(yrs[0])
    bio = srp.get('bio') or {}
    bl = srp.get('bling') or []
    honors = [b for b in bl if not re.match(r'HS ', b)]
    draft = None
    if srp.get('draft') and srp['draft'].get('year'):
        dd = srp['draft']
        draft = f"{dd['year']}, round {dd.get('round')}, pick {dd.get('overall')} · {dd.get('team')}"
    last = rows[-1]
    gl = sorted(PLAYER_GAMES.get(pid, []), key=lambda g: g['date'])
    pos_full = bio.get('Position') or last.get('pos')
    player = {'photoCredit': photo_meta.get(pid), 'id': pid, 'name': name, 'pos': pos_full, 'num': last.get('num'), 'ht': last.get('ht'), 'wt': last.get('wt'), 'home': last.get('home') or bio.get('Hometown'), 'hs': last.get('hs'),
              'born': bio.get('Born') or None, 'photo': photo_for.get(pid), 'photoWide': pid in photo_wide or None, 'photoPos': photo_pos(pid), 'span': span, 'seasons': all_rows, 'career': career,
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
    player['ranks'] = {k: RANKS[k].get(player['id']) for k in RANKS if RANKS[k].get(player['id'])}
    jdump(os.path.join(SITE, 'players', f"{player['id']}.json"), {k: v for k, v in player.items() if v not in (None, [], '')})
    c = player['career']
    first, last_n = player['name'].split(' ', 1) if ' ' in player['name'] else ('', player['name'])
    core_players.append({k: v for k, v in {
        'id': player['id'], 'name': player['name'], 'last': last_n, 'span': player['span'], 'years': [r['y'] for r in uc_rows], 'pos': (uc_rows[-1].get('cls') and player['pos']) or player['pos'],
        'num': player['num'], 'photo': player['photo'], 'photoWide': player.get('photoWide'), 'photoPos': photo_pos(player['id']), 'home': player['home'], 'ht': player['ht'],
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


career_rows = [{'pid': p['id'], 'name': p['name'], 'span': p['span'], **{k: p['career'].get(k) for k in ('pts', 'trb', 'ast', 'blk', 'stl', 'fg3')}} for p, _ in PLAYERS]
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
    'career': {k: board(career_rows, k, sub=lambda r: r['span']) for k in ('pts', 'trb', 'ast', 'blk', 'stl', 'fg3')},
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

# ───────────────────────── Eras, banners, current ─────────────────────────
coach_media = {}
for c in (legends.get('coaches') or []):
    if isinstance(c, dict) and c.get('name'):
        coach_media[norm(c['name'])] = c
eras_out = []
for e in ERAS:
    ss = [s for s in SEASON_SUM if e['from'] <= s['y'] <= e['to'] and not s.get('future')]
    cm = coach_media.get(norm(e['name']), {})
    eras_out.append({**e, 'w': sum(s['w'] for s in ss), 'l': sum(s['l'] for s in ss), 'titles': [s['y'] for s in ss if s['finish'] == 'champ'],
                     'ff': sum(1 for s in ss if s['finish'] in ('champ', 'runner', 'final4')), 'ncaa': sum(1 for s in ss if s['finish'] not in ('none', 'nit')),
                     'photo': img_url(cm.get('image') or cm.get('image_url') or cm.get('photo')), 'blurb': cm.get('summary') or cm.get('blurb')})
secondary = [{'y': s['y'], 'label': 'NCAA\nFinal Four' if s['finish'] == 'final4' else 'National\nRunner-Up', 'kind': 'ff'} for s in SEASON_SUM if s['finish'] in ('final4', 'runner')]

cur_games = [g for g in json.load(open(os.path.join(SITE, 'seasons', f'{current_season}.json')))['games']]
nxt = next((g for g in cur_games if not g.get('res')), None)
lst = next((g for g in reversed(cur_games) if g.get('res')), None)
cur_sum = next(s for s in SEASON_SUM if s['y'] == current_season)
CURRENT = {'season': current_season, 'label': label(current_season), 'record': f"{cur_sum['w']}-{cur_sum['l']}" if (cur_sum['w'] + cur_sum['l']) else None,
           'rank': ((espn_current.get('polls') or {}).get('ap') or {}).get('uconn', {}).get('rank') if ((espn_current.get('polls') or {}).get('ap') or {}).get('season') == current_season else None}
if nxt:
    CURRENT['next'] = {'id': nxt['id'], 'eid': nxt.get('eid'), 'date': nxt['date'], 'ha': nxt['ha'], 'opp': nxt['opp'], 'venue': nxt.get('arena'), 'tv': nxt.get('tv'), 'note': nxt.get('round')}
if lst:
    CURRENT['last'] = {k: lst.get(k) for k in ('id', 'date', 'ha', 'opp', 'res', 'pts', 'opp_pts', 'top')}

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
    'banners': {'secondary': secondary}, 'current': CURRENT,
    'videos': [dict(v) for v in (featured[:40] + [v for v in VIDS if v.get('round') and v not in featured][:60])],
}
jdump(os.path.join(SITE, 'core.json'), core)
jdump(os.path.join(SITE, 'games_index.json'), GAMES_INDEX)
if legends:
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
sizes = sum(os.path.getsize(f) for f in glob.glob(os.path.join(SITE, '**', '*.json'), recursive=True))
print(f"\nplayers={len(PLAYERS)} games_indexed={len(GAMES_INDEX)} opponents={len(OPP)} videos={len(VIDS)} data={sizes / 1e6:.1f} MB")
