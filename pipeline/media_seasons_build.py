"""Assemble out/media/seasons.json from season wiki data, parsed schedules, awards lists and hand-written stories."""
import json, os, re
from media_common import CACHE, save, wiki_url
from media_season_stories import STORIES, MOMENTS, PROGRAM
from media_awards import parse_awards

raw = json.load(open(os.path.join(CACHE, "seasons_raw.json")))
facts = json.load(open(os.path.join(CACHE, "season_facts.json")))
sched = json.load(open(os.path.join(CACHE, "schedules_parsed.json")))
awards = parse_awards()

HONOR_AWARDS = [  # (award key, display)
    ("NCAA Tournament MOP", "NCAA Final Four Most Outstanding Player"),
    ("Consensus First Team All-Americans", "Consensus first-team All-American"),
    ("Consensus Second Team All-Americans", "Consensus second-team All-American"),
    ("NABC National Player of the Year", "NABC National Player of the Year"),
    ("UPI College Basketball Player of the Year", "UPI College Player of the Year"),
    ("Bob Cousy Award", "Bob Cousy Award"),
    ("Lute Olson Award", "Lute Olson Award"),
    ("Pete Newell Big Man Award", "Pete Newell Big Man Award"),
    ("NABC National Defensive Player of the Year", "NABC Defensive Player of the Year"),
    ("Academic All-America Team Member of the Year", "Academic All-American of the Year"),
    ("AP National Coach of the Year", "AP National Coach of the Year"),
    ("Naismith College Coach of the Year", "Naismith College Coach of the Year"),
    ("Sporting News Coach of the Year", "Sporting News Coach of the Year"),
    ("Big East Player of the Year", "Big East Player of the Year"),
    ("AAC Player of the Year", "AAC Player of the Year"),
    ("Big East Coach of the Year", "Big East Coach of the Year"),
    ("Big East Defensive Player of the Year", "Big East Defensive Player of the Year"),
    ("AAC Defensive Player of the Year", "AAC Defensive Player of the Year"),
    ("Big East Rookie of the Year", "Big East Rookie/Freshman of the Year"),
    ("AAC Rookie of the Year", "AAC Rookie of the Year"),
    ("Big East Tournament MVP", "Big East Tournament MVP"),
    ("AAC Tournament MVP", "AAC Tournament MVP"),
    ("Big East Sixth Man of the Year", "Big East Sixth Man of the Year"),
    ("Big East Most Improved Player", "Big East Most Improved Player"),
    ("AAC Most Improved Player", "AAC Most Improved Player"),
    ("Ben Jobe Award", "Ben Jobe Award"),
    ("NCAA Tournament Regional MOP", "NCAA Regional Most Outstanding Player"),
    ("All-Big East Conference First Team", "First-team All-Big East"),
    ("All-AAC First Team", "First-team All-AAC"),
]

def label(y):
    return "1999–2000" if y == 2000 else f"{y-1}–{str(y)[2:]}"

def champ_honors(y):
    ib = facts[str(y)]["infobox"]
    out = []
    for part in re.split(r";\s*", ib.get("champion", "") or ""):
        part = part.strip()
        if not part: continue
        p = part.replace("Big East 6 Division Regular Season Champions", "Big East 6 Division regular-season champions")
        p = re.sub(r"(?i)^NCAA tournament,? National Champions", "NCAA national champions", p)
        p = re.sub(r"(?i)^NCAA tournament, Runners-up", "NCAA national runner-up", p)
        p = re.sub(r"(?i)regular season", "regular-season", p)
        p = p[0].upper() + p[1:]
        out.append(p)
    return out

EXTRA_HONORS = {1988: ["NIT champions"], 1997: ["NIT third place"], 2009: ["NCAA Final Four"], 2004: ["Big East tournament champions"] }

def auto_moments(y):
    ms = []
    gs = sched[str(y)]["games"]
    for g in gs:
        sec = g["section"].lower()
        if not g["result"] or g["uconn"] is None: continue
        score = f"{g['uconn']}–{g['opp_score']}" + (f" ({g['ot']})" if g["ot"] else "")
        verb = "beat" if g["result"] == "W" else "lost to"
        post = ("ncaa" in sec) or ("nit" in sec) or ("invitation" in sec) or ("tournament" in sec)
        big_final = post and re.search(r"(?i)championship|final", g["gamename"] or "") and "quarter" not in (g["gamename"] or "").lower() and "semi" not in (g["gamename"] or "").lower()
        if ("ncaa" in sec and "invitation" not in sec):
            rnd = re.sub(r"(?i)^ncaa\s*", "", g["gamename"]) or "NCAA tournament"
            ms.append({"date": g["date"], "title": f"NCAA {rnd}: {'W' if g['result']=='W' else 'L'} vs {g['opponent']}",
                       "text": f"UConn {verb} {g['opponent']} {score} in the NCAA tournament {rnd.lower()} at {g['site']}." + (" (Later vacated by the NCAA.)" if g.get("vacated") else ""),
                       "auto": True})
        elif big_final or (("nit" in sec or "invitation" in sec) and g is gs[-1]):
            ev = g["section"]
            ms.append({"date": g["date"], "title": f"{ev} {g['gamename'] or ''}".strip() + f": {'W' if g['result']=='W' else 'L'} vs {g['opponent']}",
                       "text": f"UConn {verb} {g['opponent']} {score} ({g['gamename'] or ev}) at {g['site']}.", "auto": True})
    return ms

def wc(s): return len(s.split())

VID = json.load(open(os.path.join(os.path.dirname(__file__), "out", "media", "videos.json")))["videos"]
PRI = {"full_game": 0, "highlights": 1, "moment": 2, "documentary": 3, "interview": 4}
def season_videos(y):
    vs = [v for v in VID if v.get("season") == y]
    def key(v):
        r = (v.get("round") or "").lower()
        imp = 0 if "national championship" in r else 1 if "final four" in r else 2 if "ncaa" in r else 3 if "tournament" in r else 4
        return (imp, PRI.get(v["kind"], 5), v.get("date") or "")
    return [v["id"] for v in sorted(vs, key=key)]

seasons = []
for y in range(1987, 2028):
    st = STORIES[y]
    r = raw[str(y)]
    url = wiki_url(r["title"])
    honors = champ_honors(y) + EXTRA_HONORS.get(y, [])
    for key, disp in HONOR_AWARDS:
        for name, yr in awards.get(key, []):
            if yr == y:
                h = f"{name} – {disp}"
                if h not in honors: honors.append(h)
    if y == 2026: honors.append("NCAA Final Four")
    # dedupe case-insensitive
    seen = set(); hon = []
    for h in honors:
        k = h.lower()
        if k in seen: continue
        seen.add(k); hon.append(h)
    ms = [{"date": d, "title": t, "text": x} for d, t, x in MOMENTS.get(y, [])]
    for m in auto_moments(y) if y != 2027 else []:
        if not any(mm["date"] == m["date"] for mm in ms): ms.append(m)
    ms.sort(key=lambda m: m["date"] or "9999")
    for m in ms: m.pop("auto", None)
    srcs = [url] + [s for s in st["sources"] if s != url]
    if PROGRAM not in srcs: srcs.append(PROGRAM)
    ib = facts[str(y)]["infobox"]
    seasons.append({"year": y, "label": label(y), "wiki_url": url, "headline": st["headline"], "story": st["story"],
                    "record": ib.get("record"), "conf_record": ib.get("conf_record"), "conference": ib.get("conference") or ib.get("short_conf"),
                    "coach": ib.get("head_coach"), "key_moments": ms, "video_ids": season_videos(y), "honors": hon, "sources": srcs,
                    "story_words": wc(st["story"])})
    if not (120 <= wc(st["story"]) <= 220): print("WORDCOUNT", y, wc(st["story"]))
    if len(st["headline"].split()) > 8: print("HEADLINE LONG", y, st["headline"])
save("seasons.json", {"generated": "2026-09-30", "note": "Narratives written from the cited Wikipedia/uconnhuskies.com pages; honors from the UConn program article awards lists and season infoboxes.", "seasons": seasons})
print(len(seasons), "seasons written")
for s in seasons[:2] + seasons[12:13]: print(json.dumps(s, ensure_ascii=False)[:1500])
