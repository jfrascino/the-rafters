"""Fetch Wikipedia season articles (wikitext + plaintext extract) for 1986-87..2026-27."""
import json, sys
from media_common import wiki, save

def label(y):  # y = spring year
    return f"{y-1}–{str(y)[2:]}" if y != 2000 else "1999–2000"

res = {}
for y in range(1987, 2028):
    lab = label(y)
    cands = [f"{lab} UConn Huskies men's basketball team",
             f"{lab} Connecticut Huskies men's basketball team"]
    found = None
    for t in cands:
        d = wiki(action="query", titles=t, redirects=1, prop="info")
        p = d["query"]["pages"][0]
        if not p.get("missing"):
            found = p["title"]; break
    if not found:
        print(y, "MISSING"); res[y] = None; continue
    wt = wiki(action="parse", page=found, prop="wikitext", redirects=1)["parse"]["wikitext"]
    ex = wiki(action="query", titles=found, prop="extracts", explaintext=1, redirects=1)["query"]["pages"][0].get("extract", "")
    res[y] = {"title": found, "wikitext": wt, "extract": ex}
    print(y, found, len(wt), len(ex))
import os
json.dump(res, open("cache.nosync/media/seasons_raw.json", "w"), ensure_ascii=False)
