"""Collect notable UConn men's basketball players from Wikipedia (category + season roster links + backlinks),
parse UConn years, draft info. Writes cache.nosync/media/players_raw.json"""
import json, os, re
from media_common import wiki, CACHE

def cat_members(cat, ns=0):
    out, cont = [], {}
    while True:
        d = wiki(action="query", list="categorymembers", cmtitle=cat, cmlimit=500, cmnamespace=ns, **cont)
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" in d: cont = {"cmcontinue": d["continue"]["cmcontinue"]}
        else: break
    return out

catm = set(cat_members("Category:UConn Huskies men's basketball players"))
coaches = set(cat_members("Category:UConn Huskies men's basketball coaches"))
roster_links = json.load(open(os.path.join(CACHE, "roster_links.json")))
back = json.load(open(os.path.join(CACHE, "backlinks.json")))
cands = sorted(catm | set(roster_links) | set(back) | coaches)
print("candidates", len(cands))

def batch(lst, n):
    for i in range(0, len(lst), n): yield lst[i:i+n]

pages = {}
redirect_map = {}
for b in batch(cands, 20):
    d = wiki(action="query", titles="|".join(b), prop="revisions|pageimages|pageprops|info|categories", rvprop="content", rvslots="main",
             piprop="thumbnail|name|original", pithumbsize=800, redirects=1, inprop="url", cllimit=500)
    for r in d["query"].get("redirects", []): redirect_map[r["from"]] = r["to"]
    for p in d["query"]["pages"]:
        if p.get("missing") or p.get("ns") != 0: continue
        c = p.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")
        pages[p["title"]] = {"title": p["title"], "content": c, "pageimage": p.get("pageimage"),
                             "thumb": p.get("thumbnail", {}).get("source"), "original": p.get("original", {}).get("source"),
                             "shortdesc": p.get("pageprops", {}).get("wikibase-shortdesc", ""), "url": p.get("fullurl"),
                             "categories": [c_["title"] for c_ in p.get("categories", [])]}
print("pages", len(pages))

def delink(s):
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{(?:nbay|cbby)\|(\d{4})[^}]*\}\}", r"\1", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return s

def field(c, name):
    m = re.search(r"\n\s*\|\s*" + name + r"\s*=(.*?)(?=\n\s*\||\n\}\})", c, re.S)
    return m.group(1).strip() if m else ""

def uconn_years(c):
    v = delink(field(c, "college"))
    yrs = []
    for m in re.finditer(r"(UConn|Connecticut)[^()\n*]*\(\s*(\d{4})\s*(?:[–-]\s*(\d{4}|present))?\s*\)", v):
        a = int(m.group(2)); b = m.group(3)
        b = 2027 if b == "present" else int(b) if b else a
        yrs.append((a, b))
    if not yrs and re.search(r"UConn|Connecticut", v):
        ys = [(int(a), int(b)) for a, b in re.findall(r"(\d{4})\s*[–-]\s*(\d{4})", v)]
        if len(ys) == 1: yrs = ys
    return yrs

def is_uconn_mens(p):
    cats = " ".join(p["categories"])
    if "UConn Huskies women's basketball" in cats and "UConn Huskies men's basketball" not in cats: return False
    if "UConn Huskies men's basketball players" in cats: return True
    col = delink(field(p["content"], "college"))
    if re.search(r"UConn|Connecticut", col) and "Infobox basketball" in p["content"]: return True
    return False

players = {}
for t, p in pages.items():
    c = p["content"]
    coach = "UConn Huskies men's basketball coaches" in " ".join(p["categories"])
    if not is_uconn_mens(p) and not coach: continue
    yrs = uconn_years(c)
    rl = sorted(set(sum([roster_links.get(k, []) for k in [t] + [f for f, to in redirect_map.items() if to == t]], [])))
    first = min([a for a, b in yrs] + ([rl[0] - 1] if rl else []), default=None)
    last = max([b for a, b in yrs] + ([rl[-1]] if rl else []), default=None)
    dy = re.search(r"\d{4}", delink(field(c, "draft_year")))
    dr = re.search(r"\d", delink(field(c, "draft_round"))); dp = re.search(r"\d+", delink(field(c, "draft_pick")))
    dt = delink(field(c, "draft_team")).strip()
    p2 = {k: v for k, v in p.items() if k != "content"}
    p2.update({"uconn_years": [first, last] if first else None, "roster_seasons": rl, "is_coach": coach,
               "is_player": "UConn Huskies men's basketball players" in " ".join(p["categories"]) or bool(yrs) or bool(rl and not coach),
               "draft": {"year": int(dy.group(0)), "round": dr and int(dr.group(0)), "pick": dp and int(dp.group(0)), "team": dt} if dy else None,
               "birth": re.sub(r"[{}|]", " ", field(c, "birth_date"))[:60]})
    players[t] = p2
json.dump(players, open(os.path.join(CACHE, "players_raw.json"), "w"), indent=1, ensure_ascii=False)
json.dump({t: pages[t]["content"] for t in players}, open(os.path.join(CACHE, "players_wikitext.json"), "w"), ensure_ascii=False)
inrange = [p for p in players.values() if p["is_player"] and p["uconn_years"] and p["uconn_years"][1] >= 1987]
print("uconn men's people", len(players), "players in range", len(inrange))
print("no years:", [t for t, p in players.items() if p["is_player"] and not p["uconn_years"]])
