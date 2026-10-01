"""Extract the record book's ALL-TIME OPPONENT SERIES HISTORIES (pp. 27-35):
every game vs every opponent with date (M/D/YY), result, score, site code.
Output: out/official/recordbook_series.json  [{opp, date, res, pts, opp_pts, site, raw}]
"""
import pdfplumber, re, collections, json, os
BASE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(BASE, 'cache.nosync/official/RECORD_BOOK_26-27_V2_.pdf')
OUT = os.path.join(BASE, 'out/official/recordbook_series.json')
GAME = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{2})\s+([WLT])\s*,?\s*(\d{1,3})\s*-\s*(\d{1,3})\s*(.*)$')
OLD = re.compile(r'^(\d{4})-(\d{2})\s+([WLT])\s*,?\s*(\d{1,3})\s*-\s*(\d{1,3})\s*(.*)$')
HEAD = re.compile(r'^(.+?)\s*\((\d+)-(\d+)\)\s*$')

def cols(p):
    words = [w for w in p.extract_words(x_tolerance=1.5, y_tolerance=2) if w['top'] > 38]
    xs = sorted(w['x0'] for w in words if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{2}|\d{4}-\d{2}', w['text']))
    cl = []
    for x in xs:
        if cl and x - cl[-1][-1] < 40: cl[-1].append(x)
        else: cl.append([x])
    starts = [sorted(c)[len(c)//5] for c in cl if len(c) >= 5]
    out = collections.defaultdict(list)
    for w in words:
        ci = 0
        for i, s in enumerate(starts):
            if w['x0'] >= s - 6: ci = i
        out[ci].append(w)
    res = []
    for ci in range(len(starts)):
        ws = sorted(out[ci], key=lambda w: (round(w['top']), w['x0']))
        lines = []
        for w in ws:
            if lines and abs(w['top'] - lines[-1][0]) <= 2.5: lines[-1][1].append(w)
            else: lines.append([w['top'], [w]])
        for top, lw in lines:
            lw.sort(key=lambda w: w['x0'])
            res.append(' '.join(w['text'] for w in lw))
    return res

pdf = pdfplumber.open(PDF)
allg = []
cur = None
raw_lines = []
for pn in range(27, 36):
    for t in cols(pdf.pages[pn - 1]):
        raw_lines.append(f'P{pn}| {t}')
        t = t.strip()
        m = GAME.match(t)
        if m:
            mo, dy, yy, r, a, b, site = m.groups()
            yy = int(yy); year = 1900 + yy if yy > 30 else 2000 + yy
            allg.append({'opp': cur, 'date': f'{year:04d}-{int(mo):02d}-{int(dy):02d}', 'res': r, 'pts': int(a), 'opp_pts': int(b), 'site': site.strip(), 'raw': t, 'page': pn})
            continue
        if OLD.match(t):
            continue
        h = HEAD.match(t)
        if h and not re.search(r'\d/\d', t):
            cur = h.group(1).strip()
open(os.path.join(BASE, 'cache.nosync/official/recordbook_series_cols.txt'), 'w').write('\n'.join(raw_lines))
json.dump(allg, open(OUT, 'w'), indent=0, ensure_ascii=False)
print(len(allg), 'dated series games;', len({g['opp'] for g in allg}), 'opponents')
