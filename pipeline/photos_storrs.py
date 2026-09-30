"""Storrs Stories (storrsstories.com/uconn_players2.html) — a UConn fan history site with a small photo for
nearly every UConn men's player, each row linked to the player's Sports-Reference page (exact sr_id match).

Images are small (≈110-275 px) — good restoration-queue material. Each image used here was visually
reviewed on contact sheets; KIND_OVERRIDE / REJECT hold the review results.
Writes candidates/storrs.json.
"""
import re
import urllib.parse

from photos_common import fetch, load_players, norm, probe, save_candidates, save_probes

PAGE = "https://www.storrsstories.com/uconn_players2.html"
BASE = "https://www.storrsstories.com/"

# visual review results (sr_id -> kind) for images that are not UConn-era action shots
KIND_OVERRIDE = {}
# sr_id -> reason, for images rejected in review (unreadable number, wrong person, not a photo, ...)
REJECT = {"marcus-white-1": "jersey number unreadable (could be Josh Boone #21)"}
CROP = {}
ALIAS = {"vassilis-lanes-1": "bill-lanes-1", "corey-floydjr-1": "corey-floyd-jr-1"}


NAME_A = re.compile(r"<a href='([^']+)'[^>]*>([^<]+)<BR>\s*<IMG SRC=\"images/bar_chart\.png\"", re.I)


def parse():
    """One record per film block: the block's own image + the NAME anchor of the same row (the anchor wrapping
    the player's name + bar-chart icon). The sr_id comes from that anchor's Sports-Reference href when present,
    else from the name text; either way the name text must agree with our player's name."""
    h = fetch(PAGE)
    players = load_players()
    byname = {}
    for p in players:
        byname.setdefault(norm(p["name"]), []).append(p)
    pname = {p["id"]: p["name"] for p in players}
    rows = []
    for chunk in h.split('<div class="film">')[1:]:
        m = re.search(r'<img[^>]+src="([^"]+)"', chunk, re.I)
        a = NAME_A.search(chunk)
        if not (m and a):
            continue
        # the name anchor must belong to this row: no other film block / row break before it
        if chunk.find("</tr>", 0, a.start()) != -1:
            continue
        href, name = a.group(1), re.sub(r"\s+", " ", a.group(2)).strip()
        src = m.group(1)
        url = urllib.parse.urljoin(BASE, src.replace(" ", "%20"))
        yrs = re.search(r"<font face=\"ARIAL\" size=\"2\">\s*([^<]+)", chunk[a.end():a.end() + 400])
        sm = re.search(r"sports-reference\.com/cbb/players/([a-z0-9-]+)\.html", href)
        sid = ALIAS.get(sm.group(1), sm.group(1)) if sm else None
        n = norm(re.sub(r"\(.*?\)", "", name))
        nick = [norm(x) for x in re.findall(r"\((.*?)\)", name)]
        if sid and sid in pname:
            ok = norm(pname[sid]) == n or n.startswith(norm(pname[sid])) or norm(pname[sid]).endswith(n[-5:]) or any(norm(pname[sid]).startswith(k) for k in nick)
            if not ok:
                print("  name mismatch, skipped:", name, sid)
                continue
        else:
            c = byname.get(n, [])
            if len(c) != 1:
                continue
            sid = c[0]["id"]
        rows.append({"sr_id": sid, "name": name, "url": url, "years": (yrs.group(1).strip() if yrs else "")})
    return rows


def main():
    ids = {p["id"] for p in load_players()}
    out = {}
    rows = parse()
    for r in rows:
        if r["sr_id"] not in ids or r["sr_id"] in REJECT:
            continue
        pr = probe(r["url"])
        if not pr["ok"]:
            print("probe failed", r["url"], pr.get("status"))
            continue
        kind = KIND_OVERRIDE.get(r["sr_id"], "uconn-action")
        crop = CROP.get(r["sr_id"])
        c = {"url": r["url"], "kind": kind, "cutout": False, "w": pr["w"], "h": pr["h"], "source": PAGE,
             "credit": "Storrs Stories (storrsstories.com) UConn players page", "license": "Copyright (hotlinked)",
             "caption": f"{r['name']} — Storrs Stories UConn player photo ({r['years']})" + (f" [crop: {crop}]" if crop else "")}
        if crop:
            c["crop"] = crop
        out.setdefault(r["sr_id"], []).append(c)
    save_probes()
    save_candidates("storrs", out)
    print("storrs rows:", len(rows), "matched players:", len(out))
    return rows


if __name__ == "__main__":
    main()
