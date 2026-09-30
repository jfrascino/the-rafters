"""Shared helpers for the player/team photo pipeline (stdlib only).

- cached, polite HTTP GETs  -> pipeline/cache.nosync/photos/<sha1>.<ext>
- image probing (status, content-type, width/height) with a hotlink Referer
- incremental JSON output helpers for pipeline/out/media/{player,team}_photos.json
"""
import hashlib
import json
import os
import re
import struct
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
CACHE = os.path.join(ROOT, "cache.nosync", "photos")
OUT = os.path.join(ROOT, "out", "media")
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

CORE = os.path.join(PROJ, "site", "data", "core.json")
SR_PLAYERS = os.path.join(ROOT, "out", "sr", "players")
PLAYER_OUT = os.path.join(OUT, "player_photos.json")
TEAM_OUT = os.path.join(OUT, "team_photos.json")
CAND_DIR = os.path.join(CACHE, "candidates")  # per-source candidate files
os.makedirs(CAND_DIR, exist_ok=True)

REFERER = "https://jfrascino.github.io/"
UA_BROWSER = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
UA_API = "UConnHoopsFanApp/1.0 (personal non-commercial fan research project; github.com/jfrascino) python-urllib"

SLOW_HOSTS = ("sports-reference.com", "basketball-reference.com")
_LAST = {}


def _interval(host):
    if any(host.endswith(h) for h in SLOW_HOSTS):
        return 4.2
    if host.endswith("wikimedia.org") or host.endswith("wikipedia.org"):
        return 1.5
    return 1.05


def _wait(host):
    w = _interval(host) - (time.time() - _LAST.get(host, 0))
    if w > 0:
        time.sleep(w)
    _LAST[host] = time.time()


def key(s):
    return hashlib.sha1(s.encode()).hexdigest()


def fetch(url, browser=True, ttl=None, ext="html", headers=None, allow_404=True, retries=3, data=None):
    """GET (or POST if data) with on-disk cache. Returns text or None (404/403/410)."""
    ck = url + ("|POST|" + data.decode() if data else "")
    path = os.path.join(CACHE, key(ck) + "." + ext)
    if os.path.exists(path) and (ttl is None or time.time() - os.path.getmtime(path) < ttl):
        txt = open(path, encoding="utf-8").read()
        return None if txt == "__404__" else txt
    h = {"User-Agent": UA_BROWSER if browser else UA_API, "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        h.update(headers)
    host = urllib.parse.urlparse(url).netloc
    last = None
    for i in range(retries):
        _wait(host)
        try:
            req = urllib.request.Request(url, headers=h, data=data)
            with urllib.request.urlopen(req, timeout=40) as r:
                txt = r.read().decode("utf-8", "replace")
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            return txt
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (404, 410, 400) or (e.code == 403 and allow_404 and i == retries - 1):
                if allow_404:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write("__404__")
                    return None
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                try:
                    ra = float(ra)
                except Exception:
                    ra = 15 * (i + 1)
                time.sleep(min(max(ra, 5), 120))
            else:
                time.sleep(2 * (i + 1))
        except Exception as e:  # noqa
            last = e
            time.sleep(2 * (i + 1))
    print("  fetch failed", url, last)
    return None


def fetch_json(url, **kw):
    kw.setdefault("ext", "json")
    t = fetch(url, **kw)
    if t is None:
        return None
    try:
        return json.loads(t)
    except Exception:
        return None


# ---------------------------------------------------------------- image probing
def image_size(b):
    """Return (w, h) from image header bytes (PNG/JPEG/GIF/WebP) or (None, None)."""
    try:
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", b[16:24])
            return w, h
        if b[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", b[6:10])
            return w, h
        if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
            chunk = b[12:16]
            if chunk == b"VP8 ":
                w, h = struct.unpack("<HH", b[26:30])
                return w & 0x3FFF, h & 0x3FFF
            if chunk == b"VP8L":
                bits = struct.unpack("<I", b[21:25])[0]
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            if chunk == b"VP8X":
                w = int.from_bytes(b[24:27], "little") + 1
                h = int.from_bytes(b[27:30], "little") + 1
                return w, h
        if b[:2] == b"\xff\xd8":
            i = 2
            while i < len(b) - 9:
                if b[i] != 0xFF:
                    i += 1
                    continue
                m = b[i + 1]
                if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                    i += 2
                    continue
                ln = struct.unpack(">H", b[i + 2:i + 4])[0]
                if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", b[i + 5:i + 9])
                    return w, h
                i += 2 + ln
    except Exception:
        pass
    return None, None


def png_has_alpha(b):
    try:
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            color_type = b[25]
            return color_type in (4, 6) or b"tRNS" in b[:4096]
    except Exception:
        pass
    return False


PROBE_DB = os.path.join(CACHE, "probe.json")
_PROBES = None


def _probes():
    global _PROBES
    if _PROBES is None:
        _PROBES = json.load(open(PROBE_DB)) if os.path.exists(PROBE_DB) else {}
    return _PROBES


def save_probes():
    if _PROBES is not None:
        tmp = PROBE_DB + ".tmp"
        json.dump(_PROBES, open(tmp, "w"))
        os.replace(tmp, PROBE_DB)


def probe(url, force=False, keep=False):
    """Fetch the image with a hotlink Referer. Returns dict(ok, status, ctype, w, h, alpha, bytes).
    Only the first ~512 KB are read (enough for headers) unless keep=True (writes cache copy)."""
    db = _probes()
    if not force and url in db:
        return db[url]
    host = urllib.parse.urlparse(url).netloc
    res = {"ok": False, "status": None, "ctype": None, "w": None, "h": None, "alpha": False}
    for attempt in range(3):
        _wait(host)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA_BROWSER, "Referer": REFERER,
                                                       "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8"})
            with urllib.request.urlopen(req, timeout=40) as r:
                res["status"] = r.status
                res["ctype"] = r.headers.get("Content-Type", "")
                res["final_url"] = r.geturl()
                b = r.read() if keep else r.read(512 * 1024)
            w, h = image_size(b)
            res["w"], res["h"] = w, h
            res["alpha"] = png_has_alpha(b)
            res["ok"] = bool(res["status"] == 200 and (res["ctype"] or "").startswith("image/") and w)
            res["bytes0"] = len(b)
            if keep and res["ok"]:
                open(os.path.join(CACHE, "img_" + key(url)), "wb").write(b)
            break
        except urllib.error.HTTPError as e:
            res["status"] = e.code
            if e.code == 429:
                time.sleep(20 * (attempt + 1))
                continue
            break
        except Exception as e:  # noqa
            res["status"] = "err:" + str(e)[:80]
            time.sleep(2)
    res["checked"] = time.strftime("%Y-%m-%d")
    db[url] = res
    if len(db) % 10 == 0:
        save_probes()
    return res


# ---------------------------------------------------------------- players
def load_players():
    return json.load(open(CORE))["players"]


def load_sr(pid):
    p = os.path.join(SR_PLAYERS, pid + ".json")
    return json.load(open(p)) if os.path.exists(p) else {}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = s.lower().replace("&#x27;", "'")
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", s)
    s = re.sub(r"[^a-z]", "", s)
    return s


def save_candidates(source, data):
    p = os.path.join(CAND_DIR, source + ".json")
    tmp = p + ".tmp"
    json.dump(data, open(tmp, "w"), indent=1)
    os.replace(tmp, p)


def load_candidates(source):
    p = os.path.join(CAND_DIR, source + ".json")
    return json.load(open(p)) if os.path.exists(p) else {}
