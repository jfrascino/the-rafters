"""Build out/media/images.json: (a) player page images with Commons licensing, (b) Commons game/season/arena photos."""
import json, os, re, html
from media_common import commons, CACHE, save

players = json.load(open(os.path.join(CACHE, "players_raw.json")))
files = json.load(open(os.path.join(CACHE, "commons_files.json")))
sched = json.load(open(os.path.join(CACHE, "schedules_parsed.json")))

NBA_TEAMS = ["Celtics", "Nets", "Knicks", "76ers", "Sixers", "Raptors", "Bulls", "Cavaliers", "Pistons", "Pacers", "Bucks", "Hawks",
             "Hornets", "Bobcats", "Heat", "Magic", "Wizards", "Nuggets", "Timberwolves", "Thunder", "Trail Blazers", "Blazers", "Jazz",
             "Warriors", "Clippers", "Lakers", "Suns", "Kings", "Mavericks", "Rockets", "Grizzlies", "Pelicans", "Spurs", "SuperSonics",
             "Sonics", "NBA", "G League", "WNBA"]
UC = re.compile(r"UConn|UCON\b|U-Conn|Connecticut Huskies|UConn Huskies|University of Connecticut|Gampel|Storrs|Huskies", re.I)
WOMEN = re.compile(r"women|WNBA|Lady", re.I)

def strip(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def context(text, cats):
    """text = filename + description (+ object name); cats = Commons categories."""
    t = text or ""
    if any(re.search(r"\b" + re.escape(x) + r"\b", t) for x in NBA_TEAMS): return "nba"
    if UC.search(t): return "uconn"
    if re.search(r"high school|McDonald's All-American|prep school", t, re.I): return "other"
    cc = [c for c in cats if not re.search(r"men's basketball players|Alumni|births|People from|basketball players from", c, re.I)]
    blob = " ".join(cc)
    if any(re.search(r"\b" + re.escape(x) + r"\b", blob) for x in NBA_TEAMS): return "nba"
    if UC.search(blob): return "uconn"
    return "other"

# ---------- (a) players ----------
inrange = {t: p for t, p in players.items() if p.get("is_player") and p.get("uconn_years") and p["uconn_years"][1] and p["uconn_years"][1] >= 1987}
coaches = {t: p for t, p in players.items() if p.get("is_coach") and t in ("Jim Calhoun", "Kevin Ollie", "Dan Hurley")}
want = {**inrange, **coaches}
fnames = sorted({p["pageimage"] for p in want.values() if p.get("pageimage")})
meta = {}
for i in range(0, len(fnames), 50):
    b = ["File:" + f for f in fnames[i:i+50]]
    d = commons(action="query", titles="|".join(b), prop="imageinfo|categories", iiprop="url|extmetadata|size", iiurlwidth=800,
                cllimit=500, clshow="!hidden")
    norm = {n["to"]: n["from"] for n in d["query"].get("normalized", [])}
    for pg in d["query"]["pages"]:
        key = pg["title"]
        if pg.get("missing") or not pg.get("imageinfo"):
            meta[key] = None; continue
        ii = pg["imageinfo"][0]; em = ii.get("extmetadata", {})
        g = lambda k: strip(em.get(k, {}).get("value", ""))
        meta[key] = {"image_url": ii.get("url"), "thumb_url": ii.get("thumburl"), "file_page": ii.get("descriptionurl"),
                     "license": g("LicenseShortName"), "license_url": g("LicenseUrl"), "author": g("Artist"), "credit": g("Credit"),
                     "description": g("ImageDescription") or g("ObjectName"), "date": g("DateTimeOriginal"),
                     "categories": [c["title"].replace("Category:", "") for c in pg.get("categories", [])]}
player_imgs = []; no_free = []
for t, p in sorted(want.items(), key=lambda kv: (kv[1].get("uconn_years") or [0])[0] or 0):
    name = re.sub(r"\s*\(.*\)", "", t)
    m = meta.get("File:" + p["pageimage"].replace("_", " ")) if p.get("pageimage") else None
    yrs = p.get("uconn_years")
    rec = {"player_name": name, "wiki_title": t, "wiki_url": p.get("url"), "role": "coach" if t in coaches else "player",
           "years_at_uconn": f"{yrs[0]}–{yrs[1]}" if yrs and yrs[0] else None}
    if not m:
        rec.update({"image_url": None, "note": "No freely licensed Commons image on the Wikipedia article (image absent or non-free)."})
        no_free.append(rec); continue
    ctx = context((m["description"] or "") + " " + p["pageimage"], m["categories"])
    rec.update({"image_url": m["image_url"], "thumb_url": m["thumb_url"], "file_page": m["file_page"], "license": m["license"],
                "license_url": m["license_url"], "author": m["author"], "caption_or_description": m["description"],
                "date": m["date"], "context": ctx, "commons_categories": m["categories"][:12]})
    if ctx == "other": rec["verify"] = True; rec["verify_reason"] = "context unclear from Commons description/categories"
    player_imgs.append(rec)

# ---------- (b) Commons photos ----------
def imageinfo_batch(titles):
    out = {}
    for i in range(0, len(titles), 50):
        d = commons(action="query", titles="|".join(titles[i:i+50]), prop="imageinfo|categories", iiprop="url|extmetadata|size|mime",
                    iiurlwidth=800, cllimit=500, clshow="!hidden")
        for pg in d["query"]["pages"]:
            ii = (pg.get("imageinfo") or [{}])[0]; em = ii.get("extmetadata", {})
            g = lambda k: strip(em.get(k, {}).get("value", ""))
            out[pg["title"]] = {"file": pg["title"], "file_page": ii.get("descriptionurl"), "image_url": ii.get("url"),
                "thumb_url": ii.get("thumburl"), "width": ii.get("width"), "height": ii.get("height"), "mime": ii.get("mime"),
                "license": g("LicenseShortName"), "license_url": g("LicenseUrl"), "author": g("Artist"), "credit": g("Credit"),
                "description": g("ImageDescription"), "object_name": g("ObjectName"), "date": g("DateTimeOriginal") or g("DateTime"),
                "categories": [c["title"] for c in pg.get("categories", [])], "found_via": []}
    return out

# per-player Commons categories (players in range + coaches)
PCAT_FILES = {}
for t in sorted(want):
    cat = "Category:" + t
    d = commons(action="query", list="categorymembers", cmtitle=cat, cmnamespace=6, cmlimit=200)
    for m in d.get("query", {}).get("categorymembers", []):
        PCAT_FILES.setdefault(m["title"], set()).add(t)
new_titles = [f for f in PCAT_FILES if f not in files]
extra = imageinfo_batch(new_titles) if new_titles else {}
for k, v in extra.items(): files[k] = v
for f, ts in PCAT_FILES.items():
    if f in files: files[f]["found_via"] = sorted(set(files[f].get("found_via") or []) | {"Category:" + t for t in ts})
print("player-category files", len(PCAT_FILES), "new", len(new_titles))

SEASON_RE = re.compile(r"\b(19[89]\d|20[0-2]\d)\s*[–-]\s*(\d{2,4})\b")
GAMEPHOTOS = []; ALLPHOTOS = []
PLAYER_NAMES = {re.sub(r"\s*\(.*\)", "", t): t for t in inrange}
MEN_CAT = re.compile(r"UConn Huskies men's basketball(?! players)|UConn Men's Basketball|UConn Huskies men's and women's basketball|Harry A\. Gampel Pavilion|Hugh S\. Greer Field House|UConn Huskies White House visit \(September 2024\)|^Category:(Jim Calhoun|Dan Hurley|Kevin Ollie)$", re.I)
WOMEN_X = re.compile(r"women|WNBA|Geno|Auriemma|Bueckers|Sue Bird|Taurasi|Lobo|Azzi|Fudd|M[üu]hl|Aaliyah|Ducharme|Maya Moore|Breanna|Tina Charles|Collier|Samuelson|Nurse|Lady", re.I)
NOISE_X = re.compile(r"hockey|Bruins|Whale|Wolf Pack|Beanpot|football|Cyclones at UConn Huskies \(September|rally|Obama|protest|concert|NASCAR|Bargain|Frank Hurley|Hurley, (New York|Berkshire)|David Hurley|Tutu|Marsalis|circus|wrestling|WWE|soccer|lacrosse|baseball|softball|volleyball|Healey|Malloy|DeLauro|Kennedy|Murphy|Valvano|V Foundation|Shabel|Tasker", re.I)
BASKET = re.compile(r"basketball|Gampel|Calhoun|Final Four|NCAA|Big East|parade|White House|championship", re.I)

def map_season(text, date):
    m = SEASON_RE.search(text)
    if m:
        a = int(m.group(1)); b = m.group(2); b = int(b) if len(b) == 4 else int(str(a)[:2] + b)
        if b == a + 1: return b
    if date and re.match(r"\d{4}-\d{2}", date):
        y, mo = int(date[:4]), int(date[5:7])
        return y + 1 if mo >= 8 else y
    return None

def map_game(season, date):
    if not season or not date or str(season) not in sched: return None
    for g in sched[str(season)]["games"]:
        if g["date"] == date[:10]:
            return {"date": g["date"], "opponent": g["opponent"], "result": g["result"], "score": f"{g['uconn']}–{g['opp_score']}" if g["uconn"] is not None else None, "site": g["site"]}
    return None

for fn, f in files.items():
    if not f.get("image_url") or not (f.get("mime") or "").startswith("image/"): continue
    if re.search(r"\.svg$", fn, re.I): continue
    cats = f.get("categories") or []
    via = [v for v in (f.get("found_via") or []) if not v.startswith("search:")]
    text = " ".join([fn, f.get("description") or "", f.get("object_name") or "", " ".join(cats)])
    men_cat = any(MEN_CAT.search(c) for c in cats + via)
    if WOMEN_X.search(text) and not re.search(r"(?<!wo)men's basketball|men's and women's basketball", text, re.I): continue
    if NOISE_X.search(text + " " + " ".join(via)) and not men_cat: continue
    if re.search(r"\bStadium\b", text) and not re.search(r"basketball", text, re.I): continue
    player_via = [v.replace("Category:", "") for v in via if v.replace("Category:", "") in want]
    subj = []
    for nm in PLAYER_NAMES:
        if re.search(r"\b" + re.escape(nm) + r"\b", text, re.I): subj.append(nm)
    for c in ("Jim Calhoun", "Kevin Ollie", "Dan Hurley"):
        if c.lower() in text.lower() and c not in subj: subj.append(c)
    for pv in player_via:
        nm = re.sub(r"\s*\(.*\)", "", pv)
        if nm not in subj: subj.append(nm)
    keep = men_cat or bool(player_via) or (re.search(r"(?<!wo)men's basketball", text, re.I) and UC.search(text)) or \
           (subj and BASKET.search(text) and UC.search(text))
    if not keep: continue
    date = (f.get("date") or "")[:10]
    season = map_season(text, date if re.match(r"\d{4}-\d{2}", date or "") else None)
    arena = re.search(r"Gampel|XL Center|Civic Center|PeoplesBank|Greer Field House|Champions Center", text, re.I)
    kind = "event" if re.search(r"parade|White House|ceremony|governor|Husky Day|celebrat", text, re.I) else \
           "arena" if arena and not subj else \
           "coach" if subj and all(x in ("Jim Calhoun", "Kevin Ollie", "Dan Hurley") for x in subj) else \
           "player" if subj else "game/team"
    ctx = context(" ".join([fn, f.get("description") or "", f.get("object_name") or ""]), cats)
    rec = {"file": fn, "image_url": f["image_url"], "thumb_url": f.get("thumb_url"), "file_page": f.get("file_page"),
           "license": f.get("license"), "license_url": f.get("license_url"), "author": f.get("author"), "credit": f.get("credit"),
           "description": f.get("description") or f.get("object_name"), "date": f.get("date"), "width": f.get("width"), "height": f.get("height"),
           "kind": kind, "context": ctx, "subjects": subj, "season": season if season and 1987 <= season <= 2027 and ctx == "uconn" else None,
           "game": map_game(season, date) if ctx == "uconn" else None,
           "categories": [c.replace("Category:", "") for c in cats][:15], "found_via": (f.get("found_via") or [])[:3]}
    lic = (f.get("license") or "").lower()
    if not lic or not re.search(r"cc|public domain|pd|gfdl|attribution|no restrictions", lic):
        rec["verify"] = True; rec["verify_reason"] = f"license '{f.get('license')}' needs review"
    if ctx == "other" and kind in ("game/team",):
        rec["verify"] = True; rec["verify_reason"] = (rec.get("verify_reason", "") + "; " if rec.get("verify_reason") else "") + "UConn link inferred only from category/search"
    ALLPHOTOS.append(rec)
    if ctx == "uconn" or kind in ("arena",):
        GAMEPHOTOS.append(rec)

# attach UConn-context extra photos to each player record
for pr in player_imgs + no_free:
    extras = [ {"file_page": g["file_page"], "thumb_url": g["thumb_url"], "image_url": g["image_url"], "license": g["license"], "author": g["author"], "context": g["context"], "date": g["date"]}
               for g in ALLPHOTOS if pr["player_name"] in g["subjects"] and g["file_page"] != pr.get("file_page")]
    pr["more_photos"] = sorted(extras, key=lambda e: e["context"] != "uconn")[:12]
    if pr.get("context") != "uconn":
        bu = next((e for e in pr["more_photos"] if e["context"] == "uconn"), None)
        if bu: pr["best_uconn_photo"] = bu
    if not pr.get("image_url"):
        uc = [e for e in extras if e["context"] == "uconn"] or extras
        if uc:
            pr["fallback_photo"] = uc[0]

from collections import Counter
save("images.json", {"generated": "2026-09-30",
    "note": "All images are real photographs/files hosted on Wikimedia Commons with the license and author recorded from Commons metadata. 'context' tells whether the photo shows the player at UConn, in the NBA, or elsewhere. Attribution (author + license) is required for CC BY/BY-SA files.",
    "players": player_imgs, "players_without_free_image": no_free, "photos": GAMEPHOTOS})
print("players with image", len(player_imgs), Counter(p["context"] for p in player_imgs), "no free image", len(no_free))
print("photos", len(GAMEPHOTOS), Counter(p["kind"] for p in GAMEPHOTOS), Counter(p["context"] for p in GAMEPHOTOS))
print("players w/o page image but with a Commons photo", sum(1 for p in no_free if p.get("fallback_photo")))
print("seasons covered", sorted(Counter(p["season"] for p in GAMEPHOTOS if p["season"]).items()))
