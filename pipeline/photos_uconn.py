"""UConn Athletics (uconnhuskies.com, Sidearm/Nuxt) roster archives -> player headshot candidates.

Roster archives exist for 2000-01 .. present. Each roster page embeds __NUXT_DATA__ with the
players list (name, rosterPlayerId, image). Player bio pages are fetched too (they sometimes carry
an image when the roster list does not).
Writes cache.nosync/photos/candidates/uconn.json : {sr_id: [cand, ...]}
"""
import json
import re
import sys

from photos_common import fetch, load_players, norm, save_candidates, probe, save_probes

BASE = "https://uconnhuskies.com"
ALIASES = {"michaelnoyes": "mikenoyes", "martygagne": "martingagne"}


def nuxt_data(html):
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html or "", re.S)
    if not m:
        return None
    arr = json.loads(m.group(1))
    memo = {}

    def h(i):
        if isinstance(i, int) and i < 0:
            return None
        if i in memo:
            return memo[i]
        v = arr[i]
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in ("Reactive", "ShallowReactive", "Ref", "ShallowRef",
                                                        "EmptyRef", "EmptyShallowRef"):
                r = h(v[1]) if len(v) > 1 else None
                memo[i] = r
                return r
            if v and v[0] == "Set":
                return [h(x) for x in v[1:]]
            if v and v[0] == "Date":
                return v[1]
            out = []
            memo[i] = out
            out.extend(h(x) for x in v)
            return out
        if isinstance(v, dict):
            out = {}
            memo[i] = out
            for k, x in v.items():
                out[k] = h(x)
            return out
        return v
    return h(0)


def img_url(img):
    if not img:
        return None
    u = img.get("absoluteUrl") or img.get("url")
    if u and u.startswith("/"):
        u = BASE + u
    return u


def main():
    players = load_players()
    by_name = {}
    for p in players:
        by_name.setdefault(norm(p["name"]), []).append(p)
    # seasons with archives
    seasons = [f"{y}-{str(y + 1)[2:]}" for y in range(2000, 2027)]
    cands = {}
    roster_log = {}
    for s in seasons:
        spring = int(s[:4]) + 1
        html = fetch(f"{BASE}/sports/mens-basketball/roster/{s}")
        d = nuxt_data(html)
        if not d:
            print(s, "no data")
            continue
        rs = d["pinia"]["roster"]["roster"]
        plist = []
        for v in rs.values():
            if v and v.get("players"):
                plist = v["players"]
        roster_log[s] = []
        for rp in plist:
            name = f"{rp.get('firstName', '')} {rp.get('lastName', '')}".strip()
            img = img_url(rp.get("image"))
            roster_log[s].append({"name": name, "img": img, "bio": rp.get("call_to_action")})
            nm = ALIASES.get(norm(name), norm(name))
            matches = [p for p in by_name.get(nm, []) if spring in p["years"] or spring - 1 in p["years"]]
            if not matches:
                continue
            p = matches[0]
            bio_url = BASE + rp["call_to_action"] if rp.get("call_to_action") else None
            c = {"url": img, "season": s, "name": name, "source": bio_url or f"{BASE}/sports/mens-basketball/roster/{s}",
                 "roster_page": f"{BASE}/sports/mens-basketball/roster/{s}", "bio": bio_url,
                 "alt": (rp.get("image") or {}).get("alt")}
            cands.setdefault(p["id"], []).append(c)
        n_img = sum(1 for x in roster_log[s] if x["img"])
        print(s, len(plist), "players,", n_img, "with image")
        sys.stdout.flush()
    json.dump(roster_log, open("cache.nosync/photos/uconn_rosters.json", "w"), indent=1)

    # bio pages: look for images when roster lacked one
    for pid, lst in cands.items():
        for c in lst:
            if c["url"] or not c["bio"]:
                continue
            html = fetch(c["bio"])
            d = nuxt_data(html)
            if not d:
                continue
            bio = d["pinia"]["roster"].get("rosterBio") or {}
            for v in bio.values():
                if not v:
                    continue
                pl = v.get("player") or v
                im = img_url(v.get("image") or pl.get("image"))
                if im:
                    c["url"] = im
                    c["alt"] = (v.get("image") or pl.get("image") or {}).get("alt")
                    c["from_bio"] = True
    out = {}
    for pid, lst in cands.items():
        for c in lst:
            if not c["url"]:
                continue
            pr = probe(c["url"])
            c.update({"w": pr["w"], "h": pr["h"], "ok": pr["ok"], "ctype": pr["ctype"], "alpha": pr["alpha"]})
            if pr["ok"]:
                out.setdefault(pid, []).append(c)
    save_probes()
    save_candidates("uconn", out)
    save_candidates("uconn_all", cands)
    print("players with uconn roster image:", len(out))


if __name__ == "__main__":
    main()
