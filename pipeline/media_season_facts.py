"""Extract structured facts per season from cached wikitext -> cache.nosync/media/season_facts.json"""
import json, re, os, html
from media_common import CACHE
raw = json.load(open(os.path.join(CACHE, "seasons_raw.json")))
sched = json.load(open(os.path.join(CACHE, "schedules_parsed.json")))

def clean(s):
    s = html.unescape(s)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    for _ in range(3):
        s = re.sub(r"\{\{(?:Tooltip|abbr)\|([^|{}]*)\|[^{}]*\}\}", r"\1", s)
        s = re.sub(r"\{\{(?:sortname)\|([^|{}]*)\|([^|{}]*)[^{}]*\}\}", r"\1 \2", s)
        s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<br\s*/?>", "; ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("'''", "").replace("''", "")
    return re.sub(r"[ \t]+", " ", s).strip()

def balanced(wt, start):
    depth = 0; i = start
    while i < len(wt):
        if wt.startswith("{{", i): depth += 1; i += 2; continue
        if wt.startswith("}}", i):
            depth -= 1; i += 2
            if depth == 0: return wt[start:i]
            continue
        i += 1
    return wt[start:]

def infobox(wt):
    i = wt.find("{{Infobox")
    if i < 0: return {}
    body = balanced(wt, i)[:-2]
    f = {}
    for mm in re.finditer(r"\n?\s*\|\s*(\w+)\s*=(.*?)(?=\n\s*\|\s*\w+\s*=|\|\s*\w+\s*=|\Z)", body, re.S):
        f[mm.group(1)] = clean(mm.group(2))
    return {k: v for k, v in f.items() if k in ("record", "conf_record", "conference", "head_coach", "hc_year", "APRank", "CoachRank",
                                               "champion", "tourney", "tourney_result", "stadium", "conf_short", "short_conf", "division_place", "conf_place", "division")}

def section(wt, name):
    m = re.search(r"\n==+\s*(?:" + name + r")[^=\n]*==+\n(.*?)(?=\n==[^=])", wt, re.S | re.I)
    return clean(m.group(1)) if m else ""

out = {}
for y, v in raw.items():
    wt = v["wikitext"]
    lead = wt.split("\n==", 1)[0]
    lead = lead[lead.find("'''"):] if "'''" in lead else lead
    out[y] = {"title": v["title"], "infobox": infobox(wt), "lead": clean(lead),
              "awards": section(wt, "Awards|Honors|Season highlights|Rankings"),
              "prev": section(wt, "Previous season"), "offseason": section(wt, "Offseason"),
              "season_text": section(wt, "Season|Regular season|Season recap|Season summary|Postseason"),
              "draft": section(wt, "Team players drafted|NBA draft|Players drafted|Draft"),
              "extract": v["extract"]}
json.dump(out, open(os.path.join(CACHE, "season_facts.json"), "w"), indent=1, ensure_ascii=False)
for y in out: print(y, out[y]["infobox"].get("record"), "|", out[y]["infobox"].get("champion", "")[:100], "|", len(out[y]["lead"]), len(out[y]["awards"]), len(out[y]["season_text"]))
