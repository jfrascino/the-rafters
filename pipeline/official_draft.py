#!/usr/bin/env python3
"""UConn record book NBA DRAFT HISTORY -> pipeline/out/official/draft.json (name, round, pick, team, year).
The record book's team column is where the player went (after any draft-night trade); Sports-Reference keeps the team
that made the pick, so the build shows both when they differ."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'official', 'draft.json')


def main():
    import pymupdf
    doc = pymupdf.open(os.path.join(HERE, 'cache.nosync', 'official', 'RECORD_BOOK_26-27_V2_.pdf'))
    page = next(p for p in doc if 'NBA DRAFT HISTORY' in p.get_text())
    L = [l.strip() for l in page.get_text().splitlines()]
    if 'UCONN NBA UNDRAFTED FREE AGENTS' in L:
        L = L[:L.index('UCONN NBA UNDRAFTED FREE AGENTS')]
    L = [l for l in L if l and l not in ('NAME', 'RD', '#', 'TEAM SELECTED BY', 'YEAR') and 'NBA DRAFT HISTORY' not in l and 'UCONN MEN' not in l and 'NATIONAL CHAMPIONS' not in l]
    out, i = [], 0
    while i + 4 < len(L):
        nm, rd, pk, tm, yr = L[i:i + 5]
        if re.fullmatch(r'\d+(st|nd|rd|th)', rd) and re.fullmatch(r'\d+', pk) and re.fullmatch(r'\d{4}', yr):
            out.append({'name': re.sub(r'^[&%#*^]+\s*', '', nm).strip(), 'round': int(re.match(r'\d+', rd).group()), 'pick': int(pk),
                        'team': tm.strip().replace('Horners', 'Hornets'), 'year': int(yr)})
            i += 5
        else:
            i += 1
    json.dump({'_source': 'UConn 2026-27 Record Book, NBA Draft History', 'picks': out}, open(OUT, 'w'), indent=1)
    print(len(out), 'draft picks')


if __name__ == '__main__':
    main()
