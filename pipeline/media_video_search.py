"""Search YouTube for each video target, score candidates, keep top picks for review.
Output: cache.nosync/media/video_candidates.json"""
import json, os, re, sys
from media_common import CACHE
from media_yt import search, length_sec

ALIASES = {
    "UTSA": ["utsa", "texas-san antonio", "texas–san antonio", "texas san antonio"],
    "NC State": ["nc state", "n.c. state", "north carolina state", "nc st"],
    "Central Florida": ["ucf", "central florida"],
    "Miami (FL)": ["miami"],
    "Saint Mary's": ["saint mary", "st. mary", "st mary", "smc"],
    "Saint Joseph's": ["saint joseph", "st. joseph", "st joseph"],
    "St. John's": ["st. john", "st john", "saint john", "red storm"],
    "Boston University": ["boston university", "boston u", " bu "],
    "George Washington": ["george washington", "gw ", "gwu"],
    "Texas A&M": ["texas a&m", "texas a & m", "texas am", "aggies"],
    "LSU": ["lsu", "louisiana state", "shaquille", "shaq"],
    "UCLA": ["ucla"],
    "San Diego State": ["san diego state", "sdsu", "san diego st"],
    "San Diego": ["san diego"],
    "Michigan State": ["michigan state", "michigan st", "msu", "spartans"],
    "Mississippi State": ["mississippi state", "miss state", "mississippi st"],
    "Southern Illinois": ["southern illinois", "siu"],
    "North Carolina": ["north carolina", "unc", "tar heels"],
    "Fairleigh Dickinson": ["fairleigh dickinson", "fdu"],
    "Eastern Michigan": ["eastern michigan", "emu"],
    "Pittsburgh": ["pittsburgh", "pitt"],
    "Georgia Tech": ["georgia tech", "yellow jackets"],
    "New Mexico State": ["new mexico state", "new mexico st", "nmsu"],
    "Iowa State": ["iowa state", "iowa st", "cyclones"],
}
UCONN = ["uconn", "connecticut", "huskies", "u conn", "u-conn"]
OFFICIAL = {"march madness": 6, "ncaa march madness": 6, "uconn huskies": 5, "uconn athletics": 5, "uconn men's basketball": 5,
            "big east conference": 5, "big east": 4, "cbs sports": 4, "cbs sports hq": 3, "espn": 4, "espn college basketball": 4,
            "fox sports": 4, "fox college hoops": 4, "house of highlights": 1, "the american": 3, "american athletic conference": 3,
            "ncaa": 5, "tnt sports": 3, "bleacher report": 1, "nbc connecticut": 2, "wfsb": 1, "sny": 2}
BAD = ["free pick", "free college basketball pick", "tournament pick", "sportsbook", "🔴", " live |", "live:", "simulated", "cyberpuck", "sue bird", "diana taurasi", "paige bueckers", "geno", "auriemma", "women", "wbb", "lady", "2k", "simulation", "sim ", "prediction", "predictions", "preview", "picks", "reaction",
       "odds", "betting", "bracket", "live stream", "watch live", "livestream", "podcast", "fortnite", "gameplay", "ps5", "xbox",
       "college hoops 2k", "ncaa basketball 10", "march madness 0", "live score", "score update", "ai "]

def opp_terms(opp):
    base = ALIASES.get(opp)
    if base: return base
    o = opp.lower().replace("(fl)", "").strip()
    return [o]

def score(c, t, year):
    title = (c["title"] or "").lower()
    desc = (c.get("desc") or "").lower()
    ch = (c["channel"] or "").lower()
    s = 0.0; why = []
    txt = " " + title + " "
    must_hit = False
    if t.get("must_any"):
        if any(m in txt for m in t["must_any"]): s += 5; why.append("must"); must_hit = True
        elif any(m in desc for m in t["must_any"]): s += 1; why.append("must-desc")
        else: s -= 8; why.append("no-must")
    if any(u in txt for u in UCONN): s += 3; why.append("uconn")
    elif any(u in desc for u in UCONN): s += 1
    else: s -= (2 if must_hit else 6); why.append("no-uconn")
    ot = opp_terms(t["opponent"]) if t.get("opponent") else []
    if ot:
        if any(o in txt for o in ot): s += 4; why.append("opp")
        elif any(o in desc for o in ot): s += 1.5; why.append("opp-desc")
        else: s -= 5; why.append("no-opp")
    if not year:
        L = length_sec(c["length"])
        if any(b in txt for b in BAD): s -= 8; why.append("bad")
        for k, v in OFFICIAL.items():
            if ch == k or (len(k) > 5 and ch.startswith(k)):
                s += v; why.append("official"); break
        return s, why, L
    ys = [str(year)]
    if t.get("date", "")[:4].isdigit(): ys.append(t["date"][:4])
    yrs = set(ys) | {"'" + y[2:] for y in ys}
    if any(y in title for y in yrs): s += 3; why.append("year")
    elif any(y in desc for y in yrs): s += 1; why.append("year-desc")
    else:
        # any other 4-digit year in the title => probably a different game
        other = re.findall(r"\b(19[89]\d|20[0-2]\d)\b", title)
        if other: s -= 6; why.append("other-year")
        else: s -= 1.5
    rnd = (t.get("round") or "").lower()
    for k in ["final four", "elite eight", "elite 8", "sweet 16", "sweet sixteen", "national championship", "championship", "first round", "second round", "big east"]:
        if k in rnd.replace("tournament final", "championship") and k in title: s += 1; why.append("round")
    for k, v in OFFICIAL.items():
        if ch == k or (len(k) > 5 and ch.startswith(k)):
            s += v; why.append("official"); break
    if any(b in txt for b in BAD): s -= 8; why.append("bad")
    L = length_sec(c["length"])
    if L == 0: s -= 3  # live/upcoming/shorts
    return s, why, L

def kind_of(c, L):
    tl = c["title"].lower()
    if "documentary" in tl or "30 for 30" in tl: return "documentary"
    if "press conference" in tl or "interview" in tl or "postgame" in tl or "post-game" in tl: return "interview"
    if L >= 50 * 60 or "full game" in tl: return "full_game"
    if L <= 100 and "highlight" not in tl: return "moment"
    return "highlights"

TEAM = {"NC State": "NC State", "Miami (FL)": "Miami"}

def queries(t):
    y = t["season"]; o = TEAM.get(t["opponent"], t["opponent"])
    r = t["round"]
    if t["target_kind"] == "ncaa":
        rr = r.replace("NCAA ", "")
        return [f"UConn vs {o} {y} NCAA tournament {rr}", f"Connecticut {o} {y} highlights"]
    if t["target_kind"] in ("conf_final", "conf_tourney"):
        return [f"UConn vs {o} {y} {r}", f"Connecticut {o} {y} {r.split(' Tournament')[0]} tournament"]
    return [f"UConn vs {o} {t['date'][:4]} {t.get('query_hint','')}".strip(), f"Connecticut {o} {y} basketball"]

def run(targets, outname="video_candidates.json"):
    res = []
    for i, t in enumerate(targets):
        seen = {}
        for q in t.get("queries") or queries(t):
            try:
                for c in search(q):
                    if c["id"] in seen: continue
                    s, why, L = score(c, t, t["season"])
                    c.update({"score": s, "why": why, "secs": L, "kind": kind_of(c, L), "q": q})
                    seen[c["id"]] = c
            except Exception as e:
                print("ERR", q, e, file=sys.stderr)
        cands = sorted(seen.values(), key=lambda c: -c["score"])[:8]
        res.append({"target": t, "cands": cands})
        top = cands[0] if cands else None
        print(i, t["season"], t["round"], t.get("opponent"), "=>", top and (round(top["score"], 1), top["kind"], top["channel"], top["title"][:70]), flush=True)
        json.dump(res, open(os.path.join(CACHE, outname), "w"), indent=1, ensure_ascii=False)
    return res

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "video_targets.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "video_candidates.json"
    targets = json.load(open(os.path.join(CACHE, name)))
    run(targets, out)
