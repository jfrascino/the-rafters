"""Pro / reference-site headshots for every player:
  - Sports-Reference CBB photo already scraped (pipeline/out/sr/players/*.json photo_url)
  - Basketball-Reference NBA page headshot (alt text names the player)
  - Basketball-Reference G League / international player pages (ids from Wikidata)
  - NBA.com CDN headshot (id from Wikidata P3647; generic silhouette rejected)
  - ESPN NBA headshot (id from Wikidata P3685)
Writes cache.nosync/photos/candidates/pro.json
"""
import hashlib
import json
import os
import re
import urllib.request

from photos_common import (CACHE, REFERER, UA_BROWSER, fetch, load_players, load_sr, probe, save_candidates,
                           save_probes, _wait)

WD = json.load(open(os.path.join(CACHE, "wikidata_ids.json")))
NBA_PLACEHOLDER_SIZES = {12430}


def body_hash(url):
    _wait(urllib.parse.urlparse(url).netloc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA_BROWSER, "Referer": REFERER})
        with urllib.request.urlopen(req, timeout=30) as r:
            b = r.read()
        return hashlib.md5(b).hexdigest(), len(b)
    except Exception:
        return None, 0


import urllib.parse  # noqa: E402


def bbref_headshot(page_url, name):
    h = fetch(page_url)
    if not h:
        return None
    for m in re.finditer(r"<img itemscope=.image. src=.([^'\"]+). alt=.Photo of ([^'\"]+).", h):
        return m.group(1), m.group(2)
    return None


def main():
    players = load_players()
    out = {}
    placeholder = None
    for p in players:
        pid, name = p["id"], p["name"]
        sr = load_sr(pid)
        wd = WD.get(pid, {})
        lst = []
        # Sports-Reference CBB photo
        if sr.get("photo_url"):
            only_uconn = (sr.get("bio", {}).get("school_slugs") or ["connecticut"]) == ["connecticut"]
            pr = probe(sr["photo_url"])
            if pr["ok"]:
                lst.append({"url": sr["photo_url"], "kind": "uconn-headshot" if only_uconn else "other", "cutout": False,
                            "w": pr["w"], "h": pr["h"], "source": sr.get("url"), "credit": "Sports-Reference.com",
                            "license": "Copyright (hotlinked)", "caption": f"{name} — Sports-Reference college player photo"})
        # Basketball-Reference NBA
        if sr.get("nba_url"):
            r = bbref_headshot(sr["nba_url"], name)
            if r:
                url, alt = r
                pr = probe(url)
                if pr["ok"]:
                    lst.append({"url": url, "kind": "nba-headshot", "cutout": False, "w": pr["w"], "h": pr["h"],
                                "source": sr["nba_url"], "credit": "Basketball-Reference.com",
                                "license": "Copyright (hotlinked)", "caption": f"Photo of {alt} — Basketball-Reference NBA page"})
        # BBRef G League / international
        for key, tmpl in (("gl", "https://www.basketball-reference.com/gleague/players/{}.html"),
                          ("intl", "https://www.basketball-reference.com/international/players/{}.html")):
            for v in wd.get(key, []) or []:
                page = tmpl.format(v)
                r = bbref_headshot(page, name)
                if r:
                    url, alt = r
                    pr = probe(url)
                    if pr["ok"]:
                        lst.append({"url": url, "kind": "pro-other", "cutout": False, "w": pr["w"], "h": pr["h"],
                                    "source": page, "credit": "Basketball-Reference.com",
                                    "license": "Copyright (hotlinked)", "caption": f"Photo of {alt} — Basketball-Reference {'G League' if key == 'gl' else 'international'} page"})
        # NBA.com
        for nid in wd.get("nba", []) or []:
            url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{nid}.png"
            pr = probe(url)
            if pr["ok"] and pr.get("bytes0") not in NBA_PLACEHOLDER_SIZES:
                lst.append({"url": url, "kind": "nba-headshot", "cutout": True, "w": pr["w"], "h": pr["h"],
                            "source": f"https://www.nba.com/player/{nid}", "credit": "NBA.com",
                            "license": "Copyright NBA (hotlinked)", "caption": f"{name} NBA.com headshot"})
        # ESPN NBA
        for eid in wd.get("espn", []) or []:
            url = f"https://a.espncdn.com/i/headshots/nba/players/full/{eid}.png"
            pr = probe(url)
            if pr["ok"]:
                lst.append({"url": url, "kind": "nba-headshot", "cutout": True, "w": pr["w"], "h": pr["h"],
                            "source": f"https://www.espn.com/nba/player/_/id/{eid}", "credit": "ESPN",
                            "license": "Copyright ESPN (hotlinked)", "caption": f"{name} ESPN NBA headshot"})
        if lst:
            out[pid] = lst
            print(pid, [c["kind"] + ":" + str(c["w"]) for c in lst], flush=True)
        save_candidates("pro", out)
        save_probes()
    print("players with pro/reference photos:", len(out))


if __name__ == "__main__":
    main()
