"""Rate-limited, cached fetcher for Sports-Reference (CBB).

- Every raw HTML is cached under pipeline/cache.nosync/sr/<url path>.
- Never re-downloads a cached page unless force=True.
- Sequential only; >= 3.5 s between network requests (SR bans >20 req/min).
- On HTTP 429: sleep 90 s and retry, max 3 retries, then raise RateLimited.
- 404s are remembered with a <path>.404 marker so they aren't re-requested.
"""
import os, time, gzip, urllib.request, urllib.error
from urllib.parse import urlparse

BASE = "https://www.sports-reference.com"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache.nosync", "sr")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
DELAY = 3.5

_last = [0.0]
STATS = {"net": 0, "cache": 0, "404": 0}


class RateLimited(Exception):
    pass


class NotFound(Exception):
    pass


def cache_path(url):
    p = urlparse(url).path.lstrip("/")
    if p.endswith("/") or p == "":
        p = p + "index.html"
    elif not p.endswith(".html"):
        p = p + ".html"
    return os.path.join(CACHE, p)


def is_cached(url):
    cp = cache_path(url)
    return os.path.exists(cp) or os.path.exists(cp + ".404")


def fetch(url, force=False, log=print):
    if url.startswith("/"):
        url = BASE + url
    cp = cache_path(url)
    if not force:
        if os.path.exists(cp):
            STATS["cache"] += 1
            with open(cp, encoding="utf-8", errors="replace") as f:
                return f.read()
        if os.path.exists(cp + ".404"):
            STATS["404"] += 1
            raise NotFound(url)
    retries = 0
    while True:
        wait = DELAY - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip",
        })
        _last[0] = time.time()
        STATS["net"] += 1
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                html = data.decode("utf-8", errors="replace")
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retries += 1
                if retries > 3:
                    raise RateLimited(url)
                log(f"  429 on {url}; sleeping 90s (retry {retries}/3)")
                time.sleep(90)
                continue
            if e.code == 404:
                os.makedirs(os.path.dirname(cp), exist_ok=True)
                open(cp + ".404", "w").close()
                raise NotFound(url)
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            retries += 1
            if retries > 3:
                raise
            log(f"  network error {e} on {url}; sleeping 20s")
            time.sleep(20)
    os.makedirs(os.path.dirname(cp), exist_ok=True)
    tmp = cp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, cp)
    log(f"  GET {url} ({len(html)//1024} KB)")
    return html
