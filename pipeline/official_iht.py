"""Grep International Herald Tribune daily issues (archive.org OCR text) for UConn results.
usage: python3 official_iht.py YYYY-MM-DD [days_after=3] [pattern=Connecticut]
Fetches the issues for the given date .. +days_after and prints context lines around the pattern."""
import sys, os, re, json, datetime, subprocess, urllib.parse
BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, 'cache.nosync/official/iht')
_meta = {}

def files(year):
    if year not in _meta:
        p = os.path.join(CACHE, f'meta_{year}.json')
        if not os.path.exists(p):
            subprocess.run(['curl', '-s', '-m', '60', f'https://archive.org/metadata/InternationalHeraldTribune{year}FranceEnglish', '-o', p])
        d = json.load(open(p))
        _meta[year] = [f['name'] for f in d.get('files', []) if f['name'].endswith('_djvu.txt')]
    return _meta[year]

def issue(date):
    mon = date.strftime('%b')
    pref = f'{mon} {date.day:02d} {date.year}, '
    for f in files(date.year):
        if f.startswith(pref):
            local = os.path.join(CACHE, f.replace(' ', '_').replace(',', '').replace('#', ''))
            if not os.path.exists(local) or os.path.getsize(local) < 1000:
                url = f'https://archive.org/download/InternationalHeraldTribune{date.year}FranceEnglish/' + urllib.parse.quote(f)
                subprocess.run(['curl', '-sL', '-m', '120', url, '-o', local])
            return f, local
    return None, None

if __name__ == '__main__':
    d0 = datetime.date.fromisoformat(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    pat = sys.argv[3] if len(sys.argv) > 3 else 'Connecticut'
    for k in range(0, n + 1):
        d = d0 + datetime.timedelta(days=k)
        f, local = issue(d)
        if not f:
            print(f'--- {d}: no issue')
            continue
        txt = open(local, encoding='utf-8', errors='replace').read()
        hits = [m.start() for m in re.finditer(pat, txt)]
        print(f'--- {d}: {f} ({len(hits)} hits)')
        for h in hits[:12]:
            s = txt[max(0, h - 160): h + 200].replace('\n', ' / ')
            print('   ...', s)
