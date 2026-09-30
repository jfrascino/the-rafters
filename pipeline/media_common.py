"""Shared helpers for the media/storytelling pipeline (stdlib only).

Cached HTTP fetches -> pipeline/cache.nosync/media/<sha1>.{json,html}
"""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "cache.nosync", "media")
OUT = os.path.join(ROOT, "out", "media")
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

UA_API = "UConnHoopsFanApp/1.0 (personal non-commercial fan research project) python-urllib/3.14"
UA_BROWSER = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

WIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


MIN_INTERVAL = {"en.wikipedia.org": 2.0, "commons.wikimedia.org": 2.5,
                "www.youtube.com": 0.6}
_LAST = {}


def _key(url):
    return hashlib.sha1(url.encode()).hexdigest()


def fetch(url, browser=False, ttl=None, retries=3, ext="txt", allow_404=False):
    """GET url with on-disk cache. Returns text (or None on 404 if allow_404)."""
    path = os.path.join(CACHE, _key(url) + "." + ext)
    if os.path.exists(path):
        if ttl is None or time.time() - os.path.getmtime(path) < ttl:
            with open(path, encoding="utf-8") as f:
                txt = f.read()
            if txt == "__404__":
                return None
            return txt
    headers = {"User-Agent": UA_BROWSER if browser else UA_API,
               "Accept-Language": "en-US,en;q=0.9"}
    last = None
    host = urllib.parse.urlparse(url).netloc
    for i in range(retries + 3):
        wait = MIN_INTERVAL.get(host, 0.3) - (time.time() - _LAST.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        _LAST[host] = time.time()
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                txt = r.read().decode("utf-8", "replace")
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            return txt
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (404, 400, 401, 403) and allow_404:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("__404__")
                return None
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                try:
                    ra = float(ra)
                except Exception:
                    ra = 10 * (i + 1)
                time.sleep(min(max(ra, 5), 90))
            else:
                time.sleep(1.5 * (i + 1))
        except Exception as e:  # noqa
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"fetch failed {url}: {last}")


def api(base, **params):
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    url = base + "?" + urllib.parse.urlencode(params)
    return json.loads(fetch(url, ext="json"))


def wiki(**params):
    return api(WIKI_API, **params)


def commons(**params):
    return api(COMMONS_API, **params)


def wiki_url(title):
    return "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe="()_,'-–")


def save(name, obj):
    path = os.path.join(OUT, name)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return path


def load(name, default=None):
    path = os.path.join(OUT, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def wt2text(s):
    """Crude wikitext -> plain text (drops refs, templates, tables kept as rows)."""
    import re, html as _h
    s = _h.unescape(s)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    for _ in range(4):
        s = re.sub(r"\{\{(?:nowrap|nobr|small|big|sortname|Sortname)\|([^{}|]*)(?:\|([^{}|]*))?[^{}]*\}\}",
                   lambda m: (m.group(1) + (" " + m.group(2) if m.group(2) and "sortname" in m.group(0).lower() else "")), s)
        s = re.sub(r"\{\{(?:cbb link|Cbb link)\|[^{}]*?title=([^|{}]*)[^{}]*\}\}", r"\1", s)
        s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:File|Image):[^\[\]]*(?:\[\[[^\]]*\]\][^\[\]]*)*\]\]", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", s)
    s = re.sub(r"<br\s*/?>", "; ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("'''", "").replace("''", "")
    return s
