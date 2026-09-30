#!/usr/bin/env python3
"""
ESPN game-level data layer for the UConn men's basketball fan app.

Usage:
  python3 pipeline/espn_fetch.py --all      # full backfill, seasons 2003..current
  python3 pipeline/espn_fetch.py --update   # current season + any non-final game (cron / CI)
Options:
  --seasons 2011,2024   restrict to specific seasons (with --all)
  --rebuild             re-normalize every game from cache (no network for settled games)
  --quiet               less per-game output

Stdlib only. Raw responses are cached gzip'd in pipeline/cache.nosync/espn/.
Outputs go to pipeline/out/espn/. Output files are only rewritten when their
content changes, so the script is safe to run repeatedly (idempotent).

Cache policy
  * completed games: summary is "settled" once it was fetched >= SETTLE_HOURS
    after tip-off (recaps/videos get attached a few hours post-game); settled
    summaries are never re-downloaded.
  * scheduled / in-progress games and the current season schedule are always
    re-downloaded.
  * past-season schedules are re-downloaded only if the cached copy was fetched
    before that season ended.

NOTE: ESPN returns 403 "Access Denied" for browser User-Agents on some site-API
endpoints; the default Python-urllib UA works, so we deliberately send no
custom User-Agent.
"""
import argparse
import datetime as dt
import gzip
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

TEAM_ID = "41"
FIRST_SEASON = 2003
SITE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
CORE = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball"
HEADSHOT = "https://a.espncdn.com/i/headshots/mens-college-basketball/players/full/{}.png"
LOGO = "https://a.espncdn.com/i/teamlogos/ncaa/500/{}.png"

PIPE = Path(__file__).resolve().parent
CACHE = PIPE / "cache.nosync" / "espn"
OUT = PIPE / "out" / "espn"

DELAY = 0.4          # seconds between API requests
HEAD_DELAY = 0.15    # seconds between CDN HEAD requests
SETTLE_HOURS = 36    # a final game's summary is re-fetched until this long after tip
HEADSHOT_RECHECK_DAYS = 30

PLAY_FIELDS = ["period", "clock", "teamId", "awayScore", "homeScore", "scoringPlay",
               "scoreValue", "text", "shootingPlay", "x", "y", "athleteId", "typeId", "type"]

UTC = dt.timezone.utc


def now():
    return dt.datetime.now(UTC)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_dt(s):
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    if re.match(r".*T\d\d:\d\d\+", s):  # "2011-04-05T01:23+00:00"
        s = s.replace("+00:00", ":00+00:00")
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def current_season(t=None):
    t = t or now()
    return t.year + 1 if t.month >= 7 else t.year


def season_end(season):
    """Schedules fetched after this are final for that season."""
    return dt.datetime(season, 7, 1, tzinfo=UTC)


# ----------------------------------------------------------------------------- IO

def write_json(path, obj, compact=False):
    """Atomic write; returns True if the file content changed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        data = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    else:
        data = json.dumps(obj, ensure_ascii=False, indent=1)
    data = data.encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return False
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return True


def read_json(path, default=None):
    try:
        with open(path, "rb") as f:
            return json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


class Fetcher:
    def __init__(self, verbose=True):
        self.last = 0.0
        self.verbose = verbose
        self.stats = {"net": 0, "cache": 0, "errors": 0, "head": 0}
        self.failures = []
        CACHE.mkdir(parents=True, exist_ok=True)

    # -- low level
    def _wait(self, delay):
        gap = time.monotonic() - self.last
        if gap < delay:
            time.sleep(delay - gap)
        self.last = time.monotonic()

    def _request(self, url, method="GET", delay=DELAY, tries=5):
        """Returns (status, bytes|None). Retries 429/5xx/network errors with backoff."""
        err = None
        for attempt in range(tries):
            self._wait(delay)
            req = urllib.request.Request(url, method=method, headers={"Accept-Encoding": "gzip"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    body = r.read()
                    if r.headers.get("Content-Encoding") == "gzip":
                        body = gzip.decompress(body)
                    return r.status, body
            except urllib.error.HTTPError as e:
                if e.code in (400, 401, 403, 404, 410):
                    return e.code, None
                err = f"HTTP {e.code}"
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as e:
                err = f"{type(e).__name__}: {e}"
            back = min(60, 2 ** attempt * 1.5)
            if self.verbose:
                print(f"    retry {attempt + 1}/{tries} in {back:.0f}s ({err}) {url}", flush=True)
            time.sleep(back)
        return None, err

    # -- cached JSON
    def cache_path(self, name):
        return CACHE / f"{name}.json.gz"

    def load_cache(self, name):
        p = self.cache_path(name)
        if not p.exists():
            return None
        try:
            with gzip.open(p, "rb") as f:
                return json.loads(f.read())
        except (OSError, EOFError, json.JSONDecodeError):
            return None  # corrupt/partial -> refetch

    def save_cache(self, name, url, data):
        p = self.cache_path(name)
        entry = {"fetched": iso(now()), "url": url, "data": data}
        tmp = p.with_suffix(".tmp")
        with gzip.open(tmp, "wb", compresslevel=6) as f:
            f.write(json.dumps(entry, separators=(",", ":")).encode("utf-8"))
        os.replace(tmp, p)
        return entry

    def get(self, url, name, refresh=False, validate=None):
        """Cached GET. `refresh` may be a bool or fn(entry)->bool.
        On network failure falls back to cached copy. Returns entry dict or None."""
        entry = self.load_cache(name)
        need = entry is None or (refresh(entry) if callable(refresh) else refresh)
        if not need:
            self.stats["cache"] += 1
            return entry
        status, body = self._request(url)
        self.stats["net"] += 1
        data = None
        if status == 200 and body:
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = None
        if data is not None and (validate is None or validate(data)):
            return self.save_cache(name, url, data)
        self.stats["errors"] += 1
        self.failures.append(f"{name}: status={status} {'' if status else body}")
        if entry is not None:
            print(f"    ! {name} fetch failed ({status}); using cached copy", flush=True)
        return entry

    def head_ok(self, url):
        self.stats["head"] += 1
        status, _ = self._request(url, method="HEAD", delay=HEAD_DELAY, tries=3)
        if status is None:
            return None  # unknown (network)
        return status == 200


# ----------------------------------------------------------------------------- helpers

def ival(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v) if float(v).is_integer() else v
    s = str(v).strip()
    if s in ("", "-", "--"):
        return None
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        return None


def nval(s):
    """Stat display value -> number if numeric, else original string."""
    n = ival(s)
    return n if n is not None else s


def rank_of(v):
    r = ival(v)
    return r if r is not None and 0 < r < 99 else None


def best_logo(team):
    if not team:
        return None
    if team.get("logo"):
        return team["logo"]
    for lg in team.get("logos") or []:
        if "default" in (lg.get("rel") or []):
            return lg.get("href")
    if team.get("logos"):
        return team["logos"][0].get("href")
    return LOGO.format(team["id"]) if team.get("id") else None


def status_of(stype):
    stype = stype or {}
    name = (stype.get("name") or "").upper()
    state = stype.get("state")
    if "POSTPONED" in name:
        return "postponed"
    if "CANCEL" in name:
        return "canceled"
    if "FORFEIT" in name and stype.get("completed"):
        return "final"
    if state == "post" and stype.get("completed"):
        return "final"
    if state == "in" or "HALFTIME" in name or "IN_PROGRESS" in name or "END_PERIOD" in name:
        return "in"
    if state == "post":
        return (stype.get("description") or "post").lower()
    return "scheduled"


def valid_coord(c):
    if not isinstance(c, dict):
        return None, None
    x, y = c.get("x"), c.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None, None
    if abs(x) > 1000 or abs(y) > 1000:  # ESPN sentinel -214748340
        return None, None
    return x, y


STAT_KEYS = {
    "minutes": ("min",), "points": ("pts",),
    "fieldGoalsMade-fieldGoalsAttempted": ("fgm", "fga"),
    "threePointFieldGoalsMade-threePointFieldGoalsAttempted": ("tpm", "tpa"),
    "freeThrowsMade-freeThrowsAttempted": ("ftm", "fta"),
    "rebounds": ("reb",), "offensiveRebounds": ("oreb",), "defensiveRebounds": ("dreb",),
    "assists": ("ast",), "turnovers": ("to",), "steals": ("stl",), "blocks": ("blk",),
    "fouls": ("pf",),
}
STAT_ORDER = ["min", "pts", "fgm", "fga", "tpm", "tpa", "ftm", "fta", "reb", "oreb", "dreb",
              "ast", "to", "stl", "blk", "pf"]


def player_stats(keys, vals):
    if not vals:
        return None
    out = {k: None for k in STAT_ORDER}
    for key, v in zip(keys, vals):
        names = STAT_KEYS.get(key)
        if not names:
            continue
        if len(names) == 2:
            parts = str(v).split("-")
            if len(parts) == 2:
                out[names[0]], out[names[1]] = ival(parts[0]), ival(parts[1])
        else:
            out[names[0]] = ival(v)
    return out


# ----------------------------------------------------------------------------- normalize

def is_ncaa_postseason(season_type):
    return str(season_type) == "3"


def normalize_game(ev, season, season_type, summ):
    """ev: schedule event (may be None); summ: summary JSON (may be None)."""
    scomp = (ev or {}).get("competitions", [{}])[0] if ev else {}
    header = (summ or {}).get("header") or {}
    hcomp = (header.get("competitions") or [{}])[0]
    gid = str(header.get("id") or (ev or {}).get("id"))

    stype = (hcomp.get("status") or {}).get("type") or (scomp.get("status") or {}).get("type")
    status = status_of(stype)
    date = hcomp.get("date") or scomp.get("date") or (ev or {}).get("date")
    time_valid = hcomp.get("timeValid", header.get("timeValid", scomp.get("timeValid", True)))

    notes = []
    if header.get("gameNote"):
        notes.append(header["gameNote"])
    for n in (hcomp.get("notes") or []) + (scomp.get("notes") or []):
        h = n.get("headline")
        if h and h not in notes:
            notes.append(h)
    note = notes[0] if notes else None

    gi = (summ or {}).get("gameInfo") or {}
    v = gi.get("venue") or scomp.get("venue") or {}
    addr = v.get("address") or {}
    venue = None
    if v:
        venue = {"id": v.get("id"), "name": v.get("fullName"), "city": addr.get("city"),
                 "state": addr.get("state")}
        if v.get("capacity"):
            venue["capacity"] = v["capacity"]
        imgs = v.get("images") or []
        if imgs:
            venue["image"] = imgs[0].get("href")
    attendance = gi.get("attendance") or scomp.get("attendance") or None

    officials = [o.get("displayName") or o.get("fullName") for o in gi.get("officials") or []]

    bcasts = []
    for b in (hcomp.get("broadcasts") or []) + ((summ or {}).get("broadcasts") or []) + (scomp.get("broadcasts") or []):
        name = (b.get("media") or {}).get("shortName") or b.get("station") or (b.get("names") or [None])[0]
        if name and name not in bcasts:
            bcasts.append(name)

    # competitors
    sched_comp = {str(c.get("id")): c for c in scomp.get("competitors") or []}
    box_team = {}
    for t in ((summ or {}).get("boxscore") or {}).get("teams") or []:
        box_team[str(t["team"]["id"])] = t
    box_players = {}
    for p in ((summ or {}).get("boxscore") or {}).get("players") or []:
        box_players[str(p["team"]["id"])] = p

    comps = hcomp.get("competitors") or scomp.get("competitors") or []
    postseason = is_ncaa_postseason(season_type)
    teams = []
    for c in comps:
        tid = str(c.get("id") or c["team"]["id"])
        sc = sched_comp.get(tid, {})
        bt = box_team.get(tid, {})
        tm = dict(sc.get("team") or {})
        tm.update({k: v2 for k, v2 in (c.get("team") or {}).items() if v2})
        btm = bt.get("team") or {}
        rank_raw = c.get("rank") if c.get("rank") is not None else (sc.get("curatedRank") or {}).get("current")
        curated = (sc.get("curatedRank") or {}).get("current")
        rec_after = None
        conf_rec = None
        for r in sc.get("record") or []:
            if r.get("type") == "total":
                rec_after = r.get("displayValue") or r.get("summary")
            elif r.get("type") == "vsconf":
                conf_rec = r.get("displayValue") or r.get("summary")
        season_rec = None
        for r in c.get("record") or []:
            if r.get("type") == "total":
                season_rec = r.get("summary") or r.get("displayValue")
        score = c.get("score")
        if isinstance(score, dict):
            score = score.get("value")
        if score is None:
            ss = sc.get("score")
            score = ss.get("value") if isinstance(ss, dict) else ss
        linescores = [ival(l.get("displayValue", l.get("value"))) for l in c.get("linescores") or []]

        team = {
            "homeAway": c.get("homeAway") or sc.get("homeAway"),
            "id": tid,
            "abbr": tm.get("abbreviation") or btm.get("abbreviation"),
            "name": tm.get("displayName") or btm.get("displayName"),
            "shortName": tm.get("shortDisplayName") or btm.get("shortDisplayName"),
            "location": tm.get("location") or btm.get("location"),
            "nickname": tm.get("name") or btm.get("name"),
            "color": tm.get("color") or btm.get("color"),
            "altColor": tm.get("alternateColor") or btm.get("alternateColor"),
            "logo": btm.get("logo") or best_logo(tm) or LOGO.format(tid),
            "rank": None if postseason else rank_rank(rank_raw, curated),
            "seed": rank_of(rank_raw if rank_raw is not None else curated) if postseason else None,
            "record": rec_after or season_rec,
            "confRecord": conf_rec,
            "score": ival(score) if status in ("final", "in") else None,
            "winner": c.get("winner", sc.get("winner")) if status == "final" else None,
            "linescores": linescores,
            "stats": None,
            "players": [],
        }
        if not postseason:
            team.pop("seed")
        if bt.get("statistics"):
            team["stats"] = {s.get("label") or s.get("name"): nval(s.get("displayValue"))
                             for s in bt["statistics"]}
        bp = box_players.get(tid)
        if bp:
            for grp in bp.get("statistics") or []:
                keys = grp.get("keys") or []
                for a in grp.get("athletes") or []:
                    ath = a.get("athlete") or {}
                    pl = {
                        "id": str(ath.get("id")) if ath.get("id") else None,
                        "name": ath.get("displayName"),
                        "short": ath.get("shortName"),
                        "jersey": (ath.get("jersey") or "").strip() or None,
                        "pos": (ath.get("position") or {}).get("abbreviation"),
                        "starter": bool(a.get("starter")),
                        "dnp": bool(a.get("didNotPlay")) or not a.get("stats"),
                        "headshot": (ath.get("headshot") or {}).get("href"),
                    }
                    if a.get("ejected"):
                        pl["ejected"] = True
                    if a.get("reason"):
                        pl["reason"] = a["reason"]
                    pl.update(player_stats(keys, a.get("stats")) or {k: None for k in STAT_ORDER})
                    team["players"].append(pl)
        # some old games (e.g. 2004 title game) list players but carry no individual stats
        team["hasPlayerStats"] = any(p["pts"] is not None or p["min"] is not None for p in team["players"])
        if team["players"] and not team["hasPlayerStats"]:
            for pl in team["players"]:
                pl["dnp"] = None
        teams.append(team)
    teams.sort(key=lambda t: 0 if t["homeAway"] == "away" else 1)
    uconn_idx = next((i for i, t in enumerate(teams) if t["id"] == TEAM_ID), None)

    # leaders (compact)
    leaders = {}
    for lt in (summ or {}).get("leaders") or []:
        tid = str((lt.get("team") or {}).get("id"))
        d = {}
        for cat in lt.get("leaders") or []:
            if not cat.get("leaders"):
                continue
            l0 = cat["leaders"][0]
            a = l0.get("athlete") or {}
            d[cat.get("name")] = {"id": a.get("id"), "name": a.get("displayName"),
                                  "value": ival(l0.get("value")) if l0.get("value") is not None else l0.get("displayValue"),
                                  "summary": l0.get("summary")}
        if d:
            leaders[tid] = d

    # odds / predictor
    odds = None
    for o in ((summ or {}).get("pickcenter") or []) + ((summ or {}).get("odds") or []):
        if not isinstance(o, dict):
            continue
        fav = None
        if (o.get("homeTeamOdds") or {}).get("favorite"):
            fav = "home"
        elif (o.get("awayTeamOdds") or {}).get("favorite"):
            fav = "away"
        odds = {"provider": (o.get("provider") or {}).get("name"), "details": o.get("details"),
                "spread": o.get("spread"), "overUnder": o.get("overUnder"), "favorite": fav,
                "homeML": (o.get("homeTeamOdds") or {}).get("moneyLine"),
                "awayML": (o.get("awayTeamOdds") or {}).get("moneyLine")}
        if o.get("details") or o.get("spread") is not None or o.get("overUnder") is not None:
            break
    predictor = None
    pr = (summ or {}).get("predictor")
    if isinstance(pr, dict):
        def proj(side):
            x = pr.get(side) or {}
            return ival(x.get("gameProjection"))
        predictor = {"homeWinPct": proj("homeTeam"), "awayWinPct": proj("awayTeam"),
                     "header": pr.get("header")}

    # plays
    plays = []
    idx_of = {}
    for p in (summ or {}).get("plays") or []:
        x, y = valid_coord(p.get("coordinate"))
        ptype = (p.get("type") or {}).get("text") or ""
        if "freethrow" in ptype.replace(" ", "").lower() or "free throw" in (p.get("text") or "").lower():
            x = y = None  # ESPN stamps every free throw with a placeholder (25, 0)
        parts = p.get("participants") or []
        aid = ((parts[0] if parts else {}).get("athlete") or {}).get("id")
        idx_of[str(p.get("id"))] = len(plays)
        plays.append([
            (p.get("period") or {}).get("number"),
            (p.get("clock") or {}).get("displayValue"),
            (p.get("team") or {}).get("id"),
            p.get("awayScore"), p.get("homeScore"),
            1 if p.get("scoringPlay") else 0,
            p.get("scoreValue") or 0,
            p.get("text"),
            1 if p.get("shootingPlay") else 0,
            x, y,
            str(aid) if aid else None,
            (p.get("type") or {}).get("id"),
            (p.get("type") or {}).get("text"),
        ])
    wp = []
    for i, w in enumerate((summ or {}).get("winprobability") or []):
        pct = w.get("homeWinPercentage")
        if pct is None:
            continue
        wp.append([idx_of.get(str(w.get("playId")), i), round(float(pct), 4)])

    # article (sanity-check: ESPN occasionally attaches the wrong recap)
    article = None
    article_rejected = None
    art = (summ or {}).get("article")
    if isinstance(art, dict) and (art.get("headline") or art.get("story")):
        gdate = parse_dt(date)
        pub = parse_dt(art.get("published") or art.get("originallyPosted"))
        ok = str(art.get("gameId") or gid) == gid
        if ok and gdate and pub and not (gdate - dt.timedelta(days=3) <= pub <= gdate + dt.timedelta(days=10)):
            ok = False
        if ok:
            article = {
                "headline": art.get("headline"), "description": art.get("description"),
                "type": art.get("type"), "source": art.get("source"),
                "published": art.get("published"), "story": art.get("story"),
                "images": [{"url": im.get("url"), "caption": im.get("caption"), "credit": im.get("credit"),
                            "width": im.get("width"), "height": im.get("height")}
                           for im in art.get("images") or [] if im.get("url")],
            }
        else:
            article_rejected = {"headline": art.get("headline"), "published": art.get("published")}

    videos = []
    for vd in (summ or {}).get("videos") or []:
        links = vd.get("links") or {}
        src = links.get("source") or {}
        mp4 = (src.get("HD") or {}).get("href") or src.get("href") or ((links.get("mobile") or {}).get("source") or {}).get("href")
        hls = ((src.get("HLS") or {}).get("HD") or {}).get("href") or (src.get("HLS") or {}).get("href")
        web = (links.get("web") or {}).get("href")
        videos.append({"id": vd.get("id"), "headline": vd.get("headline"), "description": vd.get("description"),
                       "duration": vd.get("duration"), "thumbnail": vd.get("thumbnail"),
                       "published": vd.get("originalPublishDate"),
                       "links": {"mp4": mp4, "hls": hls, "web": web}})

    # news: only items tagged with one of the two teams (ESPN otherwise returns current league news)
    news = []
    team_ids = {t["id"] for t in teams}
    for a in (((summ or {}).get("news") or {}).get("articles") or []):
        tagged = {str(c.get("teamId")) for c in a.get("categories") or [] if c.get("teamId")}
        if not (tagged & team_ids):
            continue
        img = (a.get("images") or [{}])[0]
        news.append({"headline": a.get("headline"), "description": a.get("description"),
                     "published": a.get("published"),
                     "link": ((a.get("links") or {}).get("web") or {}).get("href"),
                     "image": img.get("url")})
        if len(news) >= 5:
            break

    periods = max([len(t["linescores"]) for t in teams] + [(scomp.get("status") or {}).get("period") or 0])
    game = {
        "id": gid,
        "season": season,
        "seasonType": int(season_type),
        "date": date,
        "timeTBD": not time_valid,
        "status": status,
        "statusDetail": (stype or {}).get("detail"),
        "ot": max(0, periods - 2) if status == "final" else None,
        "neutral": bool(hcomp.get("neutralSite", scomp.get("neutralSite", False))),
        "conferenceGame": bool(hcomp.get("conferenceCompetition", scomp.get("conferenceCompetition", False))),
        "note": note,
        "notes": notes if len(notes) > 1 else None,
        "venue": venue,
        "attendance": attendance,
        "officials": officials,
        "broadcasts": bcasts,
        "uconn": uconn_idx,
        "teams": teams,
        "leaders": leaders or None,
        "odds": odds,
        "predictor": predictor,
        "playFields": PLAY_FIELDS if plays else None,
        "plays": plays,
        "wp": wp,
        "article": article,
        "videos": videos,
        "news": news,
        "source": {"summary": summ is not None,
                   "boxscore": (hcomp.get("boxscoreSource") if summ else None),
                   "playByPlay": (hcomp.get("playByPlaySource") if summ else None)},
    }
    if article_rejected:
        game["articleRejected"] = article_rejected
    return game


def rank_rank(rank_raw, curated):
    r = rank_of(rank_raw)
    return r if r is not None else rank_of(curated)


def schedule_row(g, ev):
    ui = g.get("uconn")
    if ui is None or len(g["teams"]) != 2:
        return None
    us, opp = g["teams"][ui], g["teams"][1 - ui]
    result = None
    if g["status"] == "final" and us["score"] is not None and opp["score"] is not None:
        result = "W" if us["score"] > opp["score"] else "L"
        if us.get("winner") is True:
            result = "W"
        elif us.get("winner") is False and opp.get("winner") is True:
            result = "L"
    scomp = ((ev or {}).get("competitions") or [{}])[0]
    tickets = None
    for t in scomp.get("tickets") or []:
        tickets = {"summary": t.get("summary"),
                   "url": ((t.get("links") or [{}])[0]).get("href")}
        break
    row = {
        "id": g["id"], "date": g["date"], "timeTBD": g["timeTBD"], "seasonType": g["seasonType"],
        "status": g["status"], "statusDetail": g["statusDetail"],
        "homeAway": us["homeAway"], "neutral": g["neutral"], "conferenceGame": g["conferenceGame"],
        "note": g["note"],
        "opp": {"id": opp["id"], "name": opp["name"], "short": opp.get("shortName"), "abbr": opp["abbr"],
                "logo": opp["logo"], "rank": opp.get("rank"), "seed": opp.get("seed")},
        "uconnRank": us.get("rank"), "uconnSeed": us.get("seed"),
        "venue": g["venue"] and {k: g["venue"].get(k) for k in ("name", "city", "state")},
        "broadcast": ", ".join(g["broadcasts"]) or None,
        "score": us["score"], "oppScore": opp["score"], "result": result,
        "ot": g["ot"], "record": us.get("record"), "attendance": g["attendance"],
        "tickets": tickets if g["status"] == "scheduled" else None,
        "has": {"box": bool(us.get("hasPlayerStats")), "lineup": bool(us["players"]), "plays": bool(g["plays"]), "wp": bool(g["wp"]),
                "shots": sum(1 for p in g["plays"] if p[8] and p[9] is not None) >= 10,
                "article": bool(g["article"]), "videos": len(g["videos"])},
    }
    return row


# ----------------------------------------------------------------------------- pipeline

class Pipeline:
    def __init__(self, args):
        self.args = args
        self.f = Fetcher(verbose=not args.quiet)
        self.cur = current_season()
        self.changed = {"games": 0, "schedules": 0}
        self.games_seen = {}
        self.t0 = time.time()

    # -- schedules
    def schedule(self, season, st):
        name = f"schedule_{season}_{st}"
        url = f"{SITE}/teams/{TEAM_ID}/schedule?season={season}&seasontype={st}"
        if season >= self.cur:
            refresh = True
        else:
            refresh = lambda e: parse_dt(e["fetched"]) < season_end(season)
        e = self.f.get(url, name, refresh=refresh, validate=lambda d: "events" in d)
        return (e or {}).get("data", {}).get("events") or []

    def season_events(self, season, network=True):
        """-> ordered dict id -> (event, seasontype)"""
        evs = {}
        for st in (2, 3):
            if network:
                lst = self.schedule(season, st)
            else:
                c = self.f.load_cache(f"schedule_{season}_{st}")
                lst = (c or {}).get("data", {}).get("events") or []
            for ev in lst:
                gid = str(ev["id"])
                ev_st = str((ev.get("seasonType") or {}).get("type") or st)
                if gid not in evs:
                    evs[gid] = (ev, ev_st)
                elif ev_st == "3":
                    evs[gid] = (ev, ev_st)
        return evs

    # -- summaries
    def summary(self, gid, ev, force=False):
        name = f"summary_{gid}"
        url = f"{SITE}/summary?event={gid}"

        def refresh(entry):
            if force:
                return True
            d = entry.get("data") or {}
            hc = ((d.get("header") or {}).get("competitions") or [{}])[0]
            st = status_of((hc.get("status") or {}).get("type"))
            sched_st = status_of((((ev or {}).get("competitions") or [{}])[0].get("status") or {}).get("type")) if ev else None
            fetched = parse_dt(entry["fetched"])
            gdate = parse_dt(hc.get("date") or (ev or {}).get("date"))
            if sched_st == "final" and st != "final":
                return True
            if st == "final" or st in ("canceled", "postponed"):
                return bool(gdate and fetched < gdate + dt.timedelta(hours=SETTLE_HOURS))
            # scheduled / in progress: always refresh unless it's a stale ghost long past
            if gdate and now() - gdate > dt.timedelta(days=14) and fetched > gdate + dt.timedelta(days=14):
                return False
            return True

        e = self.f.get(url, name, refresh=refresh, validate=lambda d: isinstance(d.get("header"), dict))
        return (e or {}).get("data")

    def process_game(self, gid, season, ev, st, force=False, network=True):
        if network:
            summ = self.summary(gid, ev, force=force)
        else:
            summ = (self.f.load_cache(f"summary_{gid}") or {}).get("data")
        g = normalize_game(ev, season, st, summ)
        if write_json(OUT / "games" / f"{gid}.json", g, compact=True):
            self.changed["games"] += 1
        self.games_seen[gid] = g
        return g

    def write_schedule(self, season, evs, games):
        rows = []
        for gid, (ev, st) in evs.items():
            g = games.get(gid)
            if g is None:
                continue
            r = schedule_row(g, ev)
            if r:
                rows.append(r)
        rows.sort(key=lambda r: r["date"] or "")
        fin = [r for r in rows if r["result"]]
        w = sum(1 for r in fin if r["result"] == "W")
        doc = {"season": season, "label": f"{season - 1}-{str(season)[2:]}", "wins": w,
               "losses": len(fin) - w, "games": rows}
        if write_json(OUT / "schedules" / f"{season}.json", doc):
            self.changed["schedules"] += 1
        return doc

    def run_seasons(self, seasons, network=True, force_ids=()):
        for season in seasons:
            evs = self.season_events(season, network=network)
            games = {}
            for i, (gid, (ev, st)) in enumerate(evs.items()):
                g = self.process_game(gid, season, ev, st, force=gid in force_ids, network=network)
                games[gid] = g
            doc = self.write_schedule(season, evs, games)
            print(f"  {season}: {len(evs):3d} games  {doc['wins']}-{doc['losses']}  "
                  f"(net {self.f.stats['net']}, cache {self.f.stats['cache']}, {time.time() - self.t0:.0f}s)",
                  flush=True)

    # -- rosters
    def core_roster(self, season, network=True):
        """-> {athleteId: season-athlete dict} from core API"""
        name = f"core_athletes_{season}"
        url = f"{CORE}/seasons/{season}/teams/{TEAM_ID}/athletes?limit=200"
        if network:
            refresh = (lambda e: parse_dt(e["fetched"]) < now() - dt.timedelta(hours=12)) if season >= self.cur \
                else (lambda e: parse_dt(e["fetched"]) < season_end(season))
            e = self.f.get(url, name, refresh=refresh, validate=lambda d: "items" in d)
        else:
            e = self.f.load_cache(name)
        out = {}
        for it in ((e or {}).get("data") or {}).get("items") or []:
            ref = it.get("$ref") or ""
            m = re.search(r"/athletes/(\d+)", ref)
            if not m:
                continue
            aid = m.group(1)
            aname = f"core_athlete_{season}_{aid}"
            aurl = ref.replace("http://", "https://").replace(".pvt", ".com")
            if network:
                refresh = (lambda e2: parse_dt(e2["fetched"]) < now() - dt.timedelta(days=3)) if season >= self.cur else False
                a = self.f.get(aurl, aname, refresh=refresh, validate=lambda d: "id" in d)
            else:
                a = self.f.load_cache(aname)
            if a and a.get("data"):
                out[aid] = a["data"]
        return out

    def site_roster(self):
        e = self.f.get(f"{SITE}/teams/{TEAM_ID}/roster", "roster_current", refresh=True,
                       validate=lambda d: "athletes" in d)
        return (e or {}).get("data") or {}

    def headshot_ok(self, aid, network=True):
        path = CACHE / "headshots.json"
        if not hasattr(self, "_hs"):
            self._hs = read_json(path, {})
            self._hs_dirty = False
        rec = self._hs.get(aid)
        stale = rec is None or (rec["ok"] is False and
                                parse_dt(rec["checked"]) < now() - dt.timedelta(days=HEADSHOT_RECHECK_DAYS))
        if stale and network:
            ok = self.f.head_ok(HEADSHOT.format(aid))
            if ok is not None:
                rec = {"ok": ok, "checked": iso(now())}
                self._hs[aid] = rec
                self._hs_dirty = True
        return HEADSHOT.format(aid) if rec and rec["ok"] else None

    def save_headshots(self):
        if getattr(self, "_hs_dirty", False):
            write_json(CACHE / "headshots.json", self._hs)

    # -- aggregates
    def load_all_games(self):
        games = {}
        for p in sorted((OUT / "games").glob("*.json")):
            g = self.games_seen.get(p.stem) or read_json(p)
            if g:
                games[g["id"]] = g
        return games

    def build_athletes(self, games, rosters, current_roster, network=True):
        ath = {}

        def rec(aid):
            return ath.setdefault(aid, {"id": aid, "name": None, "short": None, "jerseys": [], "position": None,
                                        "headshot": None, "height": None, "weight": None, "hometown": None,
                                        "classBySeason": {}, "seasons": [], "games": 0, "firstGame": None,
                                        "lastGame": None})

        # box scores
        for g in sorted(games.values(), key=lambda g: g["date"] or ""):
            if g.get("uconn") is None:
                continue
            us = g["teams"][g["uconn"]]
            for p in us["players"]:
                if not p["id"]:
                    continue
                a = rec(p["id"])
                a["name"] = p["name"] or a["name"]
                a["short"] = p["short"] or a["short"]
                if p["jersey"] and p["jersey"] not in a["jerseys"]:
                    a["jerseys"].append(p["jersey"])
                a["position"] = p["pos"] or a["position"]
                if g["season"] not in a["seasons"]:
                    a["seasons"].append(g["season"])
                if p["dnp"] is not True and g["status"] == "final":
                    a["games"] += 1
                    a["firstGame"] = a["firstGame"] or g["id"]
                    a["lastGame"] = g["id"]
        # core rosters (historical)
        for season, roster in sorted(rosters.items()):
            for aid, d in roster.items():
                a = rec(aid)
                a["name"] = a["name"] or d.get("displayName")
                a["short"] = a["short"] or d.get("shortName")
                j = (d.get("jersey") or "").strip()
                if j and j not in a["jerseys"]:
                    a["jerseys"].append(j)
                a["position"] = a["position"] or (d.get("position") or {}).get("abbreviation")
                a["height"] = d.get("displayHeight") or a["height"]
                a["weight"] = d.get("displayWeight") or a["weight"]
                a["hometown"] = (d.get("birthPlace") or {}).get("displayText") or a["hometown"]
                # NOTE: core season-athlete "experience" reflects the player's *latest* class,
                # not the class in that season, so it is deliberately ignored here.
                if season not in a["seasons"]:
                    a["seasons"].append(season)
        # current roster (site API, has class)
        for x in current_roster:
            aid = str(x["id"])
            a = rec(aid)
            a["name"] = x.get("displayName") or a["name"]
            a["short"] = x.get("shortName") or a["short"]
            j = (x.get("jersey") or "").strip()
            if j and j not in a["jerseys"]:
                a["jerseys"].append(j)
            a["position"] = (x.get("position") or {}).get("abbreviation") or a["position"]
            a["height"] = x.get("displayHeight") or a["height"]
            a["weight"] = x.get("displayWeight") or a["weight"]
            a["hometown"] = (x.get("birthPlace") or {}).get("displayText") or a["hometown"]
            exp = (x.get("experience") or {}).get("displayValue")
            if exp:
                a["classBySeason"][str(self.cur)] = exp
            if self.cur not in a["seasons"]:
                a["seasons"].append(self.cur)
        for aid, a in ath.items():
            a["seasons"].sort()
            a["headshot"] = self.headshot_ok(aid, network=network)
        self.save_headshots()
        ath = dict(sorted(ath.items(), key=lambda kv: (kv[1]["seasons"][0] if kv[1]["seasons"] else 0, kv[1]["name"] or "")))
        write_json(OUT / "athletes.json", ath)
        return ath

    def build_teams(self, games):
        teams = {}
        for g in sorted(games.values(), key=lambda g: g["date"] or ""):
            for t in g["teams"]:
                cur = teams.get(t["id"], {})
                teams[t["id"]] = {
                    "id": t["id"],
                    "name": t["name"] or cur.get("name"),
                    "short": t.get("shortName") or cur.get("short"),
                    "location": t["location"] or cur.get("location"),
                    "nickname": t.get("nickname") or cur.get("nickname"),
                    "abbr": t["abbr"] or cur.get("abbr"),
                    "color": t["color"] or cur.get("color"),
                    "altColor": t["altColor"] or cur.get("altColor"),
                    "logo": t["logo"] or cur.get("logo"),
                    "games": cur.get("games", 0) + (1 if t["id"] != TEAM_ID else 0),
                }
        write_json(OUT / "teams.json", dict(sorted(teams.items(), key=lambda kv: kv[1]["name"] or "")))
        return teams

    def build_current(self, games, roster_data, athletes, network=True):
        team_e = self.f.get(f"{SITE}/teams/{TEAM_ID}", "team_current", refresh=network,
                            validate=lambda d: "team" in d) if network else self.f.load_cache("team_current")
        rank_e = self.f.get(f"{SITE}/rankings", "rankings_current", refresh=network,
                            validate=lambda d: "rankings" in d) if network else self.f.load_cache("rankings_current")
        team = ((team_e or {}).get("data") or {}).get("team") or {}
        rk = (rank_e or {}).get("data") or {}

        polls = {}
        for r in rk.get("rankings") or []:
            me = None
            for x in r.get("ranks") or []:
                if str(x["team"].get("id")) == TEAM_ID:
                    me = {"rank": x.get("current"), "previous": x.get("previous"), "points": x.get("points"),
                          "firstPlaceVotes": x.get("firstPlaceVotes"), "trend": x.get("trend"),
                          "record": x.get("recordSummary")}
            if me is None:
                for x in r.get("others") or []:
                    if str(x["team"].get("id")) == TEAM_ID:
                        me = {"rank": None, "receivingVotes": True, "points": x.get("points"),
                              "record": x.get("recordSummary")}
            polls[r.get("type") or r.get("name")] = {
                "name": r.get("name"), "headline": r.get("headline"), "date": r.get("date"),
                "season": (r.get("season") or {}).get("year"), "uconn": me,
                "top25": [[x.get("current"), str(x["team"].get("id")), x["team"].get("abbreviation"),
                           x["team"].get("location") or x["team"].get("nickname"), x.get("recordSummary"),
                           x.get("points"), x.get("firstPlaceVotes")] for x in r.get("ranks") or []],
            }

        # next game: first non-final game by date among processed games
        upcoming = sorted([g for g in games.values() if g["status"] in ("scheduled", "in")],
                          key=lambda g: g["date"] or "")
        nxt = None
        ne = (team.get("nextEvent") or [None])[0]
        nid = str(ne["id"]) if ne else (upcoming[0]["id"] if upcoming else None)
        g = games.get(nid) if nid else None
        if g is None and upcoming:
            g = upcoming[0]
        if g:
            ui = g["uconn"]
            opp = g["teams"][1 - ui] if ui is not None else None
            nxt = {"id": g["id"], "date": g["date"], "timeTBD": g["timeTBD"], "status": g["status"],
                   "homeAway": g["teams"][ui]["homeAway"] if ui is not None else None,
                   "neutral": g["neutral"], "note": g["note"],
                   "opponent": opp and {k: opp.get(k) for k in ("id", "name", "abbr", "logo", "rank", "color")},
                   "venue": g["venue"], "tv": g["broadcasts"], "odds": g["odds"]}

        cur_games = [g for g in games.values() if g["season"] == self.cur and g["status"] == "final" and g["uconn"] is not None]
        w = sum(1 for g in cur_games if g["teams"][g["uconn"]]["winner"])
        rec_items = (team.get("record") or {}).get("items") or []
        roster = []
        for x in roster_data.get("athletes") or []:
            aid = str(x["id"])
            roster.append({
                "id": aid, "name": x.get("displayName"), "jersey": x.get("jersey"),
                "pos": (x.get("position") or {}).get("abbreviation"),
                "posName": (x.get("position") or {}).get("displayName"),
                "class": (x.get("experience") or {}).get("displayValue"),
                "height": x.get("displayHeight"), "weight": x.get("displayWeight"),
                "hometown": (x.get("birthPlace") or {}).get("displayText"),
                "headshot": (athletes.get(aid) or {}).get("headshot"),
                "status": (x.get("status") or {}).get("type"),
                "injuries": [i.get("status") or i.get("type") for i in x.get("injuries") or []] or None,
                "priorSeasons": [s for s in (athletes.get(aid) or {}).get("seasons", []) if s < self.cur],
            })
        roster.sort(key=lambda r: (ival(r["jersey"]) if ival(r["jersey"]) is not None else 999))
        coach = [{"name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
                  "experience": c.get("experience")} for c in roster_data.get("coach") or []]
        last = read_json(OUT / "schedules" / f"{self.cur - 1}.json", {})
        doc = {
            "season": self.cur,
            "label": f"{self.cur - 1}-{str(self.cur)[2:]}",
            "team": {"id": TEAM_ID, "name": team.get("displayName"), "abbr": team.get("abbreviation"),
                     "color": team.get("color"), "altColor": team.get("alternateColor"),
                     "logo": best_logo(team), "standing": team.get("standingSummary")},
            "record": {"overall": (rec_items[0].get("summary") if rec_items else None) or f"{w}-{len(cur_games) - w}",
                       "fromGames": f"{w}-{len(cur_games) - w}"},
            "lastSeason": {"season": self.cur - 1, "record": f"{last.get('wins')}-{last.get('losses')}"} if last else None,
            "rank": team.get("rank"),
            "polls": polls,
            "next": nxt,
            "coach": coach,
            "roster": roster,
        }
        write_json(OUT / "current.json", doc)
        return doc


def coverage(games):
    """per-season coverage of UI-relevant features among final games"""
    by = {}
    for g in games.values():
        if g["status"] != "final":
            continue
        s = by.setdefault(g["season"], {"n": 0, "box": 0, "plays": 0, "wp": 0, "coords": 0, "videos": 0, "article": 0})
        s["n"] += 1
        us = g["teams"][g["uconn"]] if g.get("uconn") is not None else None
        s["box"] += bool(us and us.get("hasPlayerStats"))
        s["plays"] += bool(g["plays"])
        s["wp"] += bool(g["wp"])
        s["coords"] += sum(1 for p in g["plays"] if p[8] and p[9] is not None) >= 10
        s["videos"] += bool(g["videos"])
        s["article"] += bool(g["article"])
    return by


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    m = ap.add_mutually_exclusive_group(required=True)
    m.add_argument("--all", action="store_true", help="full backfill of all seasons")
    m.add_argument("--update", action="store_true", help="current season + non-final games only")
    m.add_argument("--rebuild", action="store_true", help="re-normalize all outputs from cache (no game downloads)")
    ap.add_argument("--seasons", help="comma list of seasons (with --all)")
    ap.add_argument("--force", help="comma list of event ids to force re-download")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    P = Pipeline(args)
    cur = P.cur
    force_ids = set((args.force or "").split(",")) - {""}
    print(f"ESPN fetch  mode={'all' if args.all else 'update' if args.update else 'rebuild'}  current season={cur}",
          flush=True)

    all_seasons = list(range(FIRST_SEASON, cur + 1))
    if args.all:
        seasons = [int(s) for s in args.seasons.split(",")] if args.seasons else all_seasons
        P.run_seasons(seasons, network=True, force_ids=force_ids)
    elif args.rebuild:
        P.run_seasons(all_seasons, network=False)
    else:
        # current season (network) + any non-final game elsewhere
        P.run_seasons([cur], network=True, force_ids=force_ids)
        stale_seasons = set()
        for p in (OUT / "games").glob("*.json"):
            g = read_json(p)
            if g and g["season"] != cur and g["status"] in ("scheduled", "in"):
                stale_seasons.add(g["season"])
        if stale_seasons:
            print(f"  re-checking non-final games in seasons {sorted(stale_seasons)}")
            P.run_seasons(sorted(stale_seasons), network=True, force_ids=force_ids)

    # rosters: network for processed seasons, cache for the rest
    net_seasons = set(all_seasons if args.all and not args.seasons else
                      ([int(s) for s in args.seasons.split(",")] if args.seasons else []) + [cur])
    if args.rebuild:
        net_seasons = set()
    rosters = {}
    for s in all_seasons:
        rosters[s] = P.core_roster(s, network=s in net_seasons)
    roster_data = P.site_roster() if not args.rebuild else ((P.f.load_cache("roster_current") or {}).get("data") or {})

    games = P.load_all_games()
    athletes = P.build_athletes(games, rosters, roster_data.get("athletes") or [], network=not args.rebuild)
    teams = P.build_teams(games)
    current = P.build_current(games, roster_data, athletes, network=not args.rebuild)

    # summary
    st = P.f.stats
    print()
    print(f"done in {time.time() - P.t0:.0f}s  requests: net={st['net']} cache={st['cache']} head={st['head']} errors={st['errors']}")
    print(f"games on disk={len(games)}  games changed={P.changed['games']}  schedules changed={P.changed['schedules']}")
    print(f"athletes={len(athletes)} (headshots {sum(1 for a in athletes.values() if a['headshot'])})  teams={len(teams)}")
    nx = current.get("next")
    if nx:
        print(f"next game: {nx['date']} {nx['homeAway']} vs {nx['opponent'] and nx['opponent']['name']}  tv={nx['tv']}")
    for poll in current["polls"].values():
        print(f"poll {poll['name']} ({poll['date']}): UConn {poll['uconn']}")
    if P.f.failures:
        print(f"FAILURES ({len(P.f.failures)}):")
        for x in P.f.failures[:50]:
            print("  ", x)
    return 1 if P.f.failures and not games else 0


if __name__ == "__main__":
    sys.exit(main())
