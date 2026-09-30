#!/usr/bin/env python3
"""Jersey numbers from UConn's official roster archive (uconnhuskies.com, 2003-04 onward).

Sports-Reference's rosters sometimes give two players the same number in one season; the school's own roster wins.
python3 pipeline/official_numbers.py → pipeline/out/official/numbers.json  {season: {name: number}}
"""
import json, os, re, time, html, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache.nosync', 'official', 'rosters')
OUT = os.path.join(HERE, 'out', 'official', 'numbers.json')
os.makedirs(CACHE, exist_ok=True)


def main():
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for y in range(2004, 2027):
        label = f'{y - 1}-{str(y)[2:]}'
        p = os.path.join(CACHE, f'{label}.html')
        if not os.path.exists(p):
            req = urllib.request.Request(f'https://uconnhuskies.com/sports/mens-basketball/roster/{label}', headers={'User-Agent': 'Mozilla/5.0 (the-rafters fan project)'})
            open(p, 'w').write(urllib.request.urlopen(req, timeout=40).read().decode('utf-8', 'replace'))
            time.sleep(1.5)
        h = open(p).read()
        nums = {}
        for name, num in re.findall(r'aria-label="([^"<>]+?) jersey number (\w+) full bio"', h):
            nums.setdefault(html.unescape(name).strip(), num)
        out[str(y)] = nums
        print(y, len(nums))
    json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
