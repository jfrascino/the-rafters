#!/usr/bin/env python3
"""Parse UConn's official season-cumulative player stats into pipeline/out/official/cume.json.

Two formats, both downloaded into pipeline/cache.nosync/official/stats/:
  * StatCrew text ("## Player GP-GS Min--Avg FG-FGA Pct 3FG-FGA Pct FT-FTA Pct Off Def Tot Avg PF FO A TO Blk Stl Pts Avg"),
    as .txt (from the season-final PDFs) or inside an HTML page
  * Sidearm stats pages (uconnhuskies.com/sports/mens-basketball/stats/YYYY-YY), first table = individual stats

Unlike the record book's Letterwinner History, these carry games started, offensive/defensive rebounds and fouls,
and they list every player who appeared, not only letterwinners.
"""
import html as H, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'cache.nosync', 'official', 'stats')
OUT = os.path.join(HERE, 'out', 'official', 'cume.json')

# season (spring year) -> file, best source first
FILES = {
    2001: ['2001.html'], 2002: ['2002.cume.txt'], 2003: ['2003.final.txt'], 2005: ['2005.final.txt'],
    2007: ['2007.combine.txt'], 2008: ['2008.final.txt'],
    **{y: [f'{y}.html'] for y in range(2013, 2019)},
    **{y: [f'{y}.sidearm.html'] for y in range(2019, 2027)},
}
HDR_MAP = {'GP-GS': ('g', 'gs'), 'Min': ('mp',), 'FG-FGA': ('fg', 'fga'), '3FG-FGA': ('fg3', 'fg3a'), 'FT-FTA': ('ft', 'fta'),
           'Off': ('orb',), 'Def': ('drb',), 'Tot': ('trb',), 'PF': ('pf',), 'A': ('ast',), 'TO': ('tov',), 'Blk': ('blk',), 'Stl': ('stl',), 'Pts': ('pts',)}


def text_lines(path):
    s = open(path, errors='ignore').read()
    if path.endswith('.html') or '<html' in s[:2000].lower():
        s = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)
        s = H.unescape(re.sub(r'<[^>]+>', '', s))
    return s.splitlines()


def parse_statcrew(path):
    lines = text_lines(path)
    hi = next((i for i, l in enumerate(lines) if '##' in l and 'GP-GS' in l and 'Player' in l), None)
    if hi is None:
        return None
    hdr = lines[hi].replace('Min--Avg', 'Min Avg').replace('Min—Avg', 'Min Avg').split()
    hdr = hdr[hdr.index('Player') + 1:]
    players, total = [], None
    for l in lines[hi + 1: hi + 80]:
        m = re.match(r'^\s*(\d{1,2})\s+(.+?)[.\s]+(\d+-\d+\s+\d+\s+[\d.]+\s+.*)$', l)
        is_total = re.match(r'^\s*Total\.*\s+(\d+-?\d*\s+.*)$', l)
        if not m and not is_total:
            if players and re.match(r'^\s*(Team|Opponents|Total)', l) is None and not l.strip().startswith(('Conference', '-')) and l.strip() and not re.match(r'^\s*\d', l):
                pass
            continue
        num, name, rest = (m.group(1), m.group(2).strip(' .'), m.group(3)) if m else (None, 'Total', is_total.group(1))
        toks = rest.split()
        rec, k = {}, 0
        for h in hdr:
            if k >= len(toks):
                break
            t = toks[k]
            if h in HDR_MAP:
                keys = HDR_MAP[h]
                if len(keys) == 2:
                    if '-' not in t:
                        if h == 'GP-GS' and num is None and t.isdigit():   # the Total row lists games without starts
                            rec['g'] = int(t)
                            k += 1
                            continue
                        rec = None
                        break
                    a, b = t.split('-', 1)
                    rec[keys[0]], rec[keys[1]] = int(a), (int(b) if b.isdigit() else None)
                else:
                    rec[keys[0]] = int(float(t)) if re.match(r'^-?\d+(\.\d+)?$', t) else None
            k += 1
        if not rec:
            continue
        if num is None:
            total = rec
        else:
            rec.update({'num': num, 'name': name})
            players.append(rec)
    return {'players': players, 'total': total}


def parse_sidearm(path):
    s = open(path, errors='ignore').read()
    t = re.findall(r'<table.*?</table>', s, re.S)[0]
    out, total = [], None
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        cells = [H.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c))).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
        if len(cells) != 26 or cells[0] in ('#', 'Player uniform'):
            continue
        i = lambda k: int(cells[k]) if re.match(r'^-?\d+$', cells[k]) else None
        rec = {'g': i(2), 'gs': i(3), 'mp': i(4), 'pts': i(6), 'fg': i(8), 'fga': i(9), 'fg3': i(11), 'fg3a': i(12), 'ft': i(14), 'fta': i(15),
               'orb': i(17), 'drb': i(18), 'trb': i(19), 'pf': i(21), 'ast': i(22), 'tov': i(23), 'stl': i(24), 'blk': i(25)}
        if cells[0] == 'Total':
            total = rec
        elif cells[0] != 'Opponents' and cells[1]:
            rec.update({'num': cells[0].lstrip('0') or '0', 'name': cells[1]})
            out.append(rec)
    return {'players': out, 'total': total}


def check(rec):
    """Arithmetic a correct stat line must satisfy."""
    bad = []
    if None not in (rec.get('fg'), rec.get('fg3'), rec.get('ft'), rec.get('pts')) and 2 * rec['fg'] + rec['fg3'] + rec['ft'] != rec['pts']:
        bad.append('pts != 2*FG + 3P + FT')
    if None not in (rec.get('orb'), rec.get('drb'), rec.get('trb')) and rec['orb'] + rec['drb'] != rec['trb']:
        bad.append('OREB + DREB != REB')
    for a, b in (('fg', 'fga'), ('fg3', 'fg3a'), ('ft', 'fta'), ('fg3', 'fg')):
        if None not in (rec.get(a), rec.get(b)) and rec[a] > rec[b]:
            bad.append(f'{a} > {b}')
    return bad


def main():
    out = {}
    for y, files in sorted(FILES.items()):
        for f in files:
            p = os.path.join(D, f)
            if not os.path.exists(p):
                continue
            r = parse_sidearm(p) if 'sidearm' in f else parse_statcrew(p)
            if not r or not r['players']:
                print(f'{y}: could not parse {f}')
                continue
            for rec in r['players']:
                rec['bad'] = check(rec) or None
            tot = r['total'] or {}
            sums = {k: sum((pl.get(k) or 0) for pl in r['players']) for k in ('pts', 'fg', 'fga', 'fg3', 'ft', 'ast', 'stl', 'blk')}
            mism = {k: (sums[k], tot.get(k)) for k in sums if tot.get(k) is not None and sums[k] != tot[k]}
            r.update({'src': f, 'sum_vs_total': mism or None})
            out[y] = r
            nbad = sum(1 for rec in r['players'] if rec['bad'])
            print(f"{y}: {f:22s} {len(r['players']):2d} players  arithmetic issues: {nbad}  player sums vs team total: {mism or 'match'}")
            break
    json.dump(out, open(OUT, 'w'), indent=1)


if __name__ == '__main__':
    main()
