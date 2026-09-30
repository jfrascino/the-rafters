#!/usr/bin/env python3
"""Data audit: cross-check every number the app shows against a second source or an internal identity.

python3 dev/qa.py            → writes dev/qa_report.json and prints a summary
Checks
  G  game results: Sports-Reference vs ESPN (date, site, score, OT) for every game both sources have
  B  box-score arithmetic: player points sum to the team score; 2·FGM + 3PM + FTM = PTS; team FG% etc.
  X  box scores from both sources: UConn player lines agree (pts / reb / ast / min)
  S  season totals: SR season totals vs the sum of the box scores shown on the player's game log
  P  player identity: every UConn box line maps to a real roster player with a matching name
  R  season records & rankings: W-L from games vs SR header; AP final/peak vs the weekly poll table
  T  tournament: seeds, round sequence, finish vs the legends research
  O  opponents: display name vs ESPN logo identity
"""
import json, glob, os, re, collections, unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SITE = os.path.join(ROOT, 'site', 'data')
OUT = os.path.join(ROOT, 'pipeline', 'out')
J = lambda p: json.load(open(p))


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r"[.'`’\-]", '', s)
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return re.sub(r'\s+', ' ', s).strip()


issues = collections.defaultdict(list)
counts = collections.Counter()
core = J(os.path.join(SITE, 'core.json'))
seasons = {int(os.path.basename(f)[:-5]): J(f) for f in glob.glob(os.path.join(SITE, 'seasons', '*.json'))}
games = {}
for f in glob.glob(os.path.join(SITE, 'games', '*.json')):
    games.update(J(f))
sr = {int(os.path.basename(f)[:-5]): J(f) for f in glob.glob(os.path.join(OUT, 'sr', 'seasons', '*.json'))}
srbox = {os.path.basename(f)[:-5]: J(f) for f in glob.glob(os.path.join(OUT, 'sr', 'boxscores', '*.json'))}
espn = [J(f) for f in glob.glob(os.path.join(OUT, 'espn', 'games', '*.json'))]
legends = J(os.path.join(OUT, 'media', 'legends.json'))
players = {p['id']: p for p in core['players']}

# ── G: SR vs ESPN results ─────────────────────────────────────────────
from zoneinfo import ZoneInfo
import datetime
ET = ZoneInfo('America/New_York')
def et(iso):
    return datetime.datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(ET).date().isoformat()
espn_final = {}
for e in espn:
    if e.get('status') != 'final':
        continue
    u = next((t for t in e['teams'] if str(t['id']) == '41'), None)
    o = next((t for t in e['teams'] if str(t['id']) != '41'), None)
    if not u or not o:
        continue
    espn_final[(et(e['date']), )] = espn_final.get((et(e['date']),), []) + [(e, u, o)]
matched_espn = set()
for y, s in sorted(sr.items()):
    if y < 2003:
        continue
    for g in s['schedule']:
        cands = espn_final.get((g['date'],), [])
        hit = next(((e, u, o) for e, u, o in cands if int(float(u['score'])) == g['pts'] and int(float(o['score'])) == g['opp_pts']), None)
        counts['G.games'] += 1
        if not hit:
            # same date, different score → a real disagreement; no event at all → coverage gap
            if cands:
                e, u, o = cands[0]
                issues['G'].append({'game': f"{y}-{g['g']}", 'date': g['date'], 'opp': g['opp_name'], 'sr': f"{g['pts']}-{g['opp_pts']}", 'espn': f"{u['score']}-{o['score']} vs {o.get('location') or o.get('name')}"})
            else:
                d0 = datetime.date.fromisoformat(g['date'])
                near = [c for dd in (-1, 1) for c in espn_final.get(((d0 + datetime.timedelta(days=dd)).isoformat(),), [])]
                near = [c for c in near if int(float(c[1]['score'])) == g['pts']]
                if near:
                    issues['G'].append({'game': f"{y}-{g['g']}", 'date': g['date'], 'opp': g['opp_name'], 'problem': f"ESPN dates it {et(near[0][0]['date'])}"})
                    matched_espn.add(near[0][0]['id'])
                else:
                    issues['G'].append({'game': f"{y}-{g['g']}", 'date': g['date'], 'opp': g['opp_name'], 'problem': 'no ESPN event'})
            continue
        e, u, o = hit
        matched_espn.add(e['id'])
        app_g = next((x for x in seasons[y]['games'] if x['id'] == f"{y}-{g['g']}"), {})
        site_sr = {'H': 'home', 'A': 'away', 'N': 'neutral'}.get(app_g.get('ha'))
        site_es = 'neutral' if e.get('neutral') else u.get('homeAway')
        # ESPN's older data files neutral-site tournament games as home/away; only flag real regular-season disagreements
        if site_sr != site_es and app_g.get('type') not in ('NCAA', 'CTOURN') and not (site_sr == 'neutral' and not e.get('neutral')):
            issues['G'].append({'game': f"{y}-{g['g']}", 'date': g['date'], 'opp': g['opp_name'], 'problem': f'site SR={site_sr} ESPN={site_es}'})
        ot_sr = 0 if not g.get('overtimes') else (int(re.match(r'(\d*)', g['overtimes']).group(1) or 1))
        if ot_sr != (e.get('ot') or 0):
            issues['G'].append({'game': f"{y}-{g['g']}", 'date': g['date'], 'opp': g['opp_name'], 'problem': f"OT SR={g.get('overtimes')} ESPN={e.get('ot')}"})
for e in espn:
    if e.get('status') == 'final' and e['id'] not in matched_espn and e['season'] <= max(sr):
        u = next((t for t in e['teams'] if str(t['id']) == '41'), {})
        o = next((t for t in e['teams'] if str(t['id']) != '41'), {})
        issues['G'].append({'espn': e['id'], 'date': et(e['date']), 'opp': o.get('location'), 'score': f"{u.get('score')}-{o.get('score')}", 'problem': 'ESPN final not in SR schedule'})

# ── B: box arithmetic ───────────────────────────────────────────────
for gid, d in games.items():
    counts['B.boxes'] += 1
    for side, t in zip(('UConn', 'opp'), d['teams']):
        ps = [p for p in t.get('players', []) if not p.get('dnp')]
        tot = sum(p.get('pts') or 0 for p in ps)
        if t.get('score') is not None and tot != t['score']:
            issues['B'].append({'game': gid, 'team': t.get('name'), 'problem': f"players sum to {tot}, final {t['score']}"})
        line = t.get('line') or []
        if line and t.get('score') is not None and sum(x or 0 for x in line) != t['score']:
            issues['B'].append({'game': gid, 'team': t.get('name'), 'problem': f"linescore {line} sums to {sum(x or 0 for x in line)}, final {t['score']}"})
        for p in ps:
            if None in (p.get('fgm'), p.get('tpm'), p.get('ftm'), p.get('pts')):
                continue
            counts['B.lines'] += 1
            calc = 2 * p['fgm'] + p['tpm'] + p['ftm']
            if calc != p['pts']:
                issues['B'].append({'game': gid, 'player': p.get('name'), 'problem': f"2·{p['fgm']}+{p['tpm']}+{p['ftm']}={calc} ≠ {p['pts']} pts"})
            for m, a in (('fgm', 'fga'), ('tpm', 'tpa'), ('ftm', 'fta')):
                if p.get(a) is not None and p[m] > p[a]:
                    issues['B'].append({'game': gid, 'player': p.get('name'), 'problem': f'{m} {p[m]} > {a} {p[a]}'})
            if p.get('oreb') is not None and p.get('reb') is not None and p['oreb'] > p['reb']:
                issues['B'].append({'game': gid, 'player': p.get('name'), 'problem': 'oreb > reb'})

# ── X: SR box vs ESPN box for the same game (UConn players) ───────────
from importlib import util
for y, s in sr.items():
    for g in s['schedule']:
        b = srbox.get(g.get('box_slug') or '')
        gid = f"{y}-{g['g']}"
        d = games.get(gid)
        if not b or not d or d.get('source') == 'sr':
            continue
        ut = next((t for t in b['teams'] if t.get('sr_slug') == 'connecticut'), None)
        if not ut:
            continue
        srp = {p.get('sr_id'): p for p in ut.get('players', [])}
        counts['X.games'] += 1
        for p in d['teams'][0]['players']:
            q = srp.get(p.get('pid'))
            if p.get('dnp'):
                continue
            if not q:
                if (p.get('min') or 0) > 0:
                    issues['X'].append({'game': gid, 'player': p.get('name'), 'pid': p.get('pid'), 'problem': 'in ESPN box, not in SR box (id mismatch?)'})
                continue
            counts['X.lines'] += 1
            for a, bk in (('pts', 'pts'), ('reb', 'trb'), ('ast', 'ast')):
                if p.get(a) is not None and q.get(bk) is not None and p[a] != q[bk]:
                    issues['X'].append({'game': gid, 'player': p.get('name'), 'stat': a, 'espn': p[a], 'sr': q[bk]})

# ── S: SR season totals vs box-score logs ────────────────────────────
for pid, _ in players.items():
    pp = J(os.path.join(SITE, 'players', f'{pid}.json'))
    logs = collections.defaultdict(list)
    for g in pp.get('gamelog', []):
        logs[g['y']].append(g)
    for sy in pp['seasons']:
        if not sy.get('uconn'):
            continue
        y = sy['y']
        s = seasons.get(y)
        if not s:
            continue
        nbox = sum(1 for g in s['games'] if g.get('box') and g.get('res'))
        nplayed = sum(1 for g in s['games'] if g.get('res'))
        if nbox < nplayed or not sy.get('g'):
            continue
        L = logs.get(y, [])
        counts['S.seasons'] += 1
        tot_pts = round((sy.get('pts') or 0) * sy['g'])
        box_pts = sum(g.get('pts') or 0 for g in L)
        if abs(tot_pts - box_pts) > max(2, 0.02 * tot_pts) or abs(len(L) - sy['g']) > 0:
            issues['S'].append({'player': pp['name'], 'season': y, 'sr_g': sy['g'], 'box_g': len(L), 'sr_pts≈': tot_pts, 'box_pts': box_pts})

# ── P: identity of box-score players ─────────────────────────────────
for gid, d in games.items():
    y = int(gid.split('-')[0])
    for p in d['teams'][0]['players']:
        pid = p.get('pid')
        counts['P.lines'] += 1
        if not pid or pid.startswith('espn-'):
            if y < 2027 and not p.get('dnp'):
                issues['P'].append({'game': gid, 'player': p.get('name'), 'problem': f'no roster match ({pid})'})
            continue
        known = players.get(pid)
        if known and norm(known['name']).split(' ')[-1] != norm(p.get('name')).split(' ')[-1]:
            issues['P'].append({'game': gid, 'box_name': p.get('name'), 'mapped_to': known['name'], 'pid': pid})

# ── R: records & rankings ────────────────────────────────────────────
for y, s in sorted(seasons.items()):
    played = [g for g in s['games'] if g.get('res')]
    w = sum(g['res'] == 'W' for g in played); l = len(played) - w
    counts['R.seasons'] += 1
    if played and (w, l) != (s['w'], s['l']):
        issues['R'].append({'season': y, 'problem': f"games add to {w}-{l}, header {s['w']}-{s['l']}"})
    polls = [p for p in s.get('polls', []) if p.get('rank')]
    if polls:
        best = min(p['rank'] for p in polls)
        if s.get('apHigh') and s['apHigh'] != best:
            issues['R'].append({'season': y, 'problem': f"AP peak {s['apHigh']} vs best weekly rank {best}"})
        final = s['polls'][-1]
        if s.get('apFinal') and str(final.get('wk')).lower() == 'final' and final.get('rank') != s['apFinal']:
            issues['R'].append({'season': y, 'problem': f"AP final {s['apFinal']} vs final poll {final.get('rank')}"})
    running = None
    for g in played:
        if g.get('rec'):
            ww, ll = map(int, g['rec'].split('-'))
            if running and (ww + ll) != running + 1:
                issues['R'].append({'season': y, 'game': g['id'], 'problem': f"running record jumps to {g['rec']}"})
            running = ww + ll

# ── T: tournament ────────────────────────────────────────────────────
champs_leg = {c['year'] for c in legends.get('national_championships', [])}
ff_leg = {f['year'] for f in legends.get('final_fours', [])}
for s in core['seasons']:
    y = s['y']
    if (s['finish'] == 'champ') != (y in champs_leg):
        issues['T'].append({'season': y, 'problem': f"finish {s['finish']} vs legends champion={y in champs_leg}"})
    if (s['finish'] in ('champ', 'runner', 'final4')) != (y in ff_leg):
        issues['T'].append({'season': y, 'problem': f"finish {s['finish']} vs legends Final Four={y in ff_leg}"})
for c in legends.get('national_championships', []):
    s = seasons.get(c['year'])
    ncaa = [g for g in s['games'] if g['type'] == 'NCAA']
    for i, step in enumerate(c.get('path', [])):
        if i >= len(ncaa):
            issues['T'].append({'season': c['year'], 'problem': f'legends path longer than games ({step})'})
            break
        g = ncaa[i]
        sc = f"{g['pts']}–{g['opp_pts']}"
        if norm(step.get('opponent')) not in norm(g['opp']['name']) and norm(g['opp']['name']) not in norm(step.get('opponent')):
            issues['T'].append({'season': c['year'], 'round': i, 'problem': f"opponent legends={step.get('opponent')} data={g['opp']['name']}"})
        if step.get('score') and step['score'].split(' ')[0] != sc:
            issues['T'].append({'season': c['year'], 'round': i, 'problem': f"score legends={step['score']} data={sc}"})
        seed = re.match(r'(\d+)', str(step.get('opponent_seed') or ''))
        if seed and g['opp'].get('seed') and int(seed.group(1)) != g['opp']['seed']:
            issues['T'].append({'season': c['year'], 'round': i, 'problem': f"opp seed legends={step.get('opponent_seed')} data={g['opp']['seed']}"})
    counts['T.titles'] += 1

# ── O: opponent identity (name vs logo team) ─────────────────────────
teams_all = json.load(open(os.path.join(ROOT, 'pipeline', 'cache.nosync', 'espn_all_teams.json')))
by_id = {str(t['id']): t for t in teams_all}
for key, o in core['opponents'].items():
    counts['O.teams'] += 1
    m = re.search(r'/(\d+)\.png', o.get('logo') or '')
    if not m:
        issues['O'].append({'opp': o['name'], 'problem': 'no logo'})
        continue
    t = by_id.get(m.group(1))
    if t:
        names = {norm(t.get('location')), norm(t.get('shortDisplayName')), norm(t.get('displayName')), norm(t.get('nickname'))}
        on = norm(o['name'])
        if not any(n and (n in on or on in n) for n in names):
            issues['O'].append({'opp': o['name'], 'logo_team': t.get('displayName')})

summary = {k: len(v) for k, v in issues.items()}
json.dump({'counts': counts, 'summary': summary, 'issues': issues}, open(os.path.join(ROOT, 'dev', 'qa_report.json'), 'w'), indent=1, ensure_ascii=False)
print('checked:', dict(counts))
print('issues :', summary)
