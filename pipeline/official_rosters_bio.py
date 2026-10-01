#!/usr/bin/env python3
"""UConn's official season rosters (uconnhuskies.com, cached in cache.nosync/official/rosters/YYYY-YY.html)
-> pipeline/out/official/roster_bios.json: {spring year: [{name, num, pos, cls, ht, wt, home}]}"""
import html, json, os, re, glob
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'official', 'roster_bios.json')


def cards(path):
    s = open(path, errors='ignore').read()
    out = []
    for c in re.split(r'data-test-id="s-person-card-list__root"', s)[1:]:
        c = re.sub(r'<script.*?</script>|<style.*?</style>', '', c, flags=re.S)
        f = [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '|', c)).split('|') if x.strip()]
        rec = {}
        for k, key in (('Jersey Number', 'num'), ('Position', 'pos'), ('Academic Year', 'cls'), ('Height', 'ht'), ('Weight', 'wt'), ('Hometown', 'home'), ('High School', 'hs'), ('Last School', 'prev'), ('Previous School', 'prev')):
            if k in f and f.index(k) + 1 < len(f):
                rec[key] = f[f.index(k) + 1]
        if 'Jersey Number' in f:
            i = f.index('Jersey Number')
            rec['name'] = f[i + 2] if i + 2 < len(f) else None
        else:
            m = next((x for x in f if x.startswith('for ')), None)
            rec['name'] = m[4:] if m else None
        if rec.get('name'):
            out.append(rec)
    return out


def main():
    res = {}
    for p in sorted(glob.glob(os.path.join(HERE, 'cache.nosync', 'official', 'rosters', '*.html'))):
        m = re.search(r'(\d{4})-(\d{2})\.html$', p)
        res[str(int(m.group(1)) + 1)] = cards(p)
    json.dump(res, open(OUT, 'w'), indent=1)
    print({k: len(v) for k, v in res.items()})


if __name__ == '__main__':
    main()
