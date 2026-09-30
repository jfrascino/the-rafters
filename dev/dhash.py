#!/usr/bin/env python3
"""Perceptual difference hash (dHash) via macOS sips, so near-identical images match even when re-sized or re-encoded."""
import os, struct, subprocess, sys, tempfile


def dhash(path, size=16):
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, 'x.bmp')
        subprocess.run(['sips', '-s', 'format', 'bmp', '-z', str(size), str(size + 1), path, '--out', out], check=True, capture_output=True)
        b = open(out, 'rb').read()
    off = struct.unpack('<I', b[10:14])[0]
    w, h = struct.unpack('<ii', b[18:26])
    bpp = struct.unpack('<H', b[28:30])[0] // 8
    row = (w * bpp + 3) & ~3
    px = []
    for y in range(abs(h)):
        r = b[off + y * row: off + y * row + w * bpp]
        px.append([(0.299 * r[x * bpp + 2] + 0.587 * r[x * bpp + 1] + 0.114 * r[x * bpp]) if bpp >= 3 else r[x] for x in range(w)])
    if h > 0:
        px.reverse()  # BMP rows are stored bottom-up
    bits = 0
    for y in range(len(px)):
        for x in range(w - 1):
            bits = (bits << 1) | (1 if px[y][x] > px[y][x + 1] else 0)
    return bits


def dist(a, b):
    return bin(a ^ b).count('1')


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(f'{dhash(p):x}', p)
