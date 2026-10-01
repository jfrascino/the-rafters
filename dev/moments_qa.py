#!/usr/bin/env python3
"""QA for built Moments (site/data/moments/*.json): what lines up with the game data and what doesn't.

  python3 dev/moments_qa.py            every built moment
  python3 dev/moments_qa.py <slug>     one, with every beat listed

Flags: beats that didn't match a play-by-play row (games with play-by-play only), paragraphs without a source,
no hero, no video, a final score that disagrees with the dek, sources that are only the site's own data."""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'site', 'data', 'moments')


def qa(m, verbose=False):
    flags = []
    seq = m.get('sequence') or []
    if m.get('chart'):
        miss = [b for b in seq if b.get('play') is None]
        if miss:
            flags.append(f"{len(miss)}/{len(seq)} beats not matched to the play-by-play: " + ', '.join(f"{b.get('period')} {b.get('clock')}" for b in miss))
    for k in ('setup', 'story', 'aftermath', 'legacy'):
        for i, p in enumerate(m.get(k) or []):
            if not p.get('src'):
                flags.append(f'{k}[{i}] has no source')
    for i, b in enumerate(seq):
        if not b.get('src'):
            flags.append(f'sequence[{i}] has no source')
    if not m.get('hero'):
        flags.append('no hero image')
    if not m.get('videos'):
        flags.append('no video')
    g = m.get('game') or {}
    nums = re.findall(r'(\d{2,3})-(\d{2,3})', (m.get('dek') or '').replace('–', '-'))
    if g and nums and not any({int(a), int(b)} == {g.get('pts'), g.get('opp_pts')} for a, b in nums):
        flags.append(f"dek scores {nums} don't include the final {g.get('pts')}-{g.get('opp_pts')}")
    web = [s for s in m.get('sources') or [] if s.get('url')]
    if len(web) < 3:
        flags.append(f'only {len(web)} outside sources')
    line = (f"{m['slug']:24s} beats {sum(1 for b in seq if b.get('play') is not None)}/{len(seq)}  clips {sum(1 for b in seq if b.get('clip'))}  "
            f"shot {'yes' if m.get('shot') else '-'}  videos {len(m.get('videos') or [])}  quotes {len(m.get('quotes') or [])}  "
            f"sources {len(web)}  hero {(m.get('hero') or {}).get('kind', '-')}")
    print(line)
    for f in flags:
        print('    !', f)
    if verbose:
        for b in seq:
            print(f"    {b.get('period'):>3} {b.get('clock'):>6} {b.get('u')}-{b.get('o')} play={b.get('play')} clip={'y' if b.get('clip') else '-'}  {b['text'][:90]}")
    return flags


def main():
    files = sorted(glob.glob(os.path.join(D, '*.json')))
    only = sys.argv[1] if len(sys.argv) > 1 else None
    total = 0
    for f in files:
        m = json.load(open(f))
        if only and m['slug'] != only:
            continue
        total += len(qa(m, verbose=bool(only)))
    print(f'{len(files)} moments built; {total} flags')


if __name__ == '__main__':
    main()
