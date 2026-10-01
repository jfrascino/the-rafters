#!/usr/bin/env python3
"""Contact sheet of hero-image candidates for a moment, so a clean frame (no burned-in thumbnail text) can be picked.

  python3 dev/moment_frames.py <slug> [outdir]

Candidates: each video's YouTube stills (custom thumbnail + the three auto-generated frames), ESPN clip/video stills,
and the draft's photos. Prints a numbered list; the picked URL goes in pipeline/moments_heroes.json."""
import io, json, os, sys, urllib.request
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
slug = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'dev', 'frames')
# build the moment in memory from its draft (never written to site/data, so nothing unverified can be published)
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import moments as M
src = next((p for p in (os.path.join(ROOT, 'pipeline', 'out', 'moments', d, f'{slug}.json') for d in ('verified', 'drafts')) if os.path.exists(p)))
m = M.build_one(json.load(open(src)), json.load(open(os.path.join(ROOT, 'site', 'data', 'core.json'))))
cands = []
for v in m.get('videos') or []:
    if v.get('src'):
        if v.get('thumb'):
            cands.append((f"espn {v['title'][:40]}", v['thumb']))
        continue
    for f in ('maxresdefault', 'maxres1', 'maxres2', 'maxres3'):
        cands.append((f"{v['id']} {f} · {v['kind']}", f"https://i.ytimg.com/vi/{v['id']}/{f}.jpg"))
for b in m.get('sequence') or []:
    if b.get('clip', {}).get('thumb'):
        cands.append((f"clip {b['clock']} {b['clip']['title'][:30]}", b['clip']['thumb']))
for p in m.get('photos') or []:
    cands.append((f"photo {(p.get('caption') or '')[:40]}", p['url']))

tiles = []
for i, (label, url) in enumerate(cands):
    try:
        b = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20).read()
        im = Image.open(io.BytesIO(b)).convert('RGB')
    except Exception as e:
        print(f'{i:2d}  (failed: {e}) {url}')
        continue
    print(f'{i:2d}  {im.width}x{im.height}  {label}  {url}')
    im.thumbnail((480, 270))
    t = Image.new('RGB', (480, 300), (10, 14, 26))
    t.paste(im, ((480 - im.width) // 2, 0))
    d = ImageDraw.Draw(t)
    d.text((6, 276), f'{i}  {label[:60]}', fill=(230, 230, 230))
    tiles.append(t)
cols = 3
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 480, max(1, rows) * 300), (0, 0, 0))
for k, t in enumerate(tiles):
    sheet.paste(t, ((k % cols) * 480, (k // cols) * 300))
os.makedirs(out, exist_ok=True)
path = os.path.join(out, f'{slug}.jpg')
sheet.save(path, quality=80)
print(path)
