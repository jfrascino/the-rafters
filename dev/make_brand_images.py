#!/usr/bin/env python3
"""App icons (PWA / home screen) and the default link-preview card, drawn from the site's own assets.

  site/assets/icons/icon-192.png, icon-512.png, icon-maskable-512.png, apple-touch-icon.png
  site/assets/og/default.jpg   1200x630: a tilted wall of Jason's restored player photos, navy-toned, with the wordmark
Re-run after the wall photos change: python3 dev/make_brand_images.py"""
import glob, os, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'site', 'assets')
NAVY, INK, GOLD, WHITE = (0, 14, 47), (4, 10, 24), (227, 189, 110), (238, 242, 249)
SLAB = ('/System/Library/Fonts/Supplemental/Rockwell.ttc', 2)   # bold face of the collection: close to the site's varsity slab
COND = '/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf'


def shield(d, x, y, w, fill):
    h = w * 46 / 36
    pts = [(x, y), (x + w, y), (x + w, y + h * 32 / 46), (x + w / 2, y + h), (x, y + h * 32 / 46)]
    d.polygon(pts, fill=fill)
    return h


def icon(size, pad=0.0):
    im = Image.new('RGB', (size, size), NAVY)
    d = ImageDraw.Draw(im)
    w = size * (0.56 - pad)
    x, y = (size - w) / 2, size * (0.17 + pad / 2)
    h = shield(d, x, y, w, WHITE)
    f = ImageFont.truetype(SLAB[0], int(w * 0.62), index=SLAB[1])
    d.text((size / 2, y + h * 0.43), '6', font=f, fill=NAVY, anchor='mm')
    return im


def og():
    W, H = 1200, 630
    bg = Image.new('RGB', (W * 2, H * 2), INK)
    tiles = sorted(glob.glob(os.path.join(A, 'wall', '*.jpg')))
    random.Random(6).shuffle(tiles)
    tw, th, gap = 150, 182, 10
    k = 0
    for col in range(-1, W * 2 // (tw + gap) + 2):
        off = (col % 2) * th // 2
        for row in range(-1, H * 2 // (th + gap) + 2):
            t = Image.open(tiles[k % len(tiles)]).convert('L')
            k += 1
            t = ImageOps.fit(t, (tw, th))
            t = ImageOps.colorize(t, black=(2, 8, 26), white=(120, 150, 210))
            bg.paste(t, (col * (tw + gap), row * (th + gap) - off))
    bg = bg.rotate(-7, resample=Image.BICUBIC).crop((W // 2, H // 2, W // 2 + W, H // 2 + H))
    # a dark pool behind the type, soft at the edges
    shade = Image.new('L', (W, H), 0)
    sd = ImageDraw.Draw(shade)
    sd.rectangle((0, 0, W, H), fill=120)
    sd.ellipse((-200, 40, 1000, 600), fill=235)
    shade = shade.filter(ImageFilter.GaussianBlur(70))
    im = Image.composite(Image.new('RGB', (W, H), INK), bg, shade)
    d = ImageDraw.Draw(im)
    shield_w = 64
    shield(d, 80, 112, shield_w, WHITE)
    f6 = ImageFont.truetype(SLAB[0], 40, index=SLAB[1])
    d.text((80 + shield_w / 2, 112 + 82 * 0.43), '6', font=f6, fill=NAVY, anchor='mm')
    word = ImageFont.truetype(SLAB[0], 40, index=SLAB[1])
    d.text((166, 150), 'STORRS LORE', font=word, fill=WHITE, anchor='lm')
    big = ImageFont.truetype(COND, 128)
    d.text((80, 240), '6 BANNERS.', font=big, fill=GOLD)
    d.text((80, 352), 'EVERY HUSKY.', font=big, fill=WHITE)
    small = ImageFont.truetype(COND, 36)
    d.text((82, 498), "UCONN MEN'S BASKETBALL · EVERY SEASON SINCE 1900–01", font=small, fill=(195, 203, 220))
    yrs = ImageFont.truetype(SLAB[0], 30, index=SLAB[1])
    d.text((82, 548), '1999   2004   2011   2014   2023   2024', font=yrs, fill=GOLD)
    return im


def main():
    os.makedirs(os.path.join(A, 'icons'), exist_ok=True)
    os.makedirs(os.path.join(A, 'og'), exist_ok=True)
    icon(192).save(os.path.join(A, 'icons', 'icon-192.png'))
    icon(512).save(os.path.join(A, 'icons', 'icon-512.png'))
    icon(512, pad=0.12).save(os.path.join(A, 'icons', 'icon-maskable-512.png'))   # safe zone for masks
    icon(180).save(os.path.join(A, 'icons', 'apple-touch-icon.png'))
    og().save(os.path.join(A, 'og', 'default.jpg'), quality=86)
    print('icons + og/default.jpg written')


if __name__ == '__main__':
    main()
