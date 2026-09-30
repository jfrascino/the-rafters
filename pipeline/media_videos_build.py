"""Assemble out/media/videos.json from pick files with strict sanity filters + manual overrides."""
import json, os, re, sys
from media_common import CACHE, save
from media_video_search import opp_terms, UCONN
from media_yt import oembed

picks = []
for f in ["video_picks.json", "video_picks2.json"]:
    p = os.path.join(CACHE, f)
    if os.path.exists(p): picks += json.load(open(p))
rosters = json.load(open(os.path.join(CACHE, "rosters.json")))
players_raw = json.load(open(os.path.join(CACHE, "players_raw.json")))
OVR = json.load(open(os.path.join(os.path.dirname(__file__), "media_video_overrides.json"))) if os.path.exists(os.path.join(os.path.dirname(__file__), "media_video_overrides.json")) else {"reject": [], "verify": {}, "add": [], "fix": {}}

STRICT_BAD = ["free pick", "pick:", "picks", "sportsbook", "prediction", "🔴", "live |", "live stream", "simulat", "cyberpuck",
              "women", "wbb", "sue bird", "taurasi", "bueckers", "lobo", "geno", "auriemma", "2k", "reaction", "betting", "odds",
              "fortnite", "nba 2k", "college hoops", "gameplay", "ps5", "xbox", "vhs tape for sale"]
WOMEN_DESC = ["women's basketball", "lady vols", "lady huskies", "uconn women"]

# notable player names for tagging
NAMES = {}
for t, p in players_raw.items():
    if p.get("is_player") and p.get("uconn_years") and p["uconn_years"][1] and p["uconn_years"][1] >= 1987:
        nm = re.sub(r"\s*\(.*\)", "", t)
        NAMES[nm] = p["uconn_years"]
for y, names in rosters.items():
    for n in names:
        n2 = re.sub(r"\(W\)", "", n).strip()
        NAMES.setdefault(n2, [int(y) - 1, int(y)])
NICK = {"Rip Hamilton": "Richard Hamilton", "Kemba": "Kemba Walker", "Shabazz": "Shabazz Napier", "Okafor": "Emeka Okafor",
        "El-Amin": "Khalid El-Amin", "Sanogo": "Adama Sanogo", "Clingan": "Donovan Clingan", "Karaban": "Alex Karaban",
        "Thabeet": "Hasheem Thabeet", "Tate George": "Tate George", "Ray Allen": "Ray Allen", "Boatright": "Ryan Boatright",
        "Mullins": "Braylon Mullins", "Castle": None, "Hawkins": "Jordan Hawkins", "Newton": "Tristen Newton", "Bouknight": "James Bouknight",
        "McNeeley": "Liam McNeeley", "Drummond": "Andre Drummond", "Caron Butler": "Caron Butler", "Rudy Gay": "Rudy Gay",
        "Ben Gordon": "Ben Gordon", "Tarris Reed": "Tarris Reed Jr.", "Demary": "Silas Demary Jr."}

def tag_players(text, season):
    found = []
    tl = text.lower()
    for n, yrs in NAMES.items():
        if len(n) < 6: continue
        if n.lower() in tl and (not season or (yrs[0] - 1 <= season <= yrs[1] + 1)):
            found.append(n)
    for k, v in NICK.items():
        if v and k.lower() in tl and v not in found:
            yrs = NAMES.get(v)
            if not season or not yrs or (yrs[0] - 1 <= season <= yrs[1] + 1):
                found.append(v)
    return sorted(set(found))

def fmt_score(t):
    if t.get("uconn") is None: return ""
    s = f"{t['uconn']}–{t['opp_score']}"
    return s + (f" ({t['ot']})" if t.get("ot") else "")

def describe(t, kind, channel):
    k = {"full_game": "Full-game broadcast", "highlights": "Highlights", "moment": "Clip", "documentary": "Feature",
         "interview": "Press conference/interview"}.get(kind, "Video")
    if t.get("opponent"):
        verb = "win over" if t.get("result") == "W" else "loss to"
        where = f" at {t['site'].split(',')[0]}" if t.get("site") else ""
        rnd = t.get("round") or ""
        yr = (t.get("date") or "")[:4]
        return f"{k} of UConn's {fmt_score(t)} {verb} {t['opponent']} ({yr} {rnd}){where}; uploaded by {channel}."
    return f"{k}: {t.get('round')}; uploaded by {channel}."

videos = []; seen = set(); rejected = []; flagged = []
for e in picks:
    t = e["target"]
    for pk in e["picks"]:
        c = pk["cand"]; oe = pk["oembed"]
        vid = c["id"]
        title = oe["title"] or c["title"]; ch = oe["author_name"] or c["channel"]
        tl = " " + title.lower() + " "
        desc = ((c.get("det") or {}).get("description") or "").lower()
        why = []
        if vid in OVR["reject"]: rejected.append((vid, title, "manual")); continue
        if any(b in tl for b in STRICT_BAD): rejected.append((vid, title, "bad-term")); continue
        if any(w in desc[:400] for w in WOMEN_DESC) and "men's" not in tl: rejected.append((vid, title, "women-desc")); continue
        if t.get("opponent"):
            ot = opp_terms(t["opponent"])
            if not any(o in tl for o in ot):
                if any(o in desc for o in ot): why.append("opponent only in description")
                else: rejected.append((vid, title, "no-opponent")); continue
            if not any(u in tl for u in UCONN):
                if any(u in desc for u in UCONN): why.append("UConn only in description")
                else: rejected.append((vid, title, "no-uconn")); continue
            yrs = {str(t["season"]), (t.get("date") or "")[:4]} - {""}
            other = set(re.findall(r"\b(19[89]\d|20[0-2]\d)\b", title)) - yrs
            if other and not (yrs & set(re.findall(r"\b(19[89]\d|20[0-2]\d)\b", title))):
                rejected.append((vid, title, "other-year")); continue
            if not (yrs & set(re.findall(r"\b(19[89]\d|20[0-2]\d)\b", title))) and "'" + str(t["season"])[2:] not in title:
                if "contemporaneous" in c.get("why2", []): why.append("no year in title; upload date matches game")
                elif "year-in-desc" in c.get("why2", []) or any(y in desc for y in yrs): why.append("year only in description")
                else: why.append("no year in title/description — matched by opponent+round only")
        else:
            must = t.get("must_any") or []
            if must and not any(m in tl for m in must) and not any(m in desc for m in must):
                rejected.append((vid, title, "no-must")); continue
            if not any(u in tl for u in UCONN) and not any(u in desc for u in UCONN):
                why.append("UConn not named in title/description")
        if vid in seen: continue
        seen.add(vid)
        kind = c.get("kind") or "highlights"
        if t.get("target_kind") in ("documentary", "interview") and kind not in ("full_game",):
            kind = t["target_kind"]
        det = c.get("det") or {}
        v = {"id": vid, "url": f"https://www.youtube.com/watch?v={vid}", "title": title, "channel": ch, "kind": kind,
             "season": t["season"] or None, "date": t.get("date") or None, "opponent": t.get("opponent"), "round": t.get("round"),
             "result": t.get("result"), "score": fmt_score(t) or None,
             "players": sorted(set((t.get("players") or []) + tag_players(title + " " + (det.get("description") or "")[:600], t["season"]))),
             "description": describe(t, kind, ch), "length_sec": det.get("length") or c.get("secs"),
             "published": det.get("publish_date") or None, "embeddable": det.get("embeddable"),
             "verified_oembed": True, "match_score": round(c.get("score2", 0), 1), "game_source": t.get("wiki")}
        if why:
            v["verify"] = True; v["verify_reason"] = "; ".join(why)
        if vid in OVR["verify"]:
            v["verify"] = True; v["verify_reason"] = OVR["verify"][vid]
        if vid in OVR.get("fix", {}): v.update(OVR["fix"][vid])
        videos.append(v)

# manual additions (already oEmbed-verified below)
for a in OVR.get("add", []):
    if a["id"] in seen: continue
    oe = oembed(a["id"])
    if not oe: print("ADD FAILED oEmbed", a["id"]); continue
    a = dict(a); a.update({"url": f"https://www.youtube.com/watch?v={a['id']}", "title": oe["title"], "channel": oe["author_name"], "verified_oembed": True})
    videos.append(a); seen.add(a["id"])

videos.sort(key=lambda v: ((v["season"] or 0), v["date"] or "", v["kind"]))
save("videos.json", {"generated": "2026-09-30", "count": len(videos),
                     "note": "Every id verified via YouTube oEmbed (HTTP 200). Items with verify:true matched on opponent/round but lack an explicit year or team name in the title — spot-check before featuring.",
                     "videos": videos})
json.dump(rejected, open(os.path.join(CACHE, "videos_rejected.json"), "w"), indent=1, ensure_ascii=False)
print("videos", len(videos), "rejected", len(rejected), "verify", sum(1 for v in videos if v.get("verify")))
if "-v" in sys.argv:
    for v in videos:
        print(f"{v['season']}|{(v['round'] or '')[:28]:28}|{(v['opponent'] or '')[:14]:14}|{v['kind'][:5]}|{v['id']}|{v['channel'][:18]:18}|{v['title'][:80]}{' [VERIFY: '+v['verify_reason']+']' if v.get('verify') else ''}")
