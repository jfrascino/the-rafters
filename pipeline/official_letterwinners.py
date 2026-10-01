#!/usr/bin/env python3
"""Parse the "Letterwinner History" (every letterwinner's season-by-season stats) out of UConn's official
record book / media guides into pipeline/out/official/letterwinners.json.

Sources (text already extracted from the PDFs into pipeline/cache.nosync/official/):
  rb2027  recordbook_pypdf.txt            2026-27 Record Book (through 2025-26)  <- primary
  mg2010  stats/mg0910_s4_records.txt     2009-10 Media Guide (through 2008-09)  <- cross-check
  mg2009  stats/mg0809_letterwinners.txt  2008-09 Yearbook   (through 2007-08)  <- cross-check

Each season line carries 19 columns:
  G FG FGA FG% 3P 3PA 3P% FT FTA FT% REB RPG AST TO BLK STL MIN PTS PPG
"-" means the stat wasn't kept; "---" stands for all three 3-point columns before the line existed.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, 'cache.nosync', 'official')
OUT = os.path.join(HERE, 'out', 'official', 'letterwinners.json')
SOURCES = [
    ('rb2027', os.path.join(C, 'recordbook_pypdf.txt'), "UConn Men's Basketball 2026-27 Record Book, Letterwinner History"),
    ('mg2010', os.path.join(C, 'stats', 'mg0910_s4_records.txt'), "UConn 2009-10 Media Guide, Letterwinner History"),
    ('mg2009', os.path.join(C, 'stats', 'mg0809_letterwinners.txt'), "UConn 2008-09 Yearbook, Letterwinner History"),
]
COLS = ['g', 'fg', 'fga', 'fg_pct', 'fg3', 'fg3a', 'fg3_pct', 'ft', 'fta', 'ft_pct', 'trb', 'rpg', 'ast', 'tov', 'blk', 'stl', 'mp', 'pts', 'ppg']
SEASON = re.compile(r'^\s*([*#^+]*)\s*(\d{4})-(\d{2})([*#^+]*)\s+(.*)$')
NAME = re.compile(r"^([A-Z][A-Za-z'’.\- ]+?),\s*([A-Z][A-Za-z'’.\-\" ]+?)\s*$")


def is_name(m):
    """'McKAY, MICHAEL', 'DePRIEST, LYMAN', "O'BRIEN, ROBERT": a surname that is mostly capitals"""
    letters = [c for c in m.group(1) if c.isalpha()]
    return len(letters) >= 2 and sum(c.isupper() for c in letters) / len(letters) >= 0.6


def num(tok):
    if tok in ('-', '--', '—', 'NA', 'N/A', ''):
        return None
    tok = tok.replace(',', '')
    try:
        return float(tok) if '.' in tok else int(tok)
    except ValueError:
        return 'BAD:' + tok


def parse_line(rest):
    toks = rest.replace('---', '- - -').replace('—', '-').split()
    vals = [num(t) for t in toks]
    return vals


def parse(path, src):
    players, cur, skipped = [], None, []
    text = open(path, errors='ignore').read()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('=====PAGE') or 'NATIONAL CHAMPIONS' in line or '/ HISTORY' in line or 'YEARBOOK' in line.upper() and len(line) > 40:
            continue
        if '(MGR)' in line or '(MANAGER)' in line.upper():
            cur = None
            continue
        nm_line = re.sub(r'\s*\(.*\)\s*$', '', line)   # "KARABAN, ALEX (Enrolled 2nd semester 2021-22 and redshirted)"
        m = NAME.match(nm_line)
        if m and not re.search(r'\d', nm_line) and is_name(m):
            cur = {'name': f"{m.group(1).strip()}, {m.group(2).strip()}", 'last': m.group(1).strip(), 'first': m.group(2).strip(), 'seasons': [], 'src': src}
            players.append(cur)
            continue
        if cur is None:
            continue
        sm = SEASON.match(line)
        if sm:
            y = int(sm.group(2)) + 1
            vals = parse_line(sm.group(5))
            flags = (sm.group(1) + sm.group(4)).strip()
            rec = {'y': y, 'label': f"{sm.group(2)}-{sm.group(3)}", 'flags': flags or None, 'raw': line}
            if len(vals) == 19:
                rec.update(dict(zip(COLS, vals)))
            else:
                rec['bad'] = f'{len(vals)} columns'
                skipped.append((cur['name'], line))
            cur['seasons'].append(rec)
            continue
        if re.match(r'^TOTALS?\b', line.upper()):
            vals = parse_line(line.split(None, 1)[1] if ' ' in line else '')
            cur['totals'] = dict(zip(COLS, vals)) if len(vals) == 19 else {'bad': line}
            cur = None   # a TOTALS line closes the player's block (keeps later tables from attaching to the last name)
            continue
    players = [p for p in players if p['seasons']]
    return players, skipped


def main():
    out = {'_sources': {k: d for k, _, d in SOURCES}, 'players': {}}
    for key, path, _ in SOURCES:
        if not os.path.exists(path):
            continue
        players, skipped = parse(path, key)
        out['players'][key] = players
        n = sum(len(p['seasons']) for p in players)
        print(f"{key}: {len(players)} letterwinners, {n} season lines, {len(skipped)} lines not 19 columns")
        for nm, ln in skipped[:12]:
            print('   ?', nm, '|', ln)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), indent=1)


if __name__ == '__main__':
    main()
