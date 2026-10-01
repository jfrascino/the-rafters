#!/usr/bin/env python3
"""UConn's official records by building, from the 2026-27 Record Book p. 65 -> out/official/venue_records.json

Parsed (not retyped) so a new edition can be dropped in. Every "N games ... W-L" line is checked: when W + L != N the
line is kept with a note instead of silently picking a number."""
import json, os, re
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, 'cache.nosync', 'official', 'RECORD_BOOK_26-27_V2_.pdf')
OUT = os.path.join(HERE, 'out', 'official', 'venue_records.json')
HEADS = [('greer', r'Record at Storrs Field House \((\d{4})-(\d{2})\)'), ('gampel', r'Record at Harry A\. Gampel Pavilion'),
         ('hartford_arena', r'Record at XL \(Hartford Civic\) Center'), ('bridgeport_arena', r'Record at Webster Bank Arena'),
         ('new_haven_coliseum', r'Record at New Haven Coliseum')]
STREAKS = [('hartford_arena', r'Longest Hartford \(PBA/XL/HCC\) Winning Streak'), ('gampel', r'Longest Gampel Pavilion Winning Streak'),
           ('home', r'Longest Home Winning Streak'), ('home_losing', r'Longest Home Losing Streak')]


def main():
    t = pymupdf.open(PDF)[64].get_text()
    lines = [l.strip() for l in t.splitlines()]
    out = {'source': 'UConn 2026-27 Record Book, p. 65', 'buildings': {}, 'streaks': {}}
    for key, pat in HEADS:
        i = next(k for k, l in enumerate(lines) if re.search(pat, l))
        rows = []
        for l in lines[i + 1:i + 3]:
            m = re.match(r'(\d+) games?\s*(\((.*?)\))?[ .]*?(\d+)-(\d+)\s*$', l)
            if not m:
                break
            n, note, w, lo = int(m.group(1)), m.group(3), int(m.group(4)), int(m.group(5))
            rows.append({'games': n, 'w': w, 'l': lo, 'what': note, 'misprint': None if w + lo == n else f'the book lists {n} games, but {w} + {lo} = {w + lo}'})
        out['buildings'][key] = {'heading': lines[i], 'lines': rows}
    for key, pat in STREAKS:
        i = next(k for k, l in enumerate(lines) if re.search(pat, l))
        rows = []
        for l in lines[i + 1:i + 4]:
            m = re.match(r'(\d+) games[ .]*?(\d{4}-\d{2}(?: through \d{4}-\d{2})?|\d{4}-\d{2,4})\s*$', l)
            if not m:
                break
            rows.append({'games': int(m.group(1)), 'when': m.group(2)})
        out['streaks'][key] = rows
    json.dump(out, open(OUT, 'w'), indent=1)
    for k, v in out['buildings'].items():
        print(k, [(r['games'], f"{r['w']}-{r['l']}", r['what'], r['misprint']) for r in v['lines']])
    print(out['streaks'])


if __name__ == '__main__':
    main()
