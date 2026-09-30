"""YouTube search (HTML ytInitialData scrape) + oEmbed verification. stdlib only."""
import json, re, urllib.parse
from media_common import fetch

def _walk(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                yield v
            else:
                yield from _walk(v, key)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v, key)

def _txt(x):
    if not x: return ""
    if "simpleText" in x: return x["simpleText"]
    return "".join(r.get("text", "") for r in x.get("runs", []))

def search(q, limit=20):
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": q, "hl": "en", "gl": "US"})
    html = fetch(url, browser=True, ext="html")
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not m:
        m = re.search(r'ytInitialData"\]\s*=\s*(\{.*?\});', html, re.S)
    if not m: return []
    data = json.loads(m.group(1))
    out = []
    for vr in _walk(data, "videoRenderer"):
        vid = vr.get("videoId")
        if not vid: continue
        ch = _txt(vr.get("ownerText")) or _txt(vr.get("longBylineText"))
        out.append({"id": vid, "title": _txt(vr.get("title")), "channel": ch,
                    "length": _txt(vr.get("lengthText")),
                    "views": _txt(vr.get("viewCountText")),
                    "published": _txt(vr.get("publishedTimeText")),
                    "desc": " ".join(_txt(s.get("snippetText")) for s in vr.get("detailedMetadataSnippets", []) if s)})
        if len(out) >= limit: break
    return out

def length_sec(s):
    if not s: return 0
    p = [int(x) for x in s.split(":") if x.isdigit()]
    t = 0
    for x in p: t = t * 60 + x
    return t

def oembed(vid):
    url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"})
    txt = fetch(url, ext="json", allow_404=True)
    if not txt: return None
    try: return json.loads(txt)
    except Exception: return None

if __name__ == "__main__":
    import sys
    for r in search(" ".join(sys.argv[1:])):
        print(r["id"], "|", r["length"], "|", r["channel"], "|", r["title"])

def details(vid):
    """Fetch watch page; return description, publish date, length, playability/embeddable."""
    html = fetch(f"https://www.youtube.com/watch?v={vid}&hl=en&gl=US", browser=True, ext="html")
    m = re.search(r"var ytInitialPlayerResponse = (\{.*?\});(?:var |</script>)", html, re.S)
    if not m:
        return None
    try:
        pr = json.loads(m.group(1))
    except Exception:
        return None
    vd = pr.get("videoDetails", {}) or {}
    mf = (pr.get("microformat", {}) or {}).get("playerMicroformatRenderer", {}) or {}
    ps = pr.get("playabilityStatus", {}) or {}
    return {"title": vd.get("title"), "channel": vd.get("author"), "channel_id": vd.get("channelId"),
            "description": vd.get("shortDescription", ""), "length": int(vd.get("lengthSeconds") or 0),
            "views": int(vd.get("viewCount") or 0), "publish_date": (mf.get("publishDate") or "")[:10],
            "upload_date": (mf.get("uploadDate") or "")[:10], "category": mf.get("category"),
            "status": ps.get("status"), "embeddable": ps.get("playableInEmbed"),
            "is_live": vd.get("isLiveContent")}
