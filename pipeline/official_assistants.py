#!/usr/bin/env python3
"""UConn's all-time assistant coaches (1946-47 to now) from the 2026-27 Record Book, page 2 -> out/official/assistants.json

Each entry: name, the seasons listed (as spring years), and the record book's own season count. Where the count and the
list disagree, RULINGS settles it from an outside source."""
import json, os, re
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, 'cache.nosync', 'official', 'RECORD_BOOK_26-27_V2_.pdf')
OUT = os.path.join(HERE, 'out', 'official', 'assistants.json')
RULINGS = {
    # the book says "(3 seasons)" but lists two; Indiana's staff bio: "spent two seasons (2018-20)" at UConn
    'Kenya Hunter': {'seasons': [2019, 2020], 'why': 'The record book says 3 seasons but lists 2018-19 and 2019-20; his Indiana staff bio confirms two seasons (2018-20).',
                     'sources': ['https://iuhoosiers.com/sports/mens-basketball/roster/coaches/kenya-hunter/3387',
                                 'https://www.theuconnblog.com/2020/8/23/21398176/uconn-huskies-mens-basketball-assistant-coach-kenya-hunter-to-leave-for-indiana']},
}


def spring(tok):
    """'86-87' -> 1987 (the list runs 1946-47 to 2026-27)"""
    a, b = tok.split('-')
    y = int(b)
    return (1900 if y >= 47 else 2000) + y if len(b) == 2 else int(b)


def main():
    t = pymupdf.open(PDF)[1].get_text()
    t = t[:t.index('*-- list includes')]
    out, problems = [], []
    for m in re.finditer(r"([A-Z][A-Za-z.’' ]+?) \((\d+) seasons?\)\s*\n([\d\-, \s]+)", t):
        name, n, rest = m.group(1).strip(), int(m.group(2)), m.group(3)
        seasons = sorted(spring(x) for x in re.findall(r'\d{2}-\d{2}', rest))
        row = {'name': name.replace('’', "'"), 'seasons': seasons, 'book_count': n}
        r = RULINGS.get(row['name'])
        if r:
            row.update({'seasons': r['seasons'], 'ruling': r['why'], 'sources': r['sources']})
        elif n != len(seasons):
            problems.append(f'{name}: book says {n} seasons, lists {len(seasons)}')
        out.append(row)
    out.sort(key=lambda r: (r['seasons'][0], r['name']))
    heads = head_coaches(pymupdf.open(PDF)[1].get_text())
    json.dump({'source': 'UConn 2026-27 Record Book, p. 2 ("All-Time Assistant Coaches", 1946-47 to present; "All-Time Head Coaches")',
               'assistants': out, 'head_coaches': heads}, open(OUT, 'w'), indent=1)
    print(f'{len(out)} assistant coaches; unresolved count mismatches: {problems or "none"}; {len(heads)} head coach lines, '
          f"total {sum(h['w'] for h in heads)}-{sum(h['l'] for h in heads)}")


def head_coaches(t):
    """'1946-63  Hugh S. Greer  287 113 .718' -> {years, from, to, name, w, l}; spring years, 'to' None = current"""
    body = t[t.index('PCT.') + 4: t.index('Totals')]
    toks = [x.strip() for x in re.split(r'[\t\n]+', body) if x.strip() and x.strip() != 'ALL-TIME HEAD COACHES']
    rows, i = [], 0
    while i < len(toks):
        yrs = toks[i]
        if not re.fullmatch(r'Pre-1915|\d{4}(-\d{2,4})?-?', yrs):
            i += 1
            continue
        name = toks[i + 1]
        m = re.fullmatch(r'(.+?)\s+(\d+)', name)   # "George Wigton (Interim) 11" when the W shares the cell
        if m:
            name, w, l = m.group(1), int(m.group(2)), int(toks[i + 2])
            i += 4
        else:
            w, l = int(toks[i + 2]), int(toks[i + 3])
            i += 5
        if yrs == 'Pre-1915':
            fr, to = None, 1915
        else:
            a, _, b = yrs.partition('-')
            fr = int(a) + 1   # "1946-63" = 1946-47 through 1962-63
            to = None if yrs.endswith('-') else (int(a[:2] + b) if len(b) == 2 else int(b)) if b else int(a)
            if to and to < int(a):
                to += 100   # "1986-12" ends in 2012
            if not b and not yrs.endswith('-'):
                fr = to = int(a)   # "1963": an interim stint inside one season
        rows.append({'years': yrs, 'from': fr, 'to': to, 'name': name, 'w': w, 'l': l})
    return rows


if __name__ == '__main__':
    main()
