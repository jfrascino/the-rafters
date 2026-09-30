"""Extract the UConn record book's season-by-season results pages (5-15)
into a column-ordered text stream (reading order: page, column, top->bottom).
Output: pipeline/cache.nosync/official/recordbook_results_cols.txt
"""
import pdfplumber, re, collections, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(BASE, 'cache.nosync/official/RECORD_BOOK_26-27_V2_.pdf')
OUT = os.path.join(BASE, 'cache.nosync/official/recordbook_results_cols.txt')

def col_starts(words):
    xs = sorted(w['x0'] for w in words if re.fullmatch(r'\d{1,2}/\d{1,2}(-\d{1,2})?', w['text']))
    clusters = []
    for x in xs:
        if clusters and x - clusters[-1][-1] < 40:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    # keep clusters with enough members; use a low percentile so stray
    # in-line dates (e.g. 'Postponed to 2/11') don't drag a column start left
    return [sorted(c)[len(c) // 5] for c in clusters if len(c) >= 5]

def main(pages=range(5, 16)):
    pdf = pdfplumber.open(PDF)
    out = []
    for pn in pages:
        p = pdf.pages[pn - 1]
        words = p.extract_words(keep_blank_chars=False, x_tolerance=1.5, y_tolerance=2)
        words = [w for w in words if w['top'] > 38]  # drop running header
        starts = col_starts(words)
        cols = collections.defaultdict(list)
        for w in words:
            ci = 0
            for i, s in enumerate(starts):
                if w['x0'] >= s - 12:
                    ci = i
            cols[ci].append(w)
        for ci in range(len(starts)):
            ws = sorted(cols[ci], key=lambda w: (round(w['top']), w['x0']))
            lines = []
            for w in ws:
                if lines and abs(w['top'] - lines[-1][0]) <= 2.5:
                    lines[-1][1].append(w)
                else:
                    lines.append([w['top'], [w]])
            out.append(f'=====PAGE {pn} COL {ci+1} (x0={starts[ci]:.0f})=====')
            for top, lw in lines:
                lw.sort(key=lambda w: w['x0'])
                out.append(f'{top:6.1f}|' + ' '.join(w['text'] for w in lw))
    open(OUT, 'w').write('\n'.join(out) + '\n')
    print('wrote', OUT, len(out), 'lines')

if __name__ == '__main__':
    main()
