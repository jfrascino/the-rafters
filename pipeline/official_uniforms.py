#!/usr/bin/env python3
"""UConn record book "ALL-TIME UNIFORM NUMBERS" -> pipeline/out/official/uniforms.json: {spring year: [{"name", "num"}]}.
The list runs 24..77, then 00..23; each line is "Name ....... years" (years = the seasons he wore that number)."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'cache.nosync', 'official', 'recordbook_pypdf.txt')
OUT = os.path.join(HERE, 'out', 'official', 'uniforms.json')


def page_text():
    """the uniform list is one dense page; PyMuPDF keeps every column (the plain-text extraction dropped part of #23)"""
    try:
        import pymupdf
        doc = pymupdf.open(os.path.join(HERE, 'cache.nosync', 'official', 'RECORD_BOOK_26-27_V2_.pdf'))
        for pg in doc:
            t = pg.get_text()
            if 'ALL-TIME UNIFORM NUMBERS' in t and 'Clifford Robinson' in t:
                return t.splitlines()
    except Exception as e:
        print('pymupdf unavailable, falling back to text extraction:', e)
    L = open(SRC, errors='ignore').read().splitlines()
    i0 = next(i for i in range(len(L)) if re.fullmatch(r'\s*24\s*', L[i]) and 'UNIFORM' in ' '.join(L[i:i + 700]))
    i1 = next(i for i in range(i0, len(L)) if 'NBA DRAFT HISTORY' in L[i])
    return L[i0:i1]


def main():
    lines = page_text()
    num, by_year, n, orphans = None, {}, 0, []

    def add(name, years_txt, number):
        nonlocal n
        for part in re.split(r',\s*', years_txt.strip()):
            r = re.match(r'(\d{4})(?:[-–](\d{2,4})?)?', part.strip())
            if not r:
                continue
            a, b = int(r.group(1)), r.group(2)
            if part.strip().endswith('-') and not b:
                b = '2027'   # "2023-": still wearing it
            b = a if not b else (int(b) if len(b) == 4 else (a // 100) * 100 + int(b) + (100 if int(b) < a % 100 else 0))
            for y in range(a, b + 1):
                by_year.setdefault(str(y), []).append({'name': name, 'num': number})
        n += 1

    prev = ''
    for ln in lines:
        t = ln.strip()
        if re.fullmatch(r'\d{1,2}|00', t):
            if 'NATIONAL CHAMPIONS' not in prev:   # skip the page number under the running header
                num = t
            prev = t
            continue
        prev = t
        m = re.match(r"^(.+?)\*?\s*\.{2,}\s*([\d ,\-–]+)\s*$", t)
        if not m:
            continue
        name = m.group(1).strip(' .*')
        if num is None:
            orphans.append((name, m.group(2)))   # the page's text starts mid-list: these finish the last number on the page
            continue
        add(name, m.group(2), num)
    for name, yrs in orphans:
        add(name, yrs, num)
    json.dump({'_source': "UConn 2026-27 Record Book, ALL-TIME UNIFORM NUMBERS", 'by_year': by_year}, open(OUT, 'w'), indent=1)
    print(f'{n} uniform entries ({len(orphans)} carried over to #{num}), {len(by_year)} seasons')


if __name__ == '__main__':
    main()
