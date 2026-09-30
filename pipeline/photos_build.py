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
import re
import time

from photos_common import (CAND_DIR, PLAYER_OUT, PROJ, TEAM_OUT, load_candidates, load_players, probe, save_probes)

KIND_RANK = {"uconn-headshot": 0, "uconn-action": 1, "uconn-team": 5, "nba-headshot": 2, "pro-other": 3, "other": 4}
FIELDS = ("url", "kind", "cutout", "w", "h", "source", "credit", "license", "caption", "crop")
QUEUE_OUT = os.path.join(os.path.dirname(PLAYER_OUT), "photo_queue.json")
SMALL = 500  # short side under this -> restoration queue


def existing_entries(players):
    """Stable pre-existing sources (NOT core.json, which is rebuilt from this file's output):
    ESPN college headshots (out/espn/athletes.json + current.json) and the Commons lead photos in images.json."""
    from photos_common import norm
    root = os.path.dirname(os.path.dirname(PLAYER_OUT))
    out = {}
    byname = {}
    for p in players:
        byname.setdefault(norm(p["name"]), []).append(p)

    def match(name, seasons):
        c = byname.get(norm(name), [])
        if seasons:
            c = [p for p in c if set(p["years"]) & set(seasons)] or []
        return c[0] if len(c) == 1 else None

    espn = []
    try:
        espn += list(json.load(open(os.path.join(root, "espn", "athletes.json"))).values())
    except Exception:
        pass
    try:
        cur = json.load(open(os.path.join(root, "espn", "current.json")))
        for r in cur.get("roster") or []:
            espn.append({"id": r.get("id"), "name": r.get("name"), "headshot": r.get("headshot"),
                         "seasons": (r.get("priorSeasons") or []) + [cur.get("season") or 0]})
    except Exception:
        pass
    for a in espn:
        if not a.get("headshot"):
            continue
        p = match(a["name"], a.get("seasons"))
        if not p:
            continue
        e = {"url": a["headshot"], "kind": "uconn-headshot", "cutout": True,
             "source": f"https://www.espn.com/mens-college-basketball/player/_/id/{a['id']}",
             "credit": "ESPN", "license": "Copyright ESPN (hotlinked)", "caption": f"{p['name']} UConn headshot (ESPN)"}
        lst = out.setdefault(p["id"], [])
        if all(x["url"] != e["url"] for x in lst):
            lst.append(e)

    imgs = json.load(open(os.path.join(os.path.dirname(PLAYER_OUT), "images.json")))
    for x in imgs.get("players", []):
        u = x.get("thumb_url") or x.get("image_url")
        if not u:
            continue
        p = match(x["player_name"], None)
        if not p:
            continue
        ctx = x.get("context")
        kind = {"uconn": "uconn-action", "nba": "pro-other"}.get(ctx, "other")
        m = re.match(r"(\d{4})", x.get("date") or "")
        if kind == "uconn-action" and (not m or int(m.group(1)) > max(p["years"])):
            kind = "other"  # UConn context but after his playing days (e.g. as coach)
        e = {"url": u, "kind": kind, "cutout": False, "source": x.get("file_page") or u,
             "credit": x.get("author") or "Wikimedia Commons", "license": x.get("license") or "",
             "caption": x.get("caption_or_description") or p["name"]}
        out.setdefault(p["id"], []).append(e)
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
        if (not fn.endswith(".json") or name in ("uconn", "uconn_all", "rejected", "existing") or name.startswith("_")
                or name.startswith("team")):
            continue
        add(name, load_candidates(name))

    out_players, missing, queue_extra = {}, [], {}
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
            m = re.search(r"\[crop:\s*([^\]]+)\]", c.get("caption") or "")
            if m and not c.get("crop"):
                c["crop"] = m.group(1).strip()
            if c.get("queue_only"):
                queue_extra.setdefault(pid, []).append(c)
                continue
            clean.append(c)
        # unreviewed bulk imports go after everything else
        clean.sort(key=lambda c: (1 if c.get("unreviewed") else 0, KIND_RANK.get(c["kind"], 9),
                                  0 if c.get("cutout") else 1, -(c.get("w") or 0)))
        if clean:
            out_players[pid] = [{k: c.get(k) for k in FIELDS if k != "crop" or c.get("crop")}
                                | ({"season": c["season"]} if c.get("season") else {}) for c in clean]
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

    # restoration queue = (a) players the site still lacks (photos-drop/NEEDED.md, maintained by the app build)
    # + (b) players whose best photo here is small (< SMALL px short side, clean cutout headshots >=400 excepted)
    #       and who have no owner-restored photo yet (site/assets/players/<sr_id>.*, photos-drop/<Name>.*)
    pinfo = {p["id"]: p for p in players}
    from photos_common import norm
    byn = {}
    for p in players:
        byn.setdefault(norm(p["name"]), []).append(p)
    targets, reason = [], {}
    needed_md = os.path.join(PROJ, "photos-drop", "NEEDED.md")
    if os.path.exists(needed_md):
        for name, span in re.findall(r"^\| ([^|]+?) \| (\d{4}–\d{2}) \|", open(needed_md).read(), re.M):
            c = [p for p in byn.get(norm(name), []) if p["span"] == span] or byn.get(norm(name), [])
            if len(c) == 1 and c[0]["id"] not in reason:
                targets.append(c[0]["id"])
                reason[c[0]["id"]] = "needed"
    restored = set()
    adir = os.path.join(PROJ, "site", "assets", "players")
    if os.path.isdir(adir):
        restored |= {os.path.splitext(f)[0] for f in os.listdir(adir)}
    ddir = os.path.join(PROJ, "photos-drop")
    if os.path.isdir(ddir):
        for f in os.listdir(ddir):
            stem, ext = os.path.splitext(f)
            if ext.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                for p in byn.get(norm(stem), []):
                    restored.add(p["id"])
    for pid in ids:
        if pid in reason or pid in restored:
            continue
        lst = out_players.get(pid, [])
        best = lst[0] if lst else None
        short = min(best.get("w") or 0, best.get("h") or 0) if best else 0
        if best is None or (short < SMALL and not (best.get("cutout") and short >= 400)):
            targets.append(pid)
            reason[pid] = "small"
    queue = []
    for pid in targets:
        lst = out_players.get(pid, []) + [dict(c, unverified=True) for c in queue_extra.get(pid, [])]
        p = pinfo[pid]
        # best findable: verified before unverified, UConn-era first, then largest
        qrank = {"uconn-headshot": 0, "uconn-action": 1, "uconn-team": 2, "nba-headshot": 3, "pro-other": 4, "other": 5}
        cands = sorted(lst, key=lambda c: (1 if c.get("unverified") else 0, qrank.get(c["kind"], 6),
                                           -min(c.get("w") or 0, c.get("h") or 0)))
        queue.append({"sr_id": pid, "name": p["name"], "years": p.get("span"), "number": p.get("num"),
                      "status": (("needed: " if reason[pid] == "needed" else "small: ")
                                 + ("has-verified-photo" if out_players.get(pid) else
                                    "unverified-only" if queue_extra.get(pid) else "missing")),
                      "best_candidates": [{"url": c["url"], "page": c["source"], "w": c.get("w"), "h": c.get("h"),
                                           "kind": c["kind"], "caption": c.get("caption"),
                                           **({"crop": c["crop"]} if c.get("crop") else {}),
                                           **({"unverified": True} if c.get("unverified") else {})} for c in cands[:5]]})
    tmp = QUEUE_OUT + ".tmp"
    json.dump({"generated": time.strftime("%Y-%m-%d %H:%M"),
               "note": "First the players the site still lacks a photo for (photos-drop/NEEDED.md, status 'needed: ...'), then "
                       f"players whose best photo is under {SMALL}px and not yet owner-restored (status 'small: ...'). "
                       "best_candidates: real images, verified first (UConn-era portrait > action > team, then largest); "
                       "entries flagged unverified are plausible but could be namesakes — check before use.",
               "queue": queue}, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, QUEUE_OUT)
    import collections as _c
    print("restoration queue:", len(queue), dict(_c.Counter(q["status"] for q in queue)))

    # team photos
    seasons = {}
    for fn in sorted(os.listdir(CAND_DIR)):
        if not (fn.startswith("team") and fn.endswith(".json")):
            continue
        for yr, lst in load_candidates(fn[:-5]).items():
            for c in lst:
                if c.get("url") in rejected or any(x["url"] == c.get("url") for x in seasons.get(yr, [])):
                    continue
                seasons.setdefault(yr, []).append({k: c.get(k) for k in ("url", "w", "h", "source", "credit", "license", "caption")})
    def _tp(c):
        cap = (c.get("caption") or "").lower()
        return (0 if "official team" in cap or "team photo" in cap or "team poster" in cap else
                1 if "white house" in cap or "national champion" in cap else 2, -(c.get("w") or 0))
    seasons = {yr: sorted(v, key=_tp)[:5] for yr, v in sorted(seasons.items())}
    tmp = TEAM_OUT + ".tmp"
    json.dump({"generated": time.strftime("%Y-%m-%d %H:%M"), "seasons": seasons}, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, TEAM_OUT)
    print("team-photo seasons:", sorted(seasons))


if __name__ == "__main__":
    main()
