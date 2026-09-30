"""Crawl Wikimedia Commons for UConn men's basketball photos (categories + searches) with license metadata.
Writes cache.nosync/media/commons_files.json"""
import json, os, re, html
from media_common import commons, CACHE

def members(cat, ns):
    out, cont = [], {}
    while True:
        d = commons(action="query", list="categorymembers", cmtitle=cat, cmlimit=500, cmnamespace=ns, **cont)
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" in d: cont = {"cmcontinue": d["continue"]["cmcontinue"]}
        else: break
    return out

ROOTS = ["Category:UConn Huskies men's basketball", "Category:Harry A. Gampel Pavilion", "Category:XL Center",
         "Category:Jim Calhoun", "Category:Dan Hurley", "Category:Kevin Ollie", "Category:UConn Huskies basketball coaches",
         "Category:Hugh S. Greer Field House", "Category:UConn Huskies White House visit (September 2024)",
         "Category:UConn Huskies basketball players"]
SKIP = re.compile(r"women|WNBA|Lady|Geno|Auriemma|Sue Bird|Taurasi|Breanna|Paige Bueckers|Maya Moore|Stewie", re.I)

files = {}  # title -> set(source categories)
seen_cats = set()
PLAYER_CATS = set()
def crawl(cat, depth, player_cat=False):
    if cat in seen_cats or depth < 0: return
    seen_cats.add(cat); print("cat", len(seen_cats), cat, flush=True)
    for f in members(cat, 6):
        files.setdefault(f, set()).add(cat)
    for sc in members(cat, 14):
        if SKIP.search(sc): continue
        is_pc = "players" in cat.lower()
        if is_pc: PLAYER_CATS.add(sc)
        crawl(sc, depth - 1, is_pc)

for r in ROOTS:
    crawl(r, 3)
print("cats", len(seen_cats), "files", len(files))

QUERIES = ["UConn men's basketball", "UConn Huskies basketball", "Connecticut Huskies basketball", "UConn basketball Gampel",
           "Gampel Pavilion", "UConn national champions", "UConn championship parade", "UConn Huskies White House",
           "Jim Calhoun", "Dan Hurley", "Kevin Ollie", "UConn Final Four", "XL Center Hartford", "Hartford Civic Center",
           "UConn Huskies Big East", "Kemba Walker UConn", "Shabazz Napier UConn", "Emeka Okafor UConn", "Ray Allen UConn",
           "Donovan Clingan", "Adama Sanogo", "Jordan Hawkins UConn", "Tristen Newton", "Alex Karaban", "Stephon Castle",
           "Huskies basketball Storrs", "UConn Huskies 2004 champions", "UConn Huskies 1999", "UConn Huskies 2014",
           "UConn Huskies 2011", "UConn men's basketball 2023", "UConn men's basketball 2024", "Werth Champions Center",
           "UConn Huskies Obama", "UConn Huskies Bush White House", "Hugh Greer Field House", "UConn Madison Square Garden",
           "UConn basketball game", "Huskies of Honor"]
for q in QUERIES:
    off = 0
    while off < 200:
        d = commons(action="query", list="search", srsearch=q, srnamespace=6, srlimit=100, sroffset=off)
        hits = d["query"]["search"]
        for h in hits:
            files.setdefault(h["title"], set()).add("search:" + q)
        if "continue" not in d: break
        off = d["continue"]["sroffset"]
print("files after search", len(files))

def strip(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

info = {}
titles = sorted(files)
for i in range(0, len(titles), 50):
    b = titles[i:i+50]
    d = commons(action="query", titles="|".join(b), prop="imageinfo|categories", iiprop="url|extmetadata|size|mime",
                iiurlwidth=800, cllimit=500, clshow="!hidden")
    for p in d["query"]["pages"]:
        ii = (p.get("imageinfo") or [{}])[0]
        em = ii.get("extmetadata", {})
        g = lambda k: strip(em.get(k, {}).get("value", ""))
        info[p["title"]] = {"file": p["title"], "file_page": ii.get("descriptionurl"), "image_url": ii.get("url"),
                            "thumb_url": ii.get("thumburl"), "width": ii.get("width"), "height": ii.get("height"),
                            "mime": ii.get("mime"), "license": g("LicenseShortName"), "license_url": g("LicenseUrl"),
                            "usage_terms": g("UsageTerms"), "author": g("Artist"), "credit": g("Credit"),
                            "description": g("ImageDescription"), "object_name": g("ObjectName"),
                            "date": g("DateTimeOriginal") or g("DateTime"), "categories_meta": g("Categories"),
                            "categories": [c["title"] for c in p.get("categories", [])],
                            "restrictions": g("Restrictions"), "attribution_required": g("AttributionRequired"),
                            "found_via": sorted(files[p["title"]])}
    print(i, flush=True)
json.dump(info, open(os.path.join(CACHE, "commons_files.json"), "w"), indent=1, ensure_ascii=False)
json.dump(sorted(PLAYER_CATS), open(os.path.join(CACHE, "commons_player_cats.json"), "w"), indent=1)
print("done", len(info))
