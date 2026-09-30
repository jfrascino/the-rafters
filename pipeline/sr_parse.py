"""Parsers for cached Sports-Reference CBB pages. Pure functions: html -> dict.

Field names follow SR's data-stat attributes. Numbers -> int/float, empty -> None.
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup

COMMENT_RE = re.compile(r"<!--(.*?)-->", re.S)
INT_RE = re.compile(r"^[-+]?\d+$")
FLOAT_RE = re.compile(r"^[-+]?\d*\.\d+$")
# fields that look numeric but must stay strings
STR_FIELDS = {"number", "height", "class", "pos", "year_id", "season", "game_streak",
              "date_game", "time_game", "rsci", "summary", "hometown", "high_school",
              "team_name_abbr", "conf_abbr", "awards", "player", "name_display", "entity",
              "game_location", "game_result", "overtimes", "arena", "coaches", "round_max",
              "opp_name", "game_type", "team", "school_name", "info", "stat", "coach"}


def soup(html):
    return BeautifulSoup(COMMENT_RE.sub(r"\1", html), "lxml")


def num(v, key=None):
    if v is None:
        return None
    v = v.strip().replace("\xa0", " ")
    if v == "":
        return None
    if key in STR_FIELDS:
        return v
    s = v.replace(",", "") if re.match(r"^[-+]?\d{1,3}(,\d{3})+(\.\d+)?$", v) else v
    if INT_RE.match(s):
        return int(s)
    if FLOAT_RE.match(s):
        return float(s)
    if s.endswith("%") and FLOAT_RE.match(s[:-1]) or (s.endswith("%") and INT_RE.match(s[:-1])):
        return float(s[:-1])
    return v


def slug_from(href, kind):
    if not href:
        return None
    if kind == "player":
        m = re.search(r"/cbb/players/([^/.]+)\.html", href)
    elif kind == "school":
        m = re.search(r"/cbb/schools/([^/]+)/", href)
    elif kind == "box":
        m = re.search(r"/cbb/boxscores/([^/.]+)\.html", href)
    elif kind == "coach":
        m = re.search(r"/cbb/coaches/([^/.]+)\.html", href)
    elif kind == "conf":
        m = re.search(r"/cbb/conferences/([^/]+)/", href)
    else:
        return None
    return m.group(1) if m else None


def cell_value(c):
    key = c.get("data-stat")
    return num(c.get_text(" ", strip=True), key)


def row_dict(tr):
    d = {}
    for c in tr.find_all(["th", "td"], recursive=False):
        key = c.get("data-stat")
        if not key:
            continue
        d[key] = cell_value(c)
        for a in c.find_all("a", href=True):
            h = a["href"]
            p = slug_from(h, "player")
            if p and "sr_id" not in d:
                d["sr_id"] = p
                continue
            sch = slug_from(h, "school")
            if sch and key in ("team_name_abbr", "school_name", "team", "opp_name", "school"):
                d[key + "_slug"] = sch
            b = slug_from(h, "box")
            if b:
                d["box_slug"] = b
            co = slug_from(h, "coach")
            if co:
                d.setdefault("coach_ids", []).append(co)
        if key in ("player", "name_display") and "sr_id" not in d and c.get("data-append-csv"):
            d["sr_id"] = c["data-append-csv"]
    return d


def is_header_row(tr):
    cls = tr.get("class") or []
    return any(k in cls for k in ("thead", "over_header", "spacer", "partial_table")) and "partial_table" not in cls


def parse_table(t, include_notes=False):
    if t is None:
        return None
    out = {"rows": [], "footer": []}
    tb = t.find("tbody") or t
    for tr in tb.find_all("tr", recursive=False):
        cls = tr.get("class") or []
        if "thead" in cls or "over_header" in cls or "spacer" in cls:
            continue
        if "note" in cls and not include_notes:
            pass
        d = row_dict(tr)
        if not d:
            continue
        if "note" in cls:
            d["_note_row"] = True
        out["rows"].append(d)
    tf = t.find("tfoot")
    if tf:
        for tr in tf.find_all("tr"):
            d = row_dict(tr)
            if d:
                out["footer"].append(d)
    return out


def table_rows(s, tid):
    t = s.find("table", id=tid)
    if t is None:
        return None
    return parse_table(t)


def _label_paras(meta):
    """Map 'Record' -> <p> element for every <p><strong>Label:</strong>...</p>."""
    res = {}
    for p in meta.find_all("p"):
        st = p.find("strong")
        if not st:
            continue
        label = st.get_text(" ", strip=True).rstrip(":").strip()
        res.setdefault(label, p)
    return res


def _val_rank(text):
    m = re.search(r"([-+]?\d+\.?\d*)\s*\((\d+)\w*\s+of\s+(\d+)\)", text)
    if m:
        return {"value": num(m.group(1)), "rank": int(m.group(2)), "of": int(m.group(3))}
    m = re.search(r"([-+]?\d+\.?\d*)", text)
    return {"value": num(m.group(1)), "rank": None, "of": None} if m else None


def parse_postseason_para(p, label):
    """Parse NCAA/NIT paragraph lines into games list."""
    html = str(p)
    txt = p.get_text(" ", strip=True)
    res = {"label": label, "text": re.sub(r"\s+", " ", txt.split(":", 1)[-1]).strip()}
    m = re.search(r"#(\d+) seed in ([^)]+)\)", txt)
    if m:
        res["seed"] = int(m.group(1))
        res["region"] = m.group(2).strip()
    games = []
    parts = re.split(r"<br\s*/?>", html)
    for part in parts:
        ps = BeautifulSoup(part, "lxml")
        t = re.sub(r"\s+", " ", ps.get_text(" ", strip=True))
        gm = re.search(r"(Won|Lost)\s+(.+?)\s*\(\s*(\d+)-(\d+)\s*(?:\(?(\d?OT)\)?)?\s*\)\s*versus\s*(?:#(\d+)\s*)?(.+)$", t)
        if not gm:
            continue
        g = {"result": "W" if gm.group(1) == "Won" else "L", "round": gm.group(2).strip(),
             "pts": int(gm.group(3)), "opp_pts": int(gm.group(4)),
             "opp_seed": int(gm.group(6)) if gm.group(6) else None,
             "opp_name": gm.group(7).strip(), "box_slug": None, "opp_slug": None}
        for a in ps.find_all("a", href=True):
            b = slug_from(a["href"], "box")
            if b:
                g["box_slug"] = b
            sc = slug_from(a["href"], "school")
            if sc:
                g["opp_slug"] = sc
        if g["result"] == "L" and g["pts"] > g["opp_pts"]:  # SR lists winner's score first
            g["pts"], g["opp_pts"] = g["opp_pts"], g["pts"]
        if gm.group(5):
            g["overtimes"] = gm.group(5)
        games.append(g)
    res["games"] = games
    return res


def parse_season_meta(s):
    meta = s.find(id="meta")
    out = {}
    if meta is None:
        return out
    h1 = meta.find("h1")
    if h1:
        spans = [x.get_text(strip=True) for x in h1.find_all("span")]
        out["label"] = spans[0] if spans else None
        out["team_name"] = spans[1] if len(spans) > 1 else None
    L = _label_paras(meta)
    out["raw"] = {k: re.sub(r"\s+", " ", p.get_text(" ", strip=True)) for k, p in L.items()}
    if "Record" in L:
        t = re.sub(r"\s+", " ", L["Record"].get_text(" ", strip=True))
        m = re.search(r"Record:\s*(\d+)-(\d+)", t)
        if m:
            out["wins"], out["losses"] = int(m.group(1)), int(m.group(2))
        m = re.search(r"\((\d+)-(\d+),\s*([^ ]+)\s+in\s+(.+?)\)", t)
        if m:
            out["conf_wins"], out["conf_losses"] = int(m.group(1)), int(m.group(2))
            out["conf_finish"] = m.group(3)
            out["conference"] = re.sub(r"\s*MBB$", "", m.group(4).strip())
        a = L["Record"].find("a", href=True)
        if a:
            out["conf_slug"] = slug_from(a["href"], "conf")
    if "Rank" in L:
        t = L["Rank"].get_text(" ", strip=True)
        m = re.search(r"(\d+)\w*\s+in the\s+(.+)$", t)
        if m:
            out["rank_final_text"] = m.group(0)
            if "Final AP" in m.group(2):
                out["ap_final_meta"] = int(m.group(1))
    for key in ("Coach", "Coaches"):
        if key in L:
            p = L[key]
            out["coach_text"] = re.sub(r"\s+", " ", p.get_text(" ", strip=True).split(":", 1)[-1]).strip()
            coaches = []
            for a in p.find_all("a", href=True):
                cid = slug_from(a["href"], "coach")
                if cid:
                    coaches.append({"name": a.get_text(strip=True), "sr_coach_id": cid})
            # records per coach e.g. "Jim Calhoun (18-7), George Blaney (2-5)"
            for c in coaches:
                m = re.search(re.escape(c["name"]) + r"\s*\((\d+)-(\d+)\)", out["coach_text"])
                if m:
                    c["wins"], c["losses"] = int(m.group(1)), int(m.group(2))
            out["coaches"] = coaches
    for lab, key in (("PS/G", "pts_per_g"), ("PA/G", "opp_pts_per_g"), ("SRS", "srs"), ("SOS", "sos"),
                     ("ORtg", "off_rtg"), ("DRtg", "def_rtg"), ("Pace", "pace"), ("Net Rtg", "net_rtg")):
        if lab in L:
            out[key] = _val_rank(L[lab].get_text(" ", strip=True).split(":", 1)[-1])
    post = []
    for k, p in L.items():
        if "Tournament" in k or k in ("NIT", "CBI", "CIT", "NCAA"):
            post.append(parse_postseason_para(p, k))
    out["postseason"] = post
    for k, p in L.items():
        if k.startswith("Preseason Odds"):
            out["preseason_odds"] = out["raw"][k].split(":", 1)[-1].strip()
    return out


def parse_team_stat_table(s, tid):
    """season-total_per_game style: rows Team / Rank / Opponent / Rank."""
    t = s.find("table", id=tid)
    if t is None:
        return None
    res = {}
    cur = None
    for tr in (t.find("tbody") or t).find_all("tr", recursive=False):
        d = row_dict(tr)
        ent = d.pop("entity", None)
        if ent in ("Team", "Opponent"):
            cur = ent.lower()
            res[cur] = d
        elif ent and ent.startswith("Rank") and cur:
            res[cur + "_rank"] = {k: (int(re.match(r"\d+", v).group()) if isinstance(v, str) and re.match(r"\d+", v) else v)
                                 for k, v in d.items()}
        elif ent:
            res[ent.lower().replace(" ", "_")] = d
    return res


def parse_season(html, year):
    s = soup(html)
    out = {"year": year, "label": f"{year-1}-{str(year)[2:]}"}
    out["meta"] = parse_season_meta(s)
    # roster
    ro = table_rows(s, "roster")
    out["roster"] = ro["rows"] if ro else []
    stats = {}
    for key, tid in (("per_game", "players_per_game"), ("totals", "players_totals"),
                     ("per_min", "players_per_min"), ("per_poss", "players_per_poss"),
                     ("advanced", "players_advanced")):
        t = table_rows(s, tid)
        if t is not None:
            stats[key] = t["rows"]
            stats[key + "_team_totals"] = t["footer"]
        tc = table_rows(s, tid + "_conf")
        if tc is not None:
            stats[key + "_conf"] = tc["rows"]
    team = {}
    for key, tid in (("per_game", "season-total_per_game"), ("totals", "season-total_totals"),
                     ("conf_per_game", "conf_per_game"), ("conf_totals", "conf_totals"),
                     ("advanced", "season-total_advanced"), ("conf_advanced", "conf_advanced")):
        r = parse_team_stat_table(s, tid)
        if r:
            team[key] = r
    stats["team"] = {k: v.get("team") for k, v in team.items()}
    stats["team_rank"] = {k: v.get("team_rank") for k, v in team.items()}
    stats["opponent"] = {k: v.get("opponent") for k, v in team.items()}
    stats["opponent_rank"] = {k: v.get("opponent_rank") for k, v in team.items()}
    out["stats"] = stats
    known = {"roster", "players_per_game", "players_totals", "players_per_min", "players_per_poss",
             "players_advanced", "season-total_per_game", "season-total_totals", "conf_per_game",
             "conf_totals", "season-total_advanced", "conf_advanced"}
    known |= {k + "_conf" for k in known}
    extra = {}
    for t in s.find_all("table", id=True):
        if t["id"] not in known:
            extra[t["id"]] = parse_table(t)
    if extra:
        out["other_tables"] = extra
    return out


MONTHS = "%a, %b %d, %Y"


def iso_date(txt):
    if not txt:
        return None
    for fmt in (MONTHS, "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(txt.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None


def parse_schedule(html):
    s = soup(html)
    games = []
    t = s.find("table", id="schedule")
    if t is not None:
        for tr in t.find("tbody").find_all("tr", recursive=False):
            if "thead" in (tr.get("class") or []):
                continue
            d = row_dict(tr)
            if not d or d.get("g") is None:
                continue
            oc = tr.find(attrs={"data-stat": "opp_name"})
            rank = None
            if oc is not None:
                note = oc.find("span", class_="note")
                if note:
                    m = re.search(r"\d+", note.get_text())
                    rank = int(m.group()) if m else None
                    note.extract()
                a = oc.find("a")
                d["opp_name"] = (a.get_text(strip=True) if a else oc.get_text(" ", strip=True)).strip()
                if not a:  # plain text "Name(12)"
                    m = re.match(r"^(.*?)\s*\((\d+)\)\s*$", d["opp_name"])
                    if m:
                        d["opp_name"], rank = m.group(1), int(m.group(2))
            d["opp_rank"] = rank
            d["opp_slug"] = d.pop("opp_name_slug", None)
            d["date"] = iso_date(d.get("date_game"))
            loc = d.get("game_location")
            d["site"] = {"@": "away", "N": "neutral"}.get(loc, "home")
            games.append(d)
    polls = []
    p = s.find("table", id="polls")
    if p is not None:
        head = p.find("thead").find_all("tr")[-1].find_all(["th", "td"])
        cols = [(c.get("data-stat"), c.get_text(strip=True)) for c in head]
        for tr in p.find("tbody").find_all("tr"):
            cells = tr.find_all(["th", "td"])
            name = cells[0].get_text(strip=True)
            for (ds, lab), c in zip(cols[1:], cells[1:]):
                polls.append({"poll": "AP", "school": name, "week": lab, "date": ds,
                              "rank": num(c.get_text(strip=True))})
    return {"schedule": games, "polls": polls}


# ---------------- box scores ----------------

def parse_boxscore(html, slug):
    s = soup(html)
    out = {"slug": slug, "url": f"https://www.sports-reference.com/cbb/boxscores/{slug}.html"}
    sb = s.find("div", class_="scorebox")
    teams = []
    if sb:
        for div in sb.find_all("div", recursive=False):
            if "scorebox_meta" in (div.get("class") or []):
                continue
            strong = div.find("strong")
            sc = div.find("div", class_="score")
            if not strong and not sc:
                continue
            a = strong.find("a", href=True) if strong else None
            name = (a or strong).get_text(strip=True) if strong else None
            tm = {"name": name, "sr_slug": slug_from(a["href"], "school") if a else None,
                  "score": num(sc.get_text(strip=True)) if sc else None}
            rec = None
            for d2 in div.find_all("div", recursive=False):
                txt = d2.get_text(strip=True)
                if re.match(r"^\d+-\d+$", txt):
                    rec = txt
            tm["record"] = rec
            teams.append(tm)
        m = sb.find("div", class_="scorebox_meta")
        if m:
            lines = [d.get_text(" ", strip=True) for d in m.find_all("div", recursive=False)]
            lines = [l for l in lines if l and not l.startswith("Logos")]
            out["date_text"] = lines[0] if lines else None
            out["date"] = iso_date(re.sub(r"^\d{1,2}:\d{2}\s*[AP]M,\s*", "", lines[0], flags=re.I)) if lines else None
            if out["date"] is None and lines:
                mm = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", lines[0])
                out["date"] = iso_date(mm.group(1)) if mm else None
            out["arena"] = lines[1] if len(lines) > 1 else None
            out["notes"] = lines[2:] if len(lines) > 2 else []
    if not out.get("date"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", slug)
        out["date"] = m.group(1) if m else None
    # linescore
    ls = s.find("table", id="line-score")
    lines = []
    if ls is not None:
        head = ls.find("thead").find_all("tr")[-1].find_all(["th", "td"])
        periods = [c.get_text(strip=True) for c in head][1:]
        for tr in (ls.find("tbody") or ls).find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            a = cells[0].find("a", href=True)
            vals = [num(c.get_text(strip=True)) for c in cells[1:]]
            lines.append({"name": cells[0].get_text(strip=True),
                          "sr_slug": slug_from(a["href"], "school") if a else None,
                          "periods": periods, "values": vals})
    ff = table_rows(s, "four-factors")
    ff_rows = ff["rows"] if ff else []
    gi = table_rows(s, "game-info")
    out["game_info"] = {r.get("info"): r.get("stat") for r in gi["rows"]} if gi else {}
    # officials / attendance anywhere in page text
    txt = s.get_text("\n", strip=True)
    m = re.search(r"Officials?:\s*\n?(.+)", txt)
    out["officials"] = [x.strip() for x in re.split(r",", m.group(1)) if x.strip()] if m else None
    m = re.search(r"Attendance:\s*\n?([\d,]+)", txt)
    out["attendance"] = int(m.group(1).replace(",", "")) if m else None
    for k, v in list(out["game_info"].items()):
        if k and k.lower().startswith("attendance") and out["attendance"] is None:
            out["attendance"] = num(str(v).replace(",", ""))
        if k and k.lower().startswith("official") and out["officials"] is None:
            out["officials"] = [x.strip() for x in str(v).split(",")]
    # per-team box tables
    box_tables = {}
    for t in s.find_all("table", id=True):
        m = re.match(r"box-score-(basic|advanced)-(.+)$", t["id"])
        if m:
            box_tables.setdefault(m.group(2), {})[m.group(1)] = t
    # order teams per scorebox; fill if scorebox missing
    if not teams:
        teams = [{"name": l["name"], "sr_slug": l["sr_slug"], "score": l["values"][-1] if l["values"] else None}
                 for l in lines]
    for i, tm in enumerate(teams):
        key = tm.get("sr_slug")
        ln = next((l for l in lines if l["sr_slug"] and l["sr_slug"] == key), lines[i] if i < len(lines) else None)
        if ln:
            tm["linescore"] = [{"period": p, "pts": v} for p, v in zip(ln["periods"], ln["values"]) if p != "T"]
        f = next((r for r in ff_rows if r.get("school_name_slug") == key), ff_rows[i] if i < len(ff_rows) else None)
        if f:
            f = dict(f)
            f.pop("school_name", None)
            f.pop("school_name_slug", None)
        tm["four_factors"] = f
        bt = box_tables.get(key) or (list(box_tables.values())[i] if i < len(box_tables) else {})
        players, totals = [], None
        adv = {}
        if bt.get("advanced") is not None:
            pa = parse_table(bt["advanced"])
            for r in pa["rows"]:
                adv[r.get("sr_id") or r.get("player")] = r
            adv_tot = pa["footer"][0] if pa["footer"] else None
        else:
            adv_tot = None
        if bt.get("basic") is not None:
            tb = bt["basic"].find("tbody")
            starter = True
            for tr in tb.find_all("tr", recursive=False):
                if "thead" in (tr.get("class") or []):
                    starter = False
                    continue
                d = row_dict(tr)
                if not d:
                    continue
                d["starter"] = starter
                # DNP etc: reason text in merged cell
                reason = tr.find("td", attrs={"data-stat": "reason"})
                if reason:
                    d["reason"] = reason.get_text(strip=True)
                a = adv.get(d.get("sr_id") or d.get("player"))
                if a:
                    d["advanced"] = {k: v for k, v in a.items() if k not in ("player", "sr_id", "mp")}
                players.append(d)
            tf = bt["basic"].find("tfoot")
            if tf and tf.find("tr"):
                totals = row_dict(tf.find("tr"))
                totals.pop("player", None)
                if adv_tot:
                    totals["advanced"] = {k: v for k, v in adv_tot.items() if k not in ("player", "mp")}
        tm["players"] = players
        tm["totals"] = totals
    out["teams"] = teams
    return out


# ---------------- players ----------------

def parse_player(html, sr_id):
    s = soup(html)
    out = {"sr_id": sr_id, "url": f"https://www.sports-reference.com/cbb/players/{sr_id}.html"}
    meta = s.find(id="meta")
    bio = {}
    if meta:
        h1 = meta.find("h1")
        out["name"] = h1.get_text(" ", strip=True) if h1 else None
        img = meta.find("div", class_="media-item")
        img = img.find("img") if img else None
        out["photo_url"] = img.get("src") if img else None
        paras = meta.find_all("p")
        lines = []
        for p in paras:
            t = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
            if t:
                lines.append(t)
            st = p.find("strong")
            if st:
                lab = st.get_text(" ", strip=True).rstrip(":").strip()
                val = re.sub(r"\s+", " ", t.split(":", 1)[-1]).strip() if ":" in t else t
                val = re.sub(r"\s+([,)])", r"\1", val)
                bio[lab] = val
                if lab == "School" or lab == "Schools":
                    bio["school_slugs"] = [slug_from(a["href"], "school") for a in p.find_all("a", href=True)
                                           if slug_from(a["href"], "school")]
                if lab == "Draft":
                    for a in p.find_all("a", href=True):
                        m2 = re.search(r"/teams/([A-Z]+)/", a["href"])
                        if m2:
                            bio["draft_team_abbr"] = m2.group(1)
                if lab.startswith("Born"):
                    sp = p.find("span", attrs={"data-birth": True})
                    if sp:
                        bio["birth_date"] = sp["data-birth"]
                    bp = p.find("span", attrs={"itemprop": "birthPlace"})
                    if bp:
                        bio["birth_place"] = re.sub(r"\s+", " ", bp.get_text(" ", strip=True)).lstrip("in ").strip()
            elif t.startswith("(") and "nickname" not in bio:
                bio["nicknames"] = t
            m = re.search(r"(\d+-\d+),?\s*(\d+)\s*lb", t)
            if m:
                bio["height"], bio["weight"] = m.group(1), int(m.group(2))
        out["bio_lines"] = lines
        m = s.find("span", attrs={"data-birth": True})
        if m and "birth_date" not in bio:
            bio["birth_date"] = m["data-birth"]
    out["bio"] = bio
    og = s.find("meta", property="og:image")
    out["og_image"] = og["content"] if og else None
    if not out.get("photo_url") and out["og_image"] and "/images/players/" in out["og_image"]:
        out["photo_url"] = out["og_image"]
    # draft
    d = bio.get("Draft")
    out["draft_text"] = d
    if d:
        m = re.search(r"(\d+)\w* round \((\d+)\w* pick, (\d+)\w* overall\),?\s*(\d{4})", d)
        out["draft"] = {"text": d, "round": int(m.group(1)), "pick": int(m.group(2)),
                        "overall": int(m.group(3)), "year": int(m.group(4)),
                        "team": d.split(",")[0].strip() or None,
                        "team_abbr": bio.get("draft_team_abbr")} if m else {"text": d}
    else:
        out["draft"] = None
    # NBA link
    nba = None
    for a in s.find_all("a", href=True):
        if re.search(r"basketball-reference\.com/players/\w/\w+\.html", a["href"]):
            nba = a["href"]
            break
    out["nba_url"] = nba
    # stat tables
    tables = {}
    for t in s.find_all("table", id=True):
        pt = parse_table(t)
        for r in pt["rows"] + pt["footer"]:
            if "team_name_abbr_slug" in r:
                r["school_slug"] = r.pop("team_name_abbr_slug")
        tables[t["id"]] = {"rows": pt["rows"], "career": pt["footer"]}
    out["tables"] = tables
    # awards
    awards = []
    aw = s.find(id="leaderboard_awards")
    if aw:
        for sp in aw.find_all("span"):
            links = sp.find_all("a")
            if not links:
                continue
            season = links[0].get_text(strip=True)
            name = links[1].get_text(strip=True) if len(links) > 1 else sp.get_text(" ", strip=True)
            sm = sp.find("small")
            awards.append({"season": season, "award": name,
                           "detail": sm.get_text(" ", strip=True).lstrip("- ").strip() if sm else None,
                           "url": links[-1].get("href"),
                           "text": re.sub(r"\s+", " ", sp.get_text(" ", strip=True))})
    out["awards"] = awards
    bl = s.find("ul", id="bling")
    out["bling"] = [li.get_text(" ", strip=True) for li in bl.find_all("li")] if bl else []
    lbs = {}
    for dv in s.find_all("div", id=re.compile(r"^leaderboard_")):
        if dv["id"] in ("leaderboard_awards", "leaderboard_sh"):
            continue
        items = [re.sub(r"\s+", " ", x.get_text(" ", strip=True)) for x in dv.find_all("td")] or \
                [re.sub(r"\s+", " ", x.get_text(" ", strip=True)) for x in dv.find_all("span")]
        h = dv.find(["h4", "caption"])
        lbs[dv["id"].replace("leaderboard_", "")] = {"title": h.get_text(strip=True) if h else None,
                                                     "entries": [i for i in items if i]}
    out["leaderboards"] = lbs
    return out


# ---------------- school index / coaches / gamelog / adv stats ----------------

def parse_generic_tables(html):
    s = soup(html)
    return {t["id"]: parse_table(t) for t in s.find_all("table", id=True)}


def parse_school_adv(html, school="connecticut"):
    s = soup(html)
    res = {}
    for t in s.find_all("table", id=True):
        pt = parse_table(t)
        for r in pt["rows"]:
            if r.get("school_name_slug") == school:
                res[t["id"]] = r
    return res
