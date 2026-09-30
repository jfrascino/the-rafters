"""Build the list of games/moments we want videos for -> cache.nosync/media/video_targets.json"""
import json, re
from media_common import CACHE
import os

sched = json.load(open(os.path.join(CACHE, "schedules_parsed.json")))

ROUND_NORM = [
    (r"first four|opening round", "First Four"),
    (r"championship|final$|finals", "Final"),
    (r"final four|semifinal", "Final Four"),
    (r"elite", "Elite Eight"),
    (r"sweet|regional semi", "Sweet Sixteen"),
    (r"third round", "Second Round"),  # 2014 naming
    (r"second round", "Second Round"),
    (r"first round", "First Round"),
]

def norm_round(g, year):
    n = g["gamename"].lower()
    n = re.sub(r"ncaa\s*", "", n)
    if year in ("2014",) and "second round" in n:
        return "First Round"  # 2011-2015 NCAA called R64 the 'second round'
    if year in ("2012", "2013") and "second round" in n:
        return "First Round"
    for pat, lab in ROUND_NORM:
        if "national championship" in n or "championship game" in n:
            return "National Championship"
        if re.search(pat, n):
            return lab
    return g["gamename"]

targets = []
def add(y, g, kind, rnd, extra=None):
    t = {"season": int(y), "date": g["date"], "opponent": g["opponent"], "round": rnd,
         "result": g["result"], "uconn": g["uconn"], "opp_score": g["opp_score"], "ot": g["ot"],
         "site": g["site"], "seed": g["seed"], "oppseed": g["oppseed"], "vacated": g.get("vacated", False),
         "target_kind": kind, "wiki": sched[y]["url"]}
    if extra: t.update(extra)
    targets.append(t)

ICONIC = [  # (season, opponent substring, date prefix or None, label)
    ("1988", "Ohio State", "1988-03", "NIT Final"),
    ("1990", "St. John's", "1990-01", None),
    ("2009", "Syracuse", "2009-03-12", None),
    ("2006", "Syracuse", "2006-03-09", None),
    ("2016", "Cincinnati", "2016-03-11", None),
]

for y, v in sched.items():
    for g in v["games"]:
        sec = g["section"].lower()
        if not g["result"]:
            continue
        if "ncaa" in sec and "invitation" not in sec:
            add(y, g, "ncaa", "NCAA " + norm_round(g, y))
        elif ("big east" in sec or "aac" in sec or "american athletic" in sec) and "tournament" in sec:
            gn = g["gamename"].lower()
            if "championship" in gn or gn.strip() == "final":
                add(y, g, "conf_final", ("Big East" if "big east" in sec else "AAC") + " Tournament Final")
            elif y == "2011":
                add(y, g, "conf_tourney", "Big East Tournament " + re.sub(r"(?i)big east\s*|/rivalry", "", g["gamename"]).strip())

for y, opp, dp, lab in ICONIC:
    for g in sched[y]["games"]:
        if opp in g["opponent"] and (dp is None or g["date"].startswith(dp)):
            if any(t["season"] == int(y) and t["date"] == g["date"] for t in targets):
                break
            add(y, g, "iconic", lab or g["section"] + (" " + g["gamename"] if g["gamename"] else ""))
            break
    else:
        print("ICONIC NOT FOUND", y, opp, dp)

json.dump(targets, open(os.path.join(CACHE, "video_targets.json"), "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(len(targets), Counter(t["target_kind"] for t in targets))
