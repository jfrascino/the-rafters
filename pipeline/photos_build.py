"""Merge all photo candidate sources into pipeline/out/media/player_photos.json (+ team_photos.json).

Sources (cache.nosync/photos/candidates/*.json, each {sr_id: [cand, ...]}):
  existing   - photos already in site/data/core.json (ESPN college headshots, Commons, SR)
  uconn      - uconnhuskies.com roster-archive headshots (2003-04 .. 2015-16)
  <others>   - any file whose entries already carry the output schema (kind/credit/license/...)
Rejections: candidates/rejected.json {"urls": [...]} are dropped everywhere.
Ordering: UConn-era before pro; headshot before action; then by resolution.
"""
import json
import os
import time

from photos_common import (CAND_DIR, PLAYER_OUT, TEAM_OUT, load_candidates, load_players, probe, save_probes)

KIND_RANK = {"uconn-headshot": 0, "uconn-action": 1, "uconn-team": 5, "nba-headshot": 2, "pro-other": 3, "other": 4}
FIELDS = ("url", "kind", "cutout", "w", "h", "source", "credit", "license", "caption")


def existing_entries(players):
    """Photos already on core.json, with metadata recovered from images.json / URL shape."""
    imgs = json.load(open(os.path.join(os.path.dirname(PLAYER_OUT), "images.json")))
    byurl = {}
    for x in imgs.get("players", []):
        for u in (x.get("image_url"), x.get("thumb_url")):
            if u:
                byurl[u.split("?")[0]] = x
    out = {}
    for p in players:
        u = p.get("photo")
        if not u:
            continue
        base = u.split("?")[0]
        if "espncdn.com/i/headshots/mens-college-basketball" in u:
            e = {"url": u, "kind": "uconn-headshot", "cutout": True, "source":
                 "https://www.espn.com/mens-college-basketball/player/_/id/" + base.rsplit("/", 1)[-1].split(".")[0],
                 "credit": "ESPN", "license": "Copyright ESPN (hotlinked)", "caption": f"{p['name']} UConn headshot (ESPN)"}
        elif "wikimedia.org" in u:
            x = byurl.get(base, {})
            ctx = x.get("context")
            kind = {"uconn": "uconn-action", "nba": "nba-headshot"}.get(ctx, "other")
            if kind == "nba-headshot":
                kind = "pro-other"  # Commons NBA-era photos are not studio headshots
            e = {"url": u, "kind": kind, "cutout": False, "source": x.get("file_page") or u,
                 "credit": x.get("author") or "Wikimedia Commons", "license": x.get("license") or "",
                 "caption": x.get("caption_or_description") or p["name"], "context": ctx}
        else:
            e = {"url": u, "kind": "other", "cutout": False, "source": u, "credit": "", "license": "", "caption": p["name"]}
        out[p["id"]] = [e]
    return out


def uconn_entries():
    raw = load_candidates("uconn")
    out = {}
    for pid, lst in raw.items():
        for c in sorted(lst, key=lambda c: c["season"], reverse=True):
            out.setdefault(pid, []).append({
                "url": c["url"], "kind": "uconn-headshot", "cutout": bool(c.get("alpha")), "w": c.get("w"), "h": c.get("h"),
                "source": c["source"], "credit": "UConn Athletics (uconnhuskies.com)",
                "license": "Copyright UConn Athletics (hotlinked)",
                "caption": f"{c['name']} — {c['season']} UConn men's basketball roster headshot", "season": c["season"]})
    return out


def main():
    players = load_players()
    ids = [p["id"] for p in players]
    rejected = set(load_candidates("rejected").get("urls", []))
    merged = {}

    def add(src, data):
        for pid, lst in data.items():
            if pid not in ids:
                continue
            for c in lst:
                if not c.get("url") or c["url"] in rejected:
                    continue
                c = dict(c)
                c.setdefault("cutout", False)
                c["_src"] = src
                merged.setdefault(pid, []).append(c)

    add("existing", existing_entries(players))
    add("uconn", uconn_entries())
    for fn in sorted(os.listdir(CAND_DIR)):
        name = fn[:-5]
        if not fn.endswith(".json") or name in ("uconn", "uconn_all", "rejected", "existing") or name.startswith("_"):
            continue
        add(name, load_candidates(name))

    out_players, missing = {}, []
    for pid in ids:
        lst = merged.get(pid, [])
        seen, clean = set(), []
        for c in lst:
            k = c["url"].split("?")[0]
            if k in seen:
                continue
            seen.add(k)
            if not c.get("w"):
                pr = probe(c["url"])
                if not pr["ok"]:
                    continue
                c["w"], c["h"] = pr["w"], pr["h"]
            clean.append(c)
        clean.sort(key=lambda c: (KIND_RANK.get(c["kind"], 9), 0 if c.get("cutout") else 1, -(c.get("w") or 0)))
        if clean:
            out_players[pid] = [{k: c.get(k) for k in FIELDS} | ({"season": c["season"]} if c.get("season") else {})
                                for c in clean]
        else:
            missing.append(pid)
    save_probes()
    doc = {"generated": time.strftime("%Y-%m-%d %H:%M"),
           "note": "Real photographs only; each image's source page names the player. Hotlink-checked with "
                   "Referer https://jfrascino.github.io/. Lists are best-first (UConn-era > NBA headshot > other).",
           "players": out_players, "still_missing": missing}
    tmp = PLAYER_OUT + ".tmp"
    json.dump(doc, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, PLAYER_OUT)
    uc = sum(1 for v in out_players.values() if v[0]["kind"].startswith("uconn"))
    print(f"players with any photo: {len(out_players)}/{len(ids)}; UConn-era first: {uc}; missing {len(missing)}")

    # team photos
    team = load_candidates("team")
    seasons = {}
    for yr, lst in sorted(team.items()):
        for c in lst:
            if c.get("url") in rejected:
                continue
            seasons.setdefault(yr, []).append({k: c.get(k) for k in ("url", "w", "h", "source", "credit", "license", "caption")})
    tmp = TEAM_OUT + ".tmp"
    json.dump({"generated": time.strftime("%Y-%m-%d %H:%M"), "seasons": seasons}, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, TEAM_OUT)
    print("team-photo seasons:", sorted(seasons))


if __name__ == "__main__":
    main()
