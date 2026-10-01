#!/usr/bin/env python3
"""Moments: long-form pages for UConn's greatest nights -> site/data/moments.json + site/data/moments/<slug>.json

The words come only from pipeline/out/moments/verified/<slug>.json: research drafts (brief: out/moments/BRIEF.md) that
passed an independent fact-check. Everything the site already knows about the game (score, venue, attendance, box
score, play-by-play, win probability, ESPN play clips, matched videos) is read from site/data, never from the draft,
so a moment can't disagree with its own game page.

Photos: Jason's files in photos-drop/moments/<slug>.(png|jpg) always win the hero spot."""
import glob, json, os, re, subprocess, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = os.path.join(ROOT, 'site', 'data')
SRC = os.environ.get('MOMENTS_SRC') or os.path.join(HERE, 'out', 'moments', 'verified')
DROP = os.path.join(ROOT, 'photos-drop', 'moments')
ASSETS = os.path.join(ROOT, 'site', 'assets', 'moments')
CACHE = os.path.join(HERE, 'cache.nosync', 'moments_web.json')

# editorial labels for the index filters (not facts)
TAGS = {
    'roof-collapse-1978': ['Milestones'],
    'gampel-opens-1990': ['Milestones'],
    'big-east-champs-1990': ['Conference titles'],
    'the-shot-1990': ['Buzzer-beaters', 'March'],
    'ray-allen-1996': ['Buzzer-beaters', 'Conference titles'],
    'rip-hamilton-1998': ['Buzzer-beaters', 'March'],
    'title-1999': ['Championships', 'March'],
    'duke-comeback-2004': ['Comebacks', 'March'],
    'title-2004': ['Championships', 'March'],
    'six-overtimes-2009': ['Marathons', 'Heartbreak'],
    'kemba-pitt-2011': ['Buzzer-beaters', 'Conference titles'],
    'title-2011': ['Championships', 'March'],
    'napier-florida-2013': ['Buzzer-beaters'],
    'title-2014': ['Championships', 'March'],
    'jalen-adams-4ot-2016': ['Marathons', 'Buzzer-beaters'],
    'title-2023': ['Championships', 'March'],
    'thirty-zero-2024': ['March'],
    'back-to-back-2024': ['Championships', 'March'],
    'mullins-duke-2026': ['Buzzer-beaters', 'March'],
}
KIND_ORDER = {'final_play': 0, 'highlights': 1, 'moment': 1, 'espn': 2, 'radio': 2, 'documentary': 3, 'full_game': 4, 'interview': 5}

try:
    WEB = json.load(open(CACHE))
except Exception:
    WEB = {}
# hand-picked hero stills (clean frames without burned-in thumbnail text): {slug: {url, credit, pos}}
HEROES = {k: v for k, v in (json.load(open(os.path.join(HERE, 'moments_heroes.json'))) if os.path.exists(os.path.join(HERE, 'moments_heroes.json')) else {}).items() if not k.startswith('_')}


def jload(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d


def fetch(url, head=False):
    req = urllib.request.Request(url, method='HEAD' if head else 'GET', headers={'User-Agent': 'Mozilla/5.0 (Macintosh) StorrsLore/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, (b'' if head else r.read())


def oembed(vid):
    """YouTube's own title/channel for a video; None if it's gone or private (re-checked weekly)."""
    k = f'oembed:{vid}'
    if k not in WEB:
        try:
            _, b = fetch(f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json')
            o = json.loads(b)
            WEB[k] = {'title': o.get('title'), 'channel': o.get('author_name')}
        except Exception as e:
            WEB[k] = None if '404' in str(e) or '401' in str(e) or '403' in str(e) else {'error': str(e)}
    v = WEB[k]
    return v if v and not v.get('error') else None


def yt_poster(vid):
    """The biggest YouTube still that exists for a video."""
    k = f'maxres:{vid}'
    if k not in WEB:
        try:
            st, _ = fetch(f'https://i.ytimg.com/vi/{vid}/maxresdefault.jpg', head=True)
            WEB[k] = st == 200
        except Exception:
            WEB[k] = False
    return f'https://i.ytimg.com/vi/{vid}/{"maxresdefault" if WEB[k] else "hqdefault"}.jpg'


def jason_hero(slug):
    """photos-drop/moments/<slug>.* -> site/assets/moments/<slug>.<ext> (resized to 2000 px wide at most)"""
    drop = sorted(glob.glob(os.path.join(DROP, slug + '.*')), key=os.path.getmtime)
    if drop:
        src = drop[-1]
        ext = os.path.splitext(src)[1].lower().replace('.jpeg', '.jpg')
        dst = os.path.join(ASSETS, slug + ext)
        os.makedirs(ASSETS, exist_ok=True)
        mark = dst + '.src'
        sig = f'{os.path.getsize(src)}:{os.path.getmtime(src)}'
        if not os.path.exists(dst) or (open(mark).read() if os.path.exists(mark) else '') != sig:
            for old in glob.glob(os.path.join(ASSETS, slug + '.*')):
                os.remove(old)
            subprocess.run(['sips', '-Z', '2000', src, '--out', dst], capture_output=True)
            open(mark, 'w').write(sig)
    have = [f for f in glob.glob(os.path.join(ASSETS, slug + '.*')) if not f.endswith('.src')]
    return ('assets/moments/' + os.path.basename(have[0])) if have else None


PER = {'1H': 1, '2H': 2, 'OT': 3}


def per_num(s):
    s = str(s or '').upper().replace(' ', '')
    if s in PER:
        return PER[s]
    m = re.fullmatch(r'(\d)OT|OT(\d)', s)
    if m:
        return 2 + int(m.group(1) or m.group(2))
    m = re.fullmatch(r'([12])(ST|ND)?(HALF)?', s)
    return int(m.group(1)) if m else None


def clock_s(c):
    m = re.fullmatch(r'(\d+):(\d+)(?:\.\d+)?', str(c or '').strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def align(seq, plays):
    """match each beat of the decisive sequence to its row in our (ESPN) play-by-play. The drafts use UConn's official
    clock times, which can differ from ESPN's by a few seconds, so: same period, within 8 seconds, same score after the
    play, preferring a play that names someone in the beat, then the closest clock."""
    out = []
    for b in seq:
        pn, cs = per_num(b.get('period')), clock_s(b.get('clock'))
        hit = None
        if pn and cs is not None:
            cands = [i for i, p in enumerate(plays) if p[0] == pn and clock_s(p[1]) is not None and abs(clock_s(p[1]) - cs) <= 8]
            if b.get('uconn') is not None:
                cands = [i for i in cands if plays[i][3] == b['uconn'] and plays[i][4] == b['opp']]
            words = {w.lower() for w in re.findall(r"[A-Z][a-z'\-]{2,}", b.get('text') or '')} - {'uconn', 'the', 'connecticut'}
            rank = lambda i: (0 if any(w in (plays[i][7] or '').lower() for w in words) else 1, abs(clock_s(plays[i][1]) - cs), 0 if plays[i][5] else 1)
            hit = min(cands, key=rank) if cands else None
        out.append(hit)
    return out


def runs_of(plays):
    runs, cur = [], None
    for i, p in enumerate(plays):
        if not p[5] or not p[2]:
            continue
        if cur and cur['side'] == p[2]:
            cur['pts'] += p[6] or 0
            cur['end'] = i
        else:
            if cur:
                runs.append(cur)
            cur = {'side': p[2], 'pts': p[6] or 0, 'start': i, 'end': i}
    if cur:
        runs.append(cur)
    return runs


def per_label(n):
    return '1st half' if n == 1 else '2nd half' if n == 2 else ('OT' if n == 3 else f'{n - 2}OT')


def pbp_facts(plays):
    if not plays:
        return None
    lc, lead = 0, 0   # a lead change is the lead passing from one team to the other, even by way of a tie
    for p in plays:
        d = (p[3] > p[4]) - (p[3] < p[4])
        if d:
            lc += bool(lead and d != lead)
            lead = d
    ties = sum(1 for i, p in enumerate(plays) if i and p[5] and p[3] == p[4])
    big_u = max(0, *[p[3] - p[4] for p in plays])
    big_o = max(0, *[p[4] - p[3] for p in plays])
    rs = sorted(runs_of(plays), key=lambda r: -r['pts'])
    best = {s: next((r for r in rs if r['side'] == s), None) for s in ('u', 'o')}
    run = lambda r: r and {'pts': r['pts'], 'from': f"{plays[r['start']][1]} {per_label(plays[r['start']][0])}", 'to': f"{plays[r['end']][1]} {per_label(plays[r['end']][0])}",
                          'score': [plays[r['start'] - 1][3] if r['start'] else 0, plays[r['start'] - 1][4] if r['start'] else 0, plays[r['end']][3], plays[r['end']][4]]}
    return {'leadChanges': lc, 'ties': ties, 'bigU': big_u, 'bigO': big_o, 'runU': run(best['u']), 'runO': run(best['o'])}


def line(p):
    bits = [f"{p.get('pts', 0)} pts"]
    if p.get('reb'):
        bits.append(f"{p['reb']} reb")
    if p.get('ast'):
        bits.append(f"{p['ast']} ast")
    for k, lab in (('stl', 'stl'), ('blk', 'blk')):
        if (p.get(k) or 0) >= 3:
            bits.append(f'{p[k]} {lab}')
    shoot = f"{p['fgm']}-{p['fga']} FG" if p.get('fga') is not None and p.get('fgm') is not None else ''
    return ' · '.join(bits), shoot


def leaders(team, n):
    ps = [p for p in (team or {}).get('players') or [] if not p.get('dnp') and p.get('pts') is not None]
    ps.sort(key=lambda p: (-(p.get('pts') or 0), -(p.get('reb') or 0)))
    out = []
    for p in ps[:n]:
        a, b = line(p)
        out.append({'name': p['name'], 'pid': p.get('pid'), 'photo': p.get('photo'), 'num': p.get('num'), 'line': a, 'shoot': b,
                    'pts': p.get('pts'), 'reb': p.get('reb'), 'ast': p.get('ast'), 'min': p.get('min')})
    return out


class Sources:
    """one numbered source list per moment; paragraphs carry the numbers"""

    def __init__(self, listed):
        self.urls, self.what = [], {}
        for s in listed or []:
            if isinstance(s, dict) and s.get('url'):
                self.what[s['url']] = s.get('what')

    def nums(self, srcs):
        out = []
        for u in srcs or []:
            u = (u.get('url') if isinstance(u, dict) else u) or ''
            u = u.strip()
            if not u:
                continue
            if u not in self.urls:
                self.urls.append(u)
            out.append(self.urls.index(u) + 1)
        return sorted(set(out))

    def items(self):
        res = []
        for i, u in enumerate(self.urls):
            if u.startswith('site:'):
                res.append({'n': i + 1, 'url': None, 'label': 'Storrs Lore play-by-play (ESPN data)', 'what': None})
                continue
            host = urllib.parse.urlparse(u).netloc.replace('www.', '')
            res.append({'n': i + 1, 'url': u, 'label': host, 'what': self.what.get(u)})
        return res


def paras(items, S):
    out = []
    for it in items or []:
        if isinstance(it, str):
            it = {'text': it}
        t = (it.get('text') or '').strip()
        if t:
            out.append({'text': t, 'src': S.nums(it.get('sources'))})
    return out


def build_one(m, core):
    slug, gid = m['slug'], m.get('gameId')
    y = int(gid.split('-')[0]) if gid else int(m['date'][:4])
    season = jload(os.path.join(SITE, 'seasons', f'{y}.json'), {})
    games = season.get('games') or []
    g = next((x for x in games if x['id'] == gid), None)
    det = (jload(os.path.join(SITE, 'games', f'{y}.json'), {}) or {}).get(gid) or {}
    P = jload(os.path.join(SITE, 'plays', f'{gid}.json'), {}) if det.get('hasPlays') else {}
    plays = (P or {}).get('plays') or []
    S = Sources(m.get('sources'))
    teams = det.get('teams') or []
    U, O = (teams + [{}, {}])[:2]

    out = {'slug': slug, 'title': m.get('title'), 'nickname': (m.get('nickname') or {}).get('text') if isinstance(m.get('nickname'), dict) else m.get('nickname'),
           'dek': m.get('dek'), 'date': m.get('date'), 'tags': TAGS.get(slug, []), 'y': y, 'gid': gid if g else None}
    if g:
        out['game'] = {'res': g.get('res'), 'pts': g.get('pts'), 'opp_pts': g.get('opp_pts'), 'ot': g.get('ot'), 'round': g.get('round'), 'ha': g.get('ha'),
                       'forfeit': g.get('forfeit'), 'opp': {k: (g.get('opp') or {}).get(k) for k in ('name', 'abbr', 'logo', 'key')},
                       'rec': g.get('rec'), 'line': {'u': U.get('line'), 'o': O.get('line')},
                       'rank': {'u': U.get('rank'), 'o': O.get('rank')}, 'seed': {'u': U.get('seed'), 'o': O.get('seed')}}
        if g.get('date', '')[:10] != (m.get('date') or '')[:10]:
            print(f"  !! {slug}: draft date {m.get('date')} vs site {g.get('date')}; using the site's")
            out['date'] = g['date'][:10]
    venue = (det.get('venue') or {}).get('name') or (g or {}).get('arena') or m.get('venue')
    city = (det.get('venue') or {}).get('city') or (g or {}).get('city') or m.get('city')
    att = det.get('att') or ((m.get('attendance') or {}).get('n') if isinstance(m.get('attendance'), dict) else None)
    out['facts'] = {'venue': venue, 'city': city, 'att': att, 'attSrc': S.nums((m.get('attendance') or {}).get('sources')) if not det.get('att') and isinstance(m.get('attendance'), dict) else [],
                    'event': m.get('event') or (g or {}).get('round'), 'tip': (m.get('tip') or {}).get('text') if isinstance(m.get('tip'), dict) else m.get('tip'),
                    # the fact-checked network beats ESPN's feed, which lists streams too ("ESPN3, ESPN2")
                    'tv': ((m.get('tv') or {}).get('network') if isinstance(m.get('tv'), dict) else None) or det.get('tv'),
                    'announcers': (m.get('tv') or {}).get('announcers') if isinstance(m.get('tv'), dict) else None}
    ent = m.get('entering') or {}
    if ent:
        out['entering'] = {'u': ent.get('uconn'), 'o': ent.get('opp'), 'src': S.nums(ent.get('sources'))}

    out['setup'] = paras(m.get('setup'), S)
    out['story'] = paras(m.get('game'), S)

    # decisive sequence, matched to our play-by-play (clips + chart markers)
    seq = [b for b in m.get('sequence') or [] if isinstance(b, dict) and b.get('text')]
    hits = align(seq, plays) if plays else [None] * len(seq)
    clips = (P or {}).get('clips') or {}
    out['sequence'] = []
    clipped = set()
    for b, i in zip(seq, hits):
        row = {'period': b.get('period'), 'clock': b.get('clock'), 'u': b.get('uconn'), 'o': b.get('opp'), 'text': b['text'].strip(), 'src': S.nums(b.get('sources'))}
        if i is not None:
            row['play'] = i
            if (plays[i][3], plays[i][4]) != (b.get('uconn'), b.get('opp')) and b.get('uconn') is not None:
                print(f"  !! {slug}: beat {b.get('clock')} score {b.get('uconn')}-{b.get('opp')} vs play-by-play {plays[i][3]}-{plays[i][4]}")
            c = clips.get(str(i))
            if c and i not in clipped:   # two beats can sit on one play (a shot, then the inbound after it): one clip
                clipped.add(i)
                row['clip'] = {'src': c['src'], 'thumb': c.get('thumb'), 'title': c.get('title') or plays[i][7]}
        out['sequence'].append(row)

    # the decisive shot on a court, when ESPN charted it
    # the decisive shot: of the made field goals in the sequence that ESPN charted, the one closest to a horn
    # (free throws carry a placeholder coordinate). Distances are left to the fact-checked words; sources disagree on them.
    # Only a UConn shot in the last 10 seconds of a period counts: a court diagram of some mid-game basket says nothing.
    fgs = [(k, i) for k, (b, i) in enumerate(zip(out['sequence'], hits))
           if i is not None and plays[i][5] and plays[i][2] == 'u' and plays[i][8] is not None and plays[i][9] is not None
           and 'free throw' not in (plays[i][7] or '').lower() and (clock_s(plays[i][1]) or 0) <= 10]
    if fgs:
        k, i = min(fgs, key=lambda t: (clock_s(plays[t[1]][1]) or 0, t[0]))
        out['shot'] = {'x': plays[i][8], 'y': plays[i][9], 'beat': k, 'u': plays[i][2] == 'u', 'clock': plays[i][1], 'period': per_label(plays[i][0])}

    if plays:
        per_idx = [i for i in range(1, len(plays)) if plays[i][0] != plays[i - 1][0]]
        marks, seen_ = [], set()
        for b, i in zip(out['sequence'], hits):
            if i is not None and i not in seen_:
                seen_.add(i)
                marks.append({'play': i, 'label': f"{b['clock']} · {b['text'][:90]}"})
        out['chart'] = {'wp': P.get('wp') or None, 'margin': [p[3] - p[4] for p in plays], 'periods': per_idx, 'marks': marks,
                        'nPer': plays[-1][0]}
        out['pbp'] = pbp_facts(plays)
        out['clipCount'] = len(clips)

    out['numbers'] = [{'value': str(n.get('value')), 'label': n.get('label'), 'src': S.nums(n.get('sources'))} for n in m.get('numbers') or [] if n.get('value') not in (None, '')]
    out['quotes'] = [{'text': q['text'].strip(), 'who': q.get('who'), 'role': q.get('role'), 'when': q.get('when'), 'src': S.nums([q.get('source')])}
                     for q in m.get('quotes') or [] if q.get('text')]
    out['aftermath'] = paras(m.get('aftermath'), S)
    out['legacy'] = paras(m.get('legacy'), S)
    out['leaders'] = {'u': leaders(U, 3), 'o': leaders(O, 2), 'oName': (g or {}).get('opp', {}).get('name')}
    if not teams and isinstance(m.get('box'), dict):
        out['boxNote'] = 'Box score from ' + (m['box'].get('source') or 'a contemporary source')

    # UConn players in the story, for links and the cast list
    roster = {r['name']: r for r in season.get('roster') or []}
    text = ' '.join(x['text'] for k in ('setup', 'story', 'sequence', 'aftermath', 'legacy') for x in out[k])
    cast = []
    for name, r in roster.items():
        n = len(re.findall(r'\b' + re.escape(name) + r'\b', text))
        if n:
            cast.append((n, {'pid': r['pid'], 'name': name, 'photo': r.get('photo'), 'num': r.get('num'), 'pos': r.get('pos'), 'cls': r.get('cls'),
                             'photoPos': r.get('photoPos'), 'photoStudio': r.get('photoStudio')}))
    cast.sort(key=lambda c: -c[0])
    out['cast'] = [c for _, c in cast]

    # what came next that postseason
    if g:
        gi = games.index(g)
        later = [x for x in games[gi + 1:] if x.get('type') == g.get('type') and x.get('res')] if g.get('type') in ('NCAA', 'CTOURN') else []
        out['next'] = [{'gid': x['id'], 'date': x['date'][:10], 'opp': x['opp']['name'], 'logo': x['opp'].get('logo'), 'res': x['res'], 'pts': x['pts'], 'opp_pts': x['opp_pts'],
                        'ot': x.get('ot'), 'round': x.get('round')} for x in later]
        out['finish'] = season.get('finish')
        out['seasonRec'] = f"{season.get('w')}-{season.get('l')}"

    # videos: the draft's (re-verified with YouTube) + the ones already matched to the game
    vids, seen = [], set()
    site_v = [{'youtube': x.get('id'), **{k: x.get(k) for k in ('kind', 'title', 'channel', 'src', 'thumb', 'sub')}} for x in (det.get('videos') or []) + ((g or {}).get('videos') or [])]
    for v in (m.get('videos') or []) + site_v:
        vid = v.get('youtube') or v.get('id')
        if not vid or vid in seen:
            continue
        seen.add(vid)
        if v.get('src'):   # ESPN clip (mp4), already matched to the game by the pipeline
            vids.append({'id': vid, 'title': v.get('title'), 'channel': v.get('sub') or 'ESPN', 'kind': 'espn', 'src': v['src'], 'thumb': v.get('thumb')})
            continue
        o = oembed(vid)
        if not o:
            print(f'  {slug}: video {vid} unavailable; dropped')
            continue
        vids.append({'id': vid, 'title': o['title'], 'channel': o['channel'], 'kind': v.get('kind') or 'highlights', 'start': v.get('start')})
    vids.sort(key=lambda v: KIND_ORDER.get(v['kind'], 6))
    out['videos'] = vids
    sb = (out.get('shot') or {}).get('beat')
    if sb is not None and not out['sequence'][sb].get('clip'):
        shooter = (re.match(r"^\s*([A-Z][\w.'\-]+(?:\s+[A-Z][\w.'\-]+)*?)\s+(?:made|makes)", plays[hits[sb]][7] or '') or [None, ''])[1].split()
        last = shooter[-1].lower() if shooter else None
        espn = [v for v in vids if v.get('src') and last and re.search(r'\b' + re.escape(last) + r'\b', v['title'].lower())
                and re.search(r'\b(hits|drains|buries|shot|three|3|heave|winner|buzzer|beats?|forces?)\b', v['title'].lower()) and ':' not in v['title']]
        if espn:
            out['sequence'][sb]['clip'] = {'src': espn[0]['src'], 'thumb': espn[0].get('thumb'), 'title': espn[0]['title']}

    out['photos'] = [{'url': p['url'], 'page': p.get('page'), 'credit': p.get('credit'), 'license': p.get('license'), 'caption': p.get('depicts')}
                     for p in m.get('photos') or [] if p.get('url')]
    out['papers'] = [{'paper': p.get('paper'), 'date': p.get('date'), 'url': p.get('iiif') or None, 'page': p.get('page_url'), 'headline': p.get('headline')}
                     for p in m.get('newspaper') or [] if p.get('page_url')]

    hero = jason_hero(slug)
    pick = HEROES.get(slug)
    if hero:
        out['hero'] = {'url': hero, 'kind': 'photo', 'credit': None}
    elif pick:
        vid = next((v['id'] for v in vids if v['id'] in pick['url'] or (v.get('thumb') and v['thumb'] == pick['url'])), None)
        out['hero'] = {'url': pick['url'], 'kind': 'video' if vid else 'photo', 'video': vid, 'credit': pick.get('credit'), 'pos': pick.get('pos')}
    elif out['photos']:
        p = out['photos'][0]
        out['hero'] = {'url': p['url'], 'kind': 'photo', 'credit': ' · '.join(x for x in (p.get('credit'), p.get('license')) if x)}
    elif vids:
        v = next((x for x in vids if x['kind'] in ('final_play', 'highlights', 'moment')), vids[0])
        out['hero'] = {'url': yt_poster(v['id']), 'kind': 'video', 'video': v['id'], 'credit': f"Video still · {v['channel']}"}
    out['sources'] = S.items()
    return out


SITE_URL = 'https://jfrascino.github.io/the-rafters/'   # change with the custom domain
STUB = os.path.join(ROOT, 'site', 'm')


def stub(d):
    """site/m/<slug>.html: a tiny page whose tags give link previews (iMessage, Slack, X) the moment's own title, summary and
    picture, then forwards to the story in the app. The app's hash routes can't carry per-page preview tags themselves."""
    import html
    e = lambda x: html.escape(str(x or ''), quote=True)
    img = (d.get('hero') or {}).get('url') or 'assets/og/default.jpg'
    img = img if img.startswith('http') else SITE_URL + img
    target = f"../#/moment/{d['slug']}"
    title = f"{d['title']} · Storrs Lore"
    os.makedirs(STUB, exist_ok=True)
    open(os.path.join(STUB, d['slug'] + '.html'), 'w').write(f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{e(title)}</title><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{e(d.get('dek'))}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Storrs Lore">
<meta property="og:title" content="{e(d['title'])}"><meta property="og:description" content="{e(d.get('dek'))}">
<meta property="og:image" content="{e(img)}"><meta property="og:url" content="{e(SITE_URL + 'm/' + d['slug'] + '.html')}">
<meta name="twitter:card" content="summary_large_image">
<meta http-equiv="refresh" content="0; url={e(target)}"><link rel="canonical" href="{e(target)}">
<script>location.replace({json.dumps(target)})</script>
<style>body{{background:#040a18;color:#eef2f9;font:16px/1.5 system-ui,sans-serif;padding:40px}}a{{color:#8fc1ff}}</style>
</head><body><p><a href="{e(target)}">{e(d['title'])} →</a></p></body></html>
''')


def main():
    core = jload(os.path.join(SITE, 'core.json'), {})
    files = sorted(glob.glob(os.path.join(SRC, '*.json')))
    det_dir = os.path.join(SITE, 'moments')
    os.makedirs(det_dir, exist_ok=True)
    cards, built = [], set()
    for f in files:
        m = jload(f)
        if not m or not m.get('slug'):
            continue
        try:
            d = build_one(m, core)
        except Exception as e:
            print(f'moments: {os.path.basename(f)} failed ({e})')
            continue
        json.dump(d, open(os.path.join(det_dir, d['slug'] + '.json'), 'w'), separators=(',', ':'))
        stub(d)
        built.add(d['slug'])
        gm = d.get('game') or {}
        cards.append({'slug': d['slug'], 'title': d['title'], 'nickname': d.get('nickname'), 'dek': d['dek'], 'date': d['date'], 'y': d['y'], 'gid': d.get('gid'),
                      'tags': d['tags'], 'hero': d.get('hero'), 'res': gm.get('res'), 'pts': gm.get('pts'), 'opp_pts': gm.get('opp_pts'), 'ot': gm.get('ot'),
                      'opp': gm.get('opp'), 'round': gm.get('round'), 'venue': d['facts'].get('venue'), 'nVideos': len(d['videos'])})
    for old in glob.glob(os.path.join(det_dir, '*.json')) + glob.glob(os.path.join(STUB, '*.html')):
        if os.path.splitext(os.path.basename(old))[0] not in built:
            os.remove(old)
    cards.sort(key=lambda c: c['date'])
    json.dump({'moments': cards}, open(os.path.join(SITE, 'moments.json'), 'w'), separators=(',', ':'))
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(WEB, open(CACHE, 'w'), indent=0)
    print(f'moments: {len(cards)} built')
    return cards


if __name__ == '__main__':
    main()
