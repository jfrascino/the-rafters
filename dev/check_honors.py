#!/usr/bin/env python3
"""Player honors on the site vs. the 2026-27 record book's honors pages (pp. 57-58)."""
import json, re, glob, os, collections, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, 'pipeline/cache.nosync/official')
T57 = open(os.path.join(C, 'rb_p57.txt')).read().splitlines()
T58 = open(os.path.join(C, 'rb_p58.txt')).read().splitlines()


def nn(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?', '', s)
    return re.sub(r'[^a-z]', '', s)


def season_of(yy):   # "1993-94" -> 1994 ; "2011" -> 2011
    m = re.match(r'(\d{4})-(\d{2})', yy)
    return int(m.group(1)) + 1 if m else int(yy)


rb = collections.defaultdict(set)   # (player key, award) -> {season}
# ── all-conference lists (Big East, then AAC) on p58
conf, season, pending = None, None, None
for ln in T58:
    t = ln.replace('\t', ' ').strip()
    if 'BIG EAST ALL-CONFERENCE' in t: conf = 'BE'; continue
    if 'AAC ALL-CONFERENCE' in t: conf = 'AAC'; continue
    if conf is None: continue
    if re.fullmatch(r'\d{4}-\d{2}', t): season = season_of(t); pending = None; continue
    if re.match(r'^[A-Z][A-Z ]+$', t) and len(t) > 6: conf = None if 'ALL-CONFERENCE' not in t else conf; continue
    teams = re.findall(r'(First Team|Second Team|Third Team|Hon\.? Mention|Honorable Mention|All-Rookie|All-Freshman)', t)
    if not re.match(r'^(First|Second|Third|Hon|Honorable|All-|Team)', t):
        nm = re.split(r',|\t|\s{2,}|\((?:unan)|(?:First|Second|Third) Team|Hon\.? Mention|Honorable|All-Rookie|All-Freshman', t)[0].strip()
        nm = re.sub(r'\s+(Jr|Sr)\.?$', '', nm).strip(' .')
        if re.match(r"^[A-Z][A-Za-z.'’\-]+(?: [A-Z][A-Za-z.'’\-]+)+$", nm):
            pending = nm
    if pending and teams and season:
        for tm in teams:
            kind = 'freshman' if 'Rookie' in tm or 'Freshman' in tm else 'team'
            rb[(nn(pending), f'{conf}-{kind}')].add(season)
            if kind == 'team':
                rb[(nn(pending), f'{conf}-team-{"hm" if "Hon" in tm else "123"}')].add(season)
# ── award lists on p57/p58: "Name, 1993-94, 1997-98"
AWARDS = {'BIG EAST PLAYER OF THE YEAR': 'BE-POY', 'BIG EAST ROOKIE OF THE YEAR': 'BE-ROY', 'BIG EAST DEFENSIVE POY': 'BE-DPOY',
          'BIG EAST MOST IMPROVED PLAYER': 'BE-MIP', 'BIG EAST SIXTH MAN OF THE YEAR': 'BE-6MOY', 'AAC PLAYER OF THE YEAR': 'AAC-POY',
          'AAC ROOKIE OF THE YEAR': 'AAC-ROY', 'AAC DEFENSIVE POY': 'AAC-DPOY', 'AAC MOST IMPROVED PLAYER': 'AAC-MIP'}
for T in (T57, T58):
    cur = None
    for ln in T:
        t = ln.strip()
        if t in AWARDS: cur = AWARDS[t]; continue
        if re.match(r'^[A-Z][A-Z ]{6,}$', t): cur = None; continue
        if cur:
            m = re.match(r"^([A-Z][A-Za-z.'’\- ]+?),\s*((?:\d{4}-\d{2}(?:,\s*)?)+)", t)
            if m:
                for yy in re.findall(r'\d{4}-\d{2}', m.group(2)):
                    rb[(nn(m.group(1)), cur)].add(season_of(yy))

# ── site honors
SITE = collections.defaultdict(lambda: collections.defaultdict(lambda: {'years': set(), 'count': 0}))
names = {}
LABEL = {'All-Big East': 'BE-team', 'Big East All-Freshman': 'BE-freshman', 'All-AAC': 'AAC-team', 'AAC All-Freshman': 'AAC-freshman',
         'Big East POY': 'BE-POY', 'Big East ROY': 'BE-ROY', 'Big East DPOY': 'BE-DPOY', 'Big East MIP': 'BE-MIP', 'Big East 6MOY': 'BE-6MOY',
         'AAC POY': 'AAC-POY', 'AAC ROY': 'AAC-ROY', 'AAC DPOY': 'AAC-DPOY', 'AAC MIP': 'AAC-MIP'}
for f in glob.glob(os.path.join(ROOT, 'site/data/players/*.json')):
    d = json.load(open(f))
    k = nn(d['name']); names[k] = d['name']
    for h in d.get('honors') or []:
        m = re.match(r'^(?:(\d{4}-\d{2})|(\d+)x)\s+(.+)$', h)
        if not m or m.group(3) not in LABEL: continue
        e = SITE[k][LABEL[m.group(3)]]
        if m.group(1): e['years'].add(season_of(m.group(1))); e['count'] += 1
        else: e['count'] += int(m.group(2))

alias = {nn('Donny Marshall'): nn('Donny Marshall'), nn('Solo Ball'): nn('Solomon Ball'), nn('Jeremy Lamb'): nn('Jeremy Lamb')}
problems = []
keys = set(k for k, _ in rb) | set(SITE)
for (pk, award), yrs in sorted(rb.items()):
    if award.endswith('-123') or award.endswith('-hm'): continue
    sk = alias.get(pk, pk)
    if sk not in names:
        cand = [k for k in names if k.endswith(pk[-6:]) and k[:3] == pk[:3]]
        sk = cand[0] if len(cand) == 1 else sk
    site = SITE.get(sk, {}).get(award)
    n_site = site['count'] if site else 0
    n_rb = len(yrs)
    if award.endswith('-team'):
        n_123 = len(rb.get((pk, award + '-123'), set()))
        ok = n_site in (n_rb, n_123)
        if not ok: problems.append((names.get(sk, pk), award, f'record book {n_rb} ({n_123} excluding honorable mention) {sorted(yrs)}', f'site {n_site}'))
    elif n_site != n_rb:
        problems.append((names.get(sk, pk), award, f'record book {n_rb} {sorted(yrs)}', f'site {n_site}'))
# site honors the record book doesn't list (UConn seasons only)
for sk, aw in SITE.items():
    for award, e in aw.items():
        if not any(k == sk or alias.get(k) == sk for k, a in rb if a == award) and e['count']:
            problems.append((names.get(sk, sk), award, 'record book: none', f"site {e['count']} {sorted(e['years'])}"))
print(f'{len(problems)} disagreements')
for p in sorted(problems): print('  ', p)
