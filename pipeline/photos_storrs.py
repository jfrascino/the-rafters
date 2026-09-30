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

# ---- visual review (2026-09-30, contact sheets of every image for the players still missing a photo) ----
# jersey number visible and matching the Sports-Reference/UConn roster for his seasons
VERIFIED = {
    "kirk-king-1": "navy #13 (1995-97 number)", "willie-mccloud-1": "#33", "antwoine-anderson-1": "#0",
    "antric-klaiber-1": "navy #22", "ajou-deng-1": "#4", "dion-carson-1": "navy #24", "covington-cormier-1": "#5",
    "justin-brown-2": "#20", "marcus-cox-1": "#50", "ej-harrison-1": "#40 (1997-98 number)", "ruslan-inyatkin-1": "#10",
    "michael-leblanc-1": "#5", "david-onuorah-1": "#34", "james-spradling-1": "#44", "uri-cohen-mintz-1": "#50",
    "bill-lanes-1": "#50", "jeff-cybart-1": "#53", "pete-kane-1": "#52", "shawn-ellison-1": "#32",
    "pete-mccann-1": "#12 (no conflicting 1996-97 #12)",
}
# UConn uniform, number not visible — identification rests on the site's label
UNIFORM_ONLY = {"marcus-thomas-3", "clint-simmons-1", "jeff-calhoun-1", "justin-srb-1"}
KIND_OVERRIDE = {"sam-funches-1": "other"}  # #31 but a stars-and-stripes all-star uniform, not UConn
NOTE = {"sam-funches-1": "pre-UConn all-star game photo (#31), labeled Sam Funches by the site",
        "clint-simmons-1": "photo appears tinted/colorized", "karsten-kibbe-1": "tinted/colorized face crop",
        "jeff-lewis-3": "tinted/colorized face crop"}
# images rejected in review
REJECT = {"marcus-white-1": "jersey number unreadable (could be Josh Boone #21)",
          "brian-hall-1": "shows a present-day UConn SOCCER player (#3) — not the 1986-87 walk-on",
          "greg-yeomans-1": "distant back view of a golfer — unusable, identity unverifiable"}
# plausible but unverifiable (modern later-life headshots / face crops that could be namesakes):
# kept out of player_photos.json, offered only in the restoration queue
QUEUE_ONLY = {"kurt-bauer-1", "rick-bush-1", "chris-crowley-2", "craig-glazer-1", "richard-moore-2",
              "karsten-kibbe-1", "jeff-lewis-3"}
CROP = {"antric-klaiber-1": "centre, #22 in navy between two defenders", "shawn-ellison-1": "centre-right, #32",
        "antwoine-anderson-1": "right-centre, #0 in white", "covington-cormier-1": "right, #5 in white",
        "dion-carson-1": "left-centre, #24 in navy"}
REVIEWED = set(VERIFIED) | UNIFORM_ONLY | set(KIND_OVERRIDE) | set(REJECT) | QUEUE_ONLY
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
        sid = r["sr_id"]
        kind = KIND_OVERRIDE.get(sid, "uconn-action")
        if sid in QUEUE_ONLY:
            kind = "other"
        crop = CROP.get(sid)
        if sid in VERIFIED:
            review = f"jersey {VERIFIED[sid]} visible, matches roster"
        elif sid in UNIFORM_ONLY:
            review = "UConn uniform, number not visible"
        elif sid in QUEUE_ONLY:
            review = "UNVERIFIED later-life/face photo (possible namesake) — restoration queue only"
        elif sid in REVIEWED:
            review = "reviewed"
        else:
            review = "not individually reviewed"
        cap = f"{r['name']} — Storrs Stories UConn player photo ({r['years']}); {review}"
        if NOTE.get(sid):
            cap += f"; {NOTE[sid]}"
        c = {"url": r["url"], "kind": kind, "cutout": False, "w": pr["w"], "h": pr["h"], "source": PAGE,
             "credit": "Storrs Stories (storrsstories.com) UConn players page", "license": "Copyright (hotlinked)",
             "caption": cap + (f" [crop: {crop}]" if crop else "")}
        if crop:
            c["crop"] = crop
        if sid in QUEUE_ONLY:
            c["queue_only"] = True
        if sid not in REVIEWED:
            c["unreviewed"] = True
        out.setdefault(r["sr_id"], []).append(c)
    save_probes()
    save_candidates("storrs", out)
    print("storrs rows:", len(rows), "matched players:", len(out))
    return rows


if __name__ == "__main__":
    main()
