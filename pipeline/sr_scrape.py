#!/usr/bin/env python3
"""Resumable Sports-Reference (CBB) scraper for UConn men's basketball, 1987-2026.

Phases (in order):  seasons -> boxscores -> players -> school -> adv -> [gamelogs]
Then `build` parses everything from cache into pipeline/out/sr/.

All raw HTML is cached under pipeline/cache.nosync/sr/ and never re-downloaded
unless --force is given (which only applies to the --years selected, their
rosters' player pages, and the school index/coaches pages).

Examples
  python3 pipeline/sr_scrape.py                       # everything (resumable)
  python3 pipeline/sr_scrape.py --years 2027 --force  # refresh one season
  python3 pipeline/sr_scrape.py --build-only          # re-parse cache -> JSON
  python3 pipeline/sr_scrape.py --report              # validation table
  python3 pipeline/sr_scrape.py --gamelogs            # also 2011+ player game logs
"""
import argparse, json, os, sys, time, re, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_fetch as F
import sr_parse as P

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "sr")
SCHOOL = "connecticut"
FIRST, LAST = 1987, 2026
LOGF = os.path.join(HERE, "out", "sr", "scrape.log")


def log(*a):
    msg = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(msg, flush=True)
    os.makedirs(os.path.dirname(LOGF), exist_ok=True)
    with open(LOGF, "a") as f:
        f.write(msg + "\n")


def season_url(y):
    return f"/cbb/schools/{SCHOOL}/men/{y}.html"


def sched_url(y):
    return f"/cbb/schools/{SCHOOL}/men/{y}-schedule.html"


def box_url(slug):
    return f"/cbb/boxscores/{slug}.html"


def player_url(pid):
    return f"/cbb/players/{pid}.html"


def adv_url(y):
    return f"/cbb/seasons/men/{y}-advanced-school-stats.html"


def gamelog_url(pid, y):
    return f"/cbb/players/{pid}/gamelog/{y}"


def get(url, force=False):
    """fetch with logging; returns html or None on 404."""
    try:
        return F.fetch(url, force=force, log=log)
    except F.NotFound:
        log(f"  404 {url}")
        return None


def cached(url):
    try:
        return F.fetch(url, force=False, log=log) if F.is_cached(url) else None
    except F.NotFound:
        return None


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


# ---------------------------------------------------------------- fetch phases

def phase_seasons(years, force):
    log(f"== seasons: {len(years)} years")
    for y in years:
        get(season_url(y), force)
        get(sched_url(y), force)


def box_slugs_for(y):
    h = cached(sched_url(y))
    slugs = []
    if h:
        for g in P.parse_schedule(h)["schedule"]:
            if g.get("box_slug"):
                slugs.append(g["box_slug"])
    d = parsed_season(y)
    if d:  # meta NCAA links (sometimes present when schedule lacks)
        meta = d["meta"]
        for ps in meta.get("postseason", []):
            for g in ps.get("games", []):
                if g.get("box_slug") and g["box_slug"] not in slugs:
                    slugs.append(g["box_slug"])
    return slugs


def phase_boxscores(years):
    todo = [(y, s) for y in years for s in box_slugs_for(y)]
    need = [t for t in todo if not F.is_cached(box_url(t[1]))]
    log(f"== boxscores: {len(todo)} linked, {len(need)} to download")
    for i, (y, s) in enumerate(need):
        get(box_url(s))
        if i % 25 == 0:
            log(f"  box progress {i}/{len(need)}")


_PARSED = {}


def parsed_season(y):
    """parse_season memoized on the cache file's mtime (so --force refreshes it)."""
    cp = F.cache_path(F.BASE + season_url(y))
    if not os.path.exists(cp):
        return None
    key = (y, os.path.getmtime(cp))
    if key not in _PARSED:
        _PARSED[key] = P.parse_season(cached(season_url(y)), y)
    return _PARSED[key]


def roster_ids(y):
    ids = []
    d = parsed_season(y)
    if not d:
        return ids
    for r in d["roster"]:
        if r.get("sr_id") and r["sr_id"] not in ids:
            ids.append(r["sr_id"])
    for r in d["stats"].get("per_game", []) or []:
        if r.get("sr_id") and r["sr_id"] not in ids:
            ids.append(r["sr_id"])
    return ids


def all_player_ids(years):
    seen = {}
    for y in years:
        for pid in roster_ids(y):
            seen.setdefault(pid, []).append(y)
    return seen


def phase_players(years, force):
    ids = all_player_ids(years)
    need = [p for p in ids if force or not F.is_cached(player_url(p))]
    log(f"== players: {len(ids)} unique, {len(need)} to download")
    for i, p in enumerate(need):
        get(player_url(p), force)
        if i % 25 == 0:
            log(f"  player progress {i}/{len(need)}")


def phase_school(force):
    log("== school index + coaches")
    get(f"/cbb/schools/{SCHOOL}/men/", force)
    get(f"/cbb/schools/{SCHOOL}/men/coaches.html", force)


def phase_adv(years, force):
    log(f"== advanced school stats (pace etc) {len(years)} years")
    for y in years:
        get(adv_url(y), force)


def phase_gamelogs(years, force):
    pairs = []
    for y in years:
        if y < 2011:
            continue
        for pid in roster_ids(y):
            pairs.append((pid, y))
    need = [t for t in pairs if force or not F.is_cached(gamelog_url(*t))]
    log(f"== gamelogs: {len(pairs)} player-seasons, {len(need)} to download")
    for i, (pid, y) in enumerate(need):
        get(gamelog_url(pid, y), force)
        if i % 25 == 0:
            log(f"  gamelog progress {i}/{len(need)}")


# ---------------------------------------------------------------- build

def build_season(y, school_index):
    d = parsed_season(y)
    if not d:
        return None
    d = json.loads(json.dumps(d))  # don't mutate memoized copy
    hs = cached(sched_url(y))
    sc = P.parse_schedule(hs) if hs else {"schedule": [], "polls": []}
    # opponent seeds from meta postseason text
    seeds = {}
    for ps in d["meta"].get("postseason", []):
        for g in ps.get("games", []):
            if g.get("box_slug"):
                seeds[g["box_slug"]] = g
            seeds[(ps["label"], g.get("opp_slug"), g.get("pts"), g.get("opp_pts"))] = g
    for g in sc["schedule"]:
        m = seeds.get(g.get("box_slug"))
        if m is None:
            for ps in d["meta"].get("postseason", []):
                m = seeds.get((ps["label"], g.get("opp_slug"), g.get("pts"), g.get("opp_pts"))) or m
        if m and g.get("game_type") not in ("REG", "CTOURN"):
            g["opp_seed"] = m.get("opp_seed")
            g["round"] = m.get("round")
        else:
            g.setdefault("opp_seed", None)
        g["box_cached"] = bool(g.get("box_slug") and F.is_cached(box_url(g["box_slug"]))
                               and os.path.exists(F.cache_path(F.BASE + box_url(g["box_slug"]))))
    d["schedule"] = sc["schedule"]
    d["polls"] = [p for p in sc["polls"] if p["school"] in ("UConn", "Connecticut")] or sc["polls"]
    ranks = [p["rank"] for p in d["polls"] if isinstance(p["rank"], int)]
    meta = d["meta"]
    meta["ap_pre"] = next((p["rank"] for p in d["polls"] if p["week"] == "Pre"), None)
    meta["ap_high"] = min(ranks) if ranks else None
    meta["ap_final"] = next((p["rank"] for p in d["polls"] if p["week"] == "Final"), meta.get("ap_final_meta"))
    si = school_index.get(d["label"]) if school_index else None
    if si:
        meta["school_index"] = si
        meta["ap_pre"] = si.get("rank_pre") if si.get("rank_pre") is not None else meta["ap_pre"]
        meta["ap_high"] = si.get("rank_min") if si.get("rank_min") is not None else meta["ap_high"]
        meta["ap_final"] = si.get("rank_final") if si.get("rank_final") is not None else meta["ap_final"]
        meta["ncaa_seed"] = si.get("seed")
        meta["postseason_result"] = si.get("round_max")
    ha = cached(adv_url(y))
    if ha:
        adv = P.parse_school_adv(ha, SCHOOL)
        meta["school_advanced"] = adv
        for tid, row in adv.items():
            if row.get("pace") is not None and "pace" not in meta:
                meta["pace"] = row.get("pace")
            if row.get("off_rtg") is not None:
                meta.setdefault("off_rtg_adv", row.get("off_rtg"))
    meta.setdefault("pace", None)
    ncaa = next((p for p in meta.get("postseason", []) if p["label"].startswith("NCAA")), None)
    meta["ncaa_result_text"] = ncaa["text"] if ncaa else None
    return d


def load_school_index():
    h = cached(f"/cbb/schools/{SCHOOL}/men/")
    if not h:
        return None, {}
    tabs = P.parse_generic_tables(h)
    t = tabs.get(SCHOOL) or next(iter(tabs.values()), None)
    rows = t["rows"] if t else []
    by_label = {r.get("season"): r for r in rows if r.get("season")}
    return rows, by_label


def build(years, gamelogs=False):
    log("== build")
    rows, si = load_school_index()
    if rows is not None:
        hc = cached(f"/cbb/schools/{SCHOOL}/men/coaches.html")
        coaches = P.parse_generic_tables(hc).get("coaches") if hc else None
        write_json(os.path.join(OUT, "school_index.json"),
                   {"url": F.BASE + f"/cbb/schools/{SCHOOL}/men/", "seasons": rows,
                    "coaches": coaches["rows"] if coaches else None})
    n_box = n_pl = n_seas = 0
    for y in years:
        d = build_season(y, si)
        if d is None:
            continue
        n_seas += 1
        write_json(os.path.join(OUT, "seasons", f"{y}.json"), d)
        for s in box_slugs_for(y):
            h = cached(box_url(s))
            if not h:
                continue
            try:
                b = P.parse_boxscore(h, s)
                b["season"] = y
                write_json(os.path.join(OUT, "boxscores", f"{s}.json"), b)
                n_box += 1
            except Exception:
                log(f"  PARSE ERROR box {s}: {traceback.format_exc(limit=2)}")
    known = [y for y in range(FIRST, max(years + [LAST]) + 1) if F.is_cached(season_url(y))]
    ids = all_player_ids(sorted(set(known) | set(years)))
    for pid, yrs in ids.items():
        if not set(yrs) & set(years):
            continue
        h = cached(player_url(pid))
        if not h:
            continue
        try:
            p = P.parse_player(h, pid)
            p["uconn_seasons"] = yrs
            if True:  # include any cached game logs (fetched with --gamelogs)
                gl = {}
                for y in yrs:
                    if y >= 2011:
                        hg = cached(gamelog_url(pid, y))
                        if hg:
                            gl[y] = P.parse_generic_tables(hg)
                if gl:
                    p["gamelogs"] = gl
            write_json(os.path.join(OUT, "players", f"{pid}.json"), p)
            n_pl += 1
        except Exception:
            log(f"  PARSE ERROR player {pid}: {traceback.format_exc(limit=2)}")
    log(f"  built {n_seas} seasons, {n_box} boxscores, {n_pl} players")


# ---------------------------------------------------------------- report

def report(years):
    print(f"{'yr':4} {'label':7} {'W-L':6} {'conf':6} {'coach':28} {'sched':>5} {'rost':>4} {'stat':>4} {'box':>4} {'boxOK':>5} {'AP p/h/f':>9} pace")
    for y in years:
        p = os.path.join(OUT, "seasons", f"{y}.json")
        if not os.path.exists(p):
            print(y, "MISSING")
            continue
        d = json.load(open(p))
        m = d["meta"]
        links = [g for g in d["schedule"] if g.get("box_slug")]
        ok = sum(os.path.exists(os.path.join(OUT, "boxscores", g["box_slug"] + ".json")) for g in links)
        coach = ", ".join(c["name"] for c in m.get("coaches", []))[:28]
        ap = f"{m.get('ap_pre') or '-'}/{m.get('ap_high') or '-'}/{m.get('ap_final') or '-'}"
        sw = sum(1 for g in d["schedule"] if g.get("game_result") == "W")
        sl = sum(1 for g in d["schedule"] if g.get("game_result") == "L")
        flag = "" if (sw, sl) == (m.get("wins"), m.get("losses")) else f"  !! schedule {sw}-{sl}"
        print(f"{y:<4} {d['label']:7} {str(m.get('wins'))+'-'+str(m.get('losses')):6} "
              f"{str(m.get('conf_wins'))+'-'+str(m.get('conf_losses')):6} {coach:28} {len(d['schedule']):>5} "
              f"{len(d['roster']):>4} {len(d['stats'].get('per_game') or []):>4} {len(links):>4} {ok:>5} {ap:>9} {m.get('pace')}{flag}")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default=f"{FIRST}-{LAST}", help="e.g. 2027 or 1987-2026 or 1999,2004")
    ap.add_argument("--force", action="store_true", help="re-download season/schedule/players/school pages for --years")
    ap.add_argument("--phases", default="seasons,boxscores,players,school,adv",
                    help="comma list of seasons,boxscores,players,school,adv,gamelogs")
    ap.add_argument("--gamelogs", action="store_true", help="also fetch 2011+ player game logs (slow)")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    years = []
    for part in a.years.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            years += list(range(int(lo), int(hi) + 1))
        else:
            years.append(int(part))
    all_years = sorted(set(list(range(FIRST, LAST + 1)) + years))
    if a.report:
        report(years)
        return
    phases = [p.strip() for p in a.phases.split(",") if p.strip()]
    if a.gamelogs and "gamelogs" not in phases:
        phases.append("gamelogs")
    t0 = time.time()
    try:
        if not a.build_only:
            if "seasons" in phases:
                phase_seasons(years, a.force)
                build(years)
            if "boxscores" in phases:
                phase_boxscores(years)
                build(years)
            if "players" in phases:
                phase_players(years, a.force)
            if "school" in phases:
                phase_school(a.force)
            if "adv" in phases:
                phase_adv(years, a.force)
            if "gamelogs" in phases:
                phase_gamelogs(years, a.force)
    except F.RateLimited as e:
        log(f"!! RATE LIMITED (429 x3) at {e}; stopping. Re-run later to resume.")
        build(all_years if not a.force else years, gamelogs=a.gamelogs)
        sys.exit(2)
    # build: if refreshing a subset, still rebuild those years (and players on them)
    build(years if a.force or a.years != f"{FIRST}-{LAST}" else all_years, gamelogs=a.gamelogs)
    log(f"done in {time.time()-t0:.0f}s; net={F.STATS['net']} cache={F.STATS['cache']} 404={F.STATS['404']}")


if __name__ == "__main__":
    main()
