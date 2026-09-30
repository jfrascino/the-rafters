"""UConn "Huskies of Honor" (uconnhuskies.com/honors/huskies-of-honor) -> UConn-era action photos of honored
men's basketball players + the 1998-99 national champion team photo.

Every member image was visually checked (UConn uniform, playing days). Images are hotlinked from the Sidearm
CloudFront origin (uconnhuskies.com/images/... redirects to a webp converter).
Writes candidates/hoh.json (players) and candidates/team_hoh.json (seasons).
"""
import json
import os
import re

from photos_common import CACHE, fetch, load_players, norm, probe, save_candidates, save_probes
from photos_uconn import nuxt_data

CF = "https://dxbhsrqyrr690.cloudfront.net/sidearm.nextgen.sites/uconnhuskies.com"
PAGE = "https://uconnhuskies.com/honors/huskies-of-honor/{slug}/{id}"
# crop hints from visual review (subject not centred / several players in frame)
CROP = {"Shabazz Napier": "left, #13 in navy", "Kemba Walker": "right-centre, #15 shooting",
        "Caron Butler": "centre, #3", "Khalid El-Amin": "centre, #42 shooting", "Scott Burrell": "centre, #24"}
# 1998-99 team photo: jersey numbers visible; positions from visual review (L->R)
TEAM99 = {
    "43": "back row, 3rd from left", "34": "back row, 2nd from right", "51": "back row, far right",
    "23": "front row, far left", "42": "front row, 2nd from left", "15": "front row, 3rd from left",
    "21": "front row, 4th from left (left of coach Calhoun)", "3": "front row, right of coach Calhoun",
    "32": "front row, 3rd from right", "31": "front row, 2nd from right",
}


def main():
    players = load_players()
    byname = {norm(p["name"]): p for p in players}
    alias = {"cliffordrobinson": "cliffrobinson"}
    h = fetch("https://uconnhuskies.com/honors/huskies-of-honor/chris-smith/6")
    d = nuxt_data(h)
    setup = list(d["pinia"]["hall-of-fame-store"]["hofSetup"].values())[0]
    out, team = {}, {}
    for m in setup["members"]:
        if "Men's Basketball" not in (m.get("sports") or []) or not m.get("image"):
            continue
        name = f"{m['firstName']} {m['lastName']}"
        url = CF + m["image"]["url"]
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        page = PAGE.format(slug=slug, id=m["id"])
        pr = probe(url)
        if not pr["ok"]:
            print("probe failed", url)
            continue
        if m["firstName"] == "National Champion":
            season = str(m["classYear"])
            team.setdefault(season, []).append({
                "url": url, "w": pr["w"], "h": pr["h"], "source": page, "credit": "UConn Athletics",
                "license": "Copyright UConn Athletics (hotlinked)",
                "caption": "1998-99 NCAA national champion UConn men's basketball team — official team photo (Huskies of Honor)"})
            ros = json.load(open(os.path.join(os.path.dirname(CACHE), "..", "out", "sr", "seasons", season + ".json")))["roster"]
            for r in ros:
                pos = TEAM99.get(str(r.get("number")))
                if pos and r.get("sr_id"):
                    out.setdefault(r["sr_id"], []).append({
                        "url": url, "kind": "uconn-team", "cutout": False, "w": pr["w"], "h": pr["h"], "source": page,
                        "credit": "UConn Athletics", "license": "Copyright UConn Athletics (hotlinked)",
                        "caption": f"{r['player']} (#{r['number']}) in the 1998-99 national champion team photo; identified "
                                   f"by jersey number per the 1998-99 roster [crop: {pos}, #{r['number']}]",
                        "crop": f"{pos}, #{r['number']}"})
            continue
        n = norm(name)
        p = byname.get(alias.get(n, n))
        if not p:
            continue
        crop = CROP.get(name)
        out.setdefault(p["id"], []).append({
            "url": url, "kind": "uconn-action", "cutout": False, "w": pr["w"], "h": pr["h"], "source": page,
            "credit": "UConn Athletics", "license": "Copyright UConn Athletics (hotlinked)",
            "caption": f"{name} in a UConn game — Huskies of Honor portrait (inducted {m['inductionYear']})"
                       + (f" [crop: {crop}]" if crop else ""), **({"crop": crop} if crop else {})})
    save_probes()
    save_candidates("hoh", out)
    save_candidates("team_hoh", team)
    print("HoH players:", sorted(out), "teams:", sorted(team))


if __name__ == "__main__":
    main()
