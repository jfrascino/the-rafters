#!/usr/bin/env python3
"""UConn record book series pages: every opponent's all-time record vs UConn -> pipeline/out/official/series_records.json"""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
L = open(os.path.join(HERE, 'cache.nosync', 'official', 'recordbook_pypdf.txt'), errors='ignore').read().splitlines()


def main():
    start = next(i for i, l in enumerate(L) if l.strip().startswith('Air Force ('))
    end = next(i for i in range(start, len(L)) if 'NCAA TOURNAMENT REGION AND SEED' in L[i] or 'UCONN VS. NATIONALLY-RANKED' in L[i])
    out = {}
    for t in (l.strip() for l in L[start:end]):
        m = re.match(r"^(.+?) \((\d+)-(\d+)\)\s*$", t)
        if m and not re.search(r'\d/\d', t):
            out[m.group(1).strip()] = {'w': int(m.group(2)), 'l': int(m.group(3))}
    json.dump({'_source': "UConn 2026-27 Record Book, series records (through 2025-26)", 'series': out},
              open(os.path.join(HERE, 'out', 'official', 'series_records.json'), 'w'), indent=1)
    print(len(out), 'opponents;', sum(v['w'] for v in out.values()), '-', sum(v['l'] for v in out.values()))


if __name__ == '__main__':
    main()
