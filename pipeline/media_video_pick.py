"""Enrich top candidates with watch-page details, rescore with date sanity checks, pick full_game + highlights per target,
verify via oEmbed. Output cache.nosync/media/video_picks_<name>.json"""
import json, os, re, sys, datetime
from media_common import CACHE
from media_yt import details, oembed
from media_video_search import opp_terms, UCONN, kind_of

def d(s):
    try: return datetime.date.fromisoformat(s[:10])
    except Exception: return None

def rescore(c, t, det):
    s = c["score"]; why = list(c["why"])
    desc = (det.get("description") or "").lower()
    title = (det.get("title") or c["title"]).lower()
    gd = d(t.get("date", "")) if t.get("date") else None
    pd = d(det.get("publish_date") or det.get("upload_date") or "")
    yrs = {str(t["season"]), t.get("date", "")[:4]} - {""}
    if "year" not in why and "other-year" not in why:
        if any(y in desc for y in yrs): s += 3; why.append("year-in-desc")
    other_years = set(re.findall(r"\b(19[89]\d|20[0-2]\d)\b", title)) - yrs
    if gd and pd:
        delta = (pd - gd).days
        if delta < -1: s -= 30; why.append("published-before-game")
        elif delta <= 21: s += 5; why.append("contemporaneous")
        elif "year" not in why and "year-in-desc" not in why:
            s -= 4; why.append("late-upload-no-year")
    if t.get("opponent") and "opp" not in why:
        if any(o in desc for o in opp_terms(t["opponent"])): s += 1.5; why.append("opp-in-desc")
    if det.get("status") not in (None, "OK"): s -= 20; why.append("unplayable:" + str(det.get("status")))
    if "women" in desc[:300] and "men's" not in title: s -= 6; why.append("women-desc")
    return s, why

def pick(entries, min_score=8, per_kind=("full_game", "highlights", "moment"), max_total=2):
    out = []
    for e in entries:
        t = e["target"]
        cands = [c for c in e["cands"] if c["score"] >= 2][:6]
        scored = []
        for c in cands:
            det = details(c["id"]) or {}
            s, why = rescore(c, t, det)
            L = det.get("length") or c["secs"]
            k = kind_of({"title": det.get("title") or c["title"]}, L)
            scored.append(dict(c, score2=s, why2=why, det=det, kind=k))
        scored.sort(key=lambda c: -c["score2"])
        chosen = []
        if t.get("target_kind") in ("moment", "documentary", "interview", "highlights"):
            for c in scored:
                if c["score2"] >= min_score and len(chosen) < (2 if t.get("target_kind") == "documentary" else 1):
                    chosen.append(c)
        for k in (per_kind if not chosen else ()):
            best = next((c for c in scored if c["kind"] == k and c["score2"] >= min_score and c not in chosen), None)
            if best and len(chosen) < max_total: chosen.append(best)
        if not chosen:
            best = next((c for c in scored if c["score2"] >= min_score), None)
            if best: chosen.append(best)
        verified = []
        for c in chosen:
            oe = oembed(c["id"])
            if oe:
                verified.append({"cand": c, "oembed": {"title": oe.get("title"), "author_name": oe.get("author_name")}})
        out.append({"target": t, "picks": verified, "rejected_top": [
            {"id": c["id"], "title": c["title"], "channel": c["channel"], "score2": c["score2"], "why2": c["why2"]} for c in scored[:4] if c not in chosen]})
        print(t["season"], t.get("round"), t.get("opponent"), "->", [(round(v["cand"]["score2"], 1), v["cand"]["kind"], v["oembed"]["author_name"], v["oembed"]["title"][:60]) for v in verified], flush=True)
    return out

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "video_candidates.json"
    entries = json.load(open(os.path.join(CACHE, name)))
    res = pick(entries)
    json.dump(res, open(os.path.join(CACHE, name.replace("candidates", "picks")), "w"), indent=1, ensure_ascii=False)
