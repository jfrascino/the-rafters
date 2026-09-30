"""Parse CBB schedule entry templates from cached Wikipedia season wikitext."""
import json, re, html, datetime
from media_common import save, wiki_url

raw = json.load(open("cache.nosync/media/seasons_raw.json"))

MONTHS = {m: i for i, m in enumerate(["january","february","march","april","may","june","july","august","september","october","november","december"], 1)}

def iso_date(d, y):
    y = int(y)
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", d)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", d)
    if m:
        yy = int(m.group(3)); yy = yy + 1900 if yy < 100 else yy
        return f"{yy:04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r"([A-Za-z]+)\.?\s+(\d{1,2})(?:,\s*(\d{4}))?", d)
    if m and m.group(1).lower()[:3] in [k[:3] for k in MONTHS]:
        mo = [v for k, v in MONTHS.items() if k[:3] == m.group(1).lower()[:3]][0]
        yy = int(m.group(3)) if m.group(3) else (y - 1 if mo >= 8 else y)
        return f"{yy:04d}-{mo:02d}-{int(m.group(2)):02d}"
    return d

def clean(s):
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"\{\{dts\|(?:format=\w+\|)?([^{}]*)\}\}", lambda m: m.group(1).replace("|", "-"), s)
    s = re.sub(r"\{\{cbb link\|[^{}]*?title=([^|{}]*)[^{}]*\}\}", r"\1", s)
    s = re.sub(r"\{\{cbb link\|[^{}]*?team=([^|{}]*)[^{}]*\}\}", r"\1", s)
    s = re.sub(r"\{\{(?:white|color\|white)\|([^{}]*)\}\}", r"\1", s)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", s)
    s = s.replace("'''", "").replace("''", "")
    return s.strip()

def section_name(line):
    t = clean(line.split("|", 1)[-1] if "style" in line else line.lstrip("!"))
    t = re.sub(r"^.*?\|\s*", "", t) if "colspan" in t else t
    return t.strip()

def parse(y):
    wt = raw[y]["wikitext"]
    out = []
    sec = "Regular Season"
    pos = 0
    tokens = [(m.start(), "sec", m.group(0)) for m in re.finditer(r"^!\s*colspan[^\n]*", wt, re.M)]
    tokens += [(m.start(), "g", m.group(1)) for m in re.finditer(r"\{\{CBB schedule entry(.*?)\n\s*\}\}", wt, re.S)]
    tokens.sort()
    prev = (0, 0)
    for _, kind, txt in tokens:
        if kind == "sec":
            t = re.sub(r"^!\s*colspan=\d+\s*", "", txt)
            t = re.sub(r'^style=("[^"]*"|\{\{.*?\}\})\s*\|', "", t)
            s = clean(t).lstrip('|" ').replace('style="|', "").strip()
            sec = s or sec
            continue
        f = {}
        txt = re.sub(r"[ \t]\|[ \t]*(?=[\w/ ]+?\s*=)", "\n| ", txt)
        for m in re.finditer(r"\n\s*\|\s*([\w/ ]+?)\s*=(.*?)(?=\n\s*\|\s*[\w/ ]+?\s*=|\Z)", txt, re.S):
            f[m.group(1).strip()] = m.group(2).strip()
        rec = clean(f.get("record", ""))
        score = clean(f.get("score", ""))
        wl = (clean(f.get("w/l", "")) or clean(f.get("status", ""))).upper()[:1]
        if wl not in ("W", "L"): wl = ""
        mm = re.match(r"(\d+)\s*[–-]\s*(\d+)", rec)
        vac = "vacated" in rec.lower()
        if mm:
            cur = (int(mm.group(1)), int(mm.group(2)))
            if not wl:
                if cur[0] > prev[0]: wl = "W"
                elif cur[1] > prev[1]: wl = "L"
            prev = cur
        sm = re.match(r"(\d+)\s*[–-]\s*(\d+)", score)
        us = them = None
        if sm:
            a, b = int(sm.group(1)), int(sm.group(2))
            if wl == "W": us, them = max(a, b), min(a, b)
            elif wl == "L": us, them = min(a, b), max(a, b)
            else:  # vacated/unknown: Wikipedia lists UConn's score first
                us, them = a, b
                wl = "W" if a > b else "L"
        opp = clean(f.get("opponent", ""))
        opp = re.sub(r"^(at|vs\.?)\s+", "", opp)
        opp = re.sub(r"^\([^)]*\)\s*", "", opp)
        opp_rank_prefix = re.match(r"^(?:#|No\.\s*)(\d+)\s+", opp)
        opp = re.sub(r"^(?:#|No\.\s*)\d+\s+", "", opp)
        ot = clean(f.get("overtime", ""))
        dt = iso_date(clean(f.get("date", "")), y)
        date_fixed = False
        mdt = re.match(r"(\d{4})-(\d{2})-(\d{2})", dt)
        if mdt:
            yy, mo = int(mdt.group(1)), int(mdt.group(2))
            want = int(y) - 1 if mo >= 8 else int(y)
            if yy != want:
                dt = f"{want}-{mdt.group(2)}-{mdt.group(3)}"; date_fixed = True
        gname = clean(f.get("gamename", "")).split("}}")[0].strip()
        out.append({"date": dt, "date_fixed": date_fixed, "section": sec,
                    "opponent": opp, "result": wl, "uconn": us, "opp_score": them,
                    "score": score, "ot": ot, "gamename": gname,
                    "site": ", ".join(x for x in [clean(f.get("site_stadium", "")), clean(f.get("site_cityst", ""))] if x),
                    "seed": clean(f.get("seed", "")), "oppseed": clean(f.get("oppseed", "")),
                    "home": "neutral" if f.get("neutral", "").strip() else ("away" if f.get("away", "").strip() else "home"),
                    "status": clean(f.get("status", "")), "vacated": vac, "rank": clean(f.get("rank", "")), "opprank": clean(f.get("opprank", "")).strip("()") or (opp_rank_prefix.group(1) if opp_rank_prefix else ""), "attend": clean(f.get("attend", ""))})
    return out

res = {}
for y in sorted(raw):
    if raw[y]: res[y] = {"title": raw[y]["title"], "url": wiki_url(raw[y]["title"]), "games": parse(y)}
json.dump(res, open("cache.nosync/media/schedules_parsed.json", "w"), ensure_ascii=False, indent=1)
for y, v in res.items():
    secs = {}
    for g in v["games"]:
        secs.setdefault(g["section"], 0); secs[g["section"]] += 1
    post = [f'{g["gamename"] or "?"}:{g["opponent"]} {g["result"]}{g["uconn"]}-{g["opp_score"]}' for g in v["games"] if "NCAA" in g["section"] or "NIT" in g["section"] or "National Invitation" in g["section"]]
    print(y, len(v["games"]), secs, "\n   ", post)
