"""Wikimedia sources -> candidates/wiki.json (players) and candidates/team.json (seasons).

  A. Commons photos already crawled by media_commons.py (out/media/images.json 'photos') whose 'subjects'
     name a player (UConn-context photos become uconn-action).
  B. Wikidata P18 image for each player (ids from photos_wikidata.py).
  C. English Wikipedia lead image of the player's article (pageimages; includes non-free files, which are
     flagged "Non-free (Wikipedia fair use)").
  D. Team/event photos (White House visits, parades, games) for team_photos.json.
"""
import html
import json
import os
import re
import urllib.parse

from photos_common import (CACHE, OUT, fetch_json, load_candidates, load_players, norm, probe, save_candidates,
                           save_probes)

WD = json.load(open(os.path.join(CACHE, "wikidata_ids.json")))
UCONN_RE = re.compile(r"\bUConn\b|Connecticut|Huskies|Gampel|XL Center|Hartford Civic", re.I)


def strip(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def imageinfo(titles, api="https://commons.wikimedia.org/w/api.php"):
    out = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        url = api + "?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "formatversion": 2, "titles": "|".join(chunk),
            "prop": "imageinfo|categories", "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 1200, "cllimit": 500})
        d = fetch_json(url, browser=False)
        for p in (d or {}).get("query", {}).get("pages", []):
            if p.get("missing") or not p.get("imageinfo"):
                if p.get("missing") and "imagerepository" not in p:
                    continue
            ii = (p.get("imageinfo") or [{}])[0]
            if not ii:
                continue
            md = ii.get("extmetadata", {})
            out[p["title"]] = {
                "title": p["title"], "url": ii.get("url"), "thumb": ii.get("thumburl"), "w": ii.get("width"),
                "h": ii.get("height"), "tw": ii.get("thumbwidth"), "th": ii.get("thumbheight"),
                "page": ii.get("descriptionurl"), "mime": ii.get("mime"),
                "license": strip(md.get("LicenseShortName", {}).get("value")) or "",
                "artist": strip(md.get("Artist", {}).get("value")),
                "credit": strip(md.get("Credit", {}).get("value")),
                "desc": strip(md.get("ImageDescription", {}).get("value")),
                "nonfree": md.get("NonFree", {}).get("value") == "true" or "wikipedia/en/" in (ii.get("url") or ""),
                "cats": [c["title"] for c in p.get("categories", [])],
            }
    return out


def pick_url(info):
    """Prefer the 1200px thumb for big files (lighter hotlink), else the original."""
    if info.get("thumb") and info.get("w") and info["w"] > 1300 and not info["mime"].endswith("svg+xml"):
        return info["thumb"], info["tw"], info["th"]
    return info["url"], info["w"], info["h"]


def main():
    players = load_players()
    byname = {norm(p["name"]): p for p in players}
    out = {}

    def add(pid, info, kind, caption, source_note=""):
        url, w, h = pick_url(info)
        if not url:
            return
        pr = probe(url)
        if not pr["ok"]:
            print("  probe failed", url, pr.get("status"))
            return
        lic = info["license"] or ("Non-free (Wikipedia fair use)" if info["nonfree"] else "")
        if info["nonfree"] and "non-free" not in lic.lower():
            lic = "Non-free (Wikipedia fair use): " + lic
        c = {"url": url, "kind": kind, "cutout": False, "w": pr["w"], "h": pr["h"], "source": info["page"],
             "credit": info["artist"] or info["credit"] or "Wikimedia", "license": lic,
             "caption": (caption or info["desc"] or info["title"])[:300] + source_note}
        lst = out.setdefault(pid, [])
        if all(x["url"] != url for x in lst):
            lst.append(c)

    # A. crawled Commons photos
    imgs = json.load(open(os.path.join(OUT, "images.json")))
    team = {}
    titlesA = {}
    for ph in imgs.get("photos", []):
        for s in ph.get("subjects") or []:
            p = byname.get(norm(s))
            if p and ph.get("context") == "uconn":
                yr = ph.get("season")
                if yr and not (min(p["years"]) - 1 <= yr <= max(p["years"]) + 1) and ph["kind"] != "event":
                    continue
                titlesA.setdefault(ph["file"], []).append((p["id"], ph))
    infoA = imageinfo(list(titlesA))
    for t, lst in titlesA.items():
        info = infoA.get(t)
        if not info:
            continue
        for pid, ph in lst:
            p = next(x for x in players if x["id"] == pid)
            yr = ph.get("season")
            at_uconn = yr is None or (min(p["years"]) <= yr <= max(p["years"]))
            kind = "uconn-action" if at_uconn else "other"
            add(pid, info, kind, ph.get("description"))

    # B/C. Wikidata P18 + enwiki lead image
    p18 = {}
    for pid, e in WD.items():
        for u in e.get("img", []) or []:
            t = "File:" + urllib.parse.unquote(u.rsplit("/", 1)[-1]).replace("_", " ")
            p18.setdefault(t, []).append(pid)
    infoB = imageinfo(list(p18))
    for t, pids in p18.items():
        info = infoB.get(t)
        if not info:
            continue
        for pid in pids:
            text = info["desc"] + " " + " ".join(info["cats"]) + " " + t
            kind = "uconn-action" if UCONN_RE.search(text) else ("pro-other" if re.search(r"NBA|Celtics|Knicks|Lakers|Nets|Bucks|Hornets|Pistons|Blazers|Mavericks|Kings|Heat|Magic|Wizards|Raptors|Grizzlies|Suns|Rockets|Thunder|Hawks|Bulls|Jazz|Nuggets|Pacers|Pelicans|Spurs|Warriors|Clippers|Timberwolves|76ers|Cavaliers", text) else "other")
            add(pid, info, kind, info["desc"] or t, " [Wikidata image]")

    enwiki = {}
    for pid, e in WD.items():
        for t in e.get("enwiki", []) or []:
            enwiki.setdefault(t, []).append(pid)
    titles = list(enwiki)
    files = {}
    for i in range(0, len(titles), 40):
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "formatversion": 2, "titles": "|".join(titles[i:i + 40]),
            "prop": "pageimages", "piprop": "name", "redirects": 1})
        d = fetch_json(url, browser=False) or {}
        redir = {r["to"]: r["from"] for r in d.get("query", {}).get("redirects", [])}
        norm_ = {n["to"]: n["from"] for n in d.get("query", {}).get("normalized", [])}
        for pg in d.get("query", {}).get("pages", []):
            if pg.get("pageimage"):
                orig = redir.get(pg["title"], pg["title"])
                orig = norm_.get(orig, orig)
                files.setdefault("File:" + pg["pageimage"].replace("_", " "), []).extend(enwiki.get(orig, []) or enwiki.get(pg["title"], []))
    infoC = imageinfo(list(files), api="https://en.wikipedia.org/w/api.php")
    for t, pids in files.items():
        info = infoC.get(t)
        if not info or not info.get("url"):
            continue
        if info["mime"] and "svg" in info["mime"]:
            continue
        for pid in set(pids):
            text = info["desc"] + " " + " ".join(info["cats"]) + " " + t
            kind = "uconn-action" if UCONN_RE.search(text) else "other"
            add(pid, info, kind, info["desc"] or t, " [Wikipedia article lead image]")
    save_probes()
    save_candidates("wiki", out)
    print("wiki candidates for", len(out), "players")

    # D. team photos from crawled Commons photos
    tinfo = imageinfo([ph["file"] for ph in imgs.get("photos", []) if ph["kind"] in ("event", "game/team")
                       and ph.get("context") == "uconn"])
    TEAM_FILES = {  # file -> season (spring year); only images showing the team (not trophies/arenas)
        "File:President George W. Bush stands with Emeka Okafor of the University of Connecticut's men basketball team during a ceremony honoring the 2004 NCAA Champions.jpg": "2004",
        "File:P051611PS-0987 (5836483628).jpg": "2011",
        "File:2011 UConn Men's Basketball White House.png": "2011",
        "File:2014 UConn National Championship teams at the White House.JPG": "2014",
        "File:Barack Obama with UConn men's and women's 2014 NCAA basketball champions.jpg": "2014",
        "File:2009PittUConn2ndmin.jpg": "2009",
        "File:Huskies edge out Spartans 66-62 in Armed Forces Classic 121110-F-XXXXX.jpg": "2013",
    }
    team = load_candidates("team")
    for t, info in tinfo.items():
        yr = TEAM_FILES.get(t)
        if not yr:
            for k, v in TEAM_FILES.items():
                if k.startswith(t[:60]):
                    yr = v
        if not yr and ("2011 Championship Parade" in t or "2014 NCAA National Champion UConn Huskies" in t):
            yr = "2011" if "2011" in t else "2014"
        if not yr:
            continue
        url, w, h = pick_url(info)
        pr = probe(url)
        if not pr["ok"]:
            continue
        lst = team.setdefault(yr, [])
        if any(x["url"] == url for x in lst):
            continue
        lst.append({"url": url, "w": pr["w"], "h": pr["h"], "source": info["page"],
                    "credit": info["artist"] or info["credit"], "license": info["license"],
                    "caption": info["desc"][:300]})
    save_probes()
    save_candidates("team", team)
    print("team seasons:", {k: len(v) for k, v in sorted(team.items())})


if __name__ == "__main__":
    main()
