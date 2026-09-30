"""Wikidata lookup: SR CBB id (P3696) / BBRef NBA id (P2685) -> NBA.com id (P3647), ESPN NBA id (P3685),
BBRef international (P4790) / G League (P4744) ids, Commons image (P18), enwiki title.
Writes cache.nosync/photos/wikidata_ids.json {sr_id: {...}}"""
import json, re, urllib.parse
from photos_common import fetch_json, load_players, load_sr, CACHE
import os

def q(sparql):
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(sparql)
    d = fetch_json(url, browser=False)
    return d["results"]["bindings"] if d else []

def main():
    P = load_players()
    ids = [p["id"] for p in P]
    bb = {}
    for p in P:
        s = load_sr(p["id"])
        m = re.search(r"/players/(./[^.]+)\.html", s.get("nba_url") or "")
        if m:
            bb[m.group(1)] = p["id"]
    fields = """OPTIONAL{?item wdt:P3647 ?nba} OPTIONAL{?item wdt:P3685 ?espn} OPTIONAL{?item wdt:P4790 ?intl}
      OPTIONAL{?item wdt:P4744 ?gl} OPTIONAL{?item wdt:P18 ?img} OPTIONAL{?item wdt:P2685 ?bbv} OPTIONAL{?item wdt:P3696 ?cbbv}
      OPTIONAL{?art schema:about ?item; schema:isPartOf <https://en.wikipedia.org/>; schema:name ?enwiki}"""
    out = {}
    def absorb(rows, keyfn):
        for r in rows:
            sid = keyfn(r)
            if not sid: continue
            e = out.setdefault(sid, {"wd": r["item"]["value"]})
            for k in ("nba", "espn", "intl", "gl", "img", "bbv", "cbbv", "enwiki"):
                if k in r:
                    v = r[k]["value"]
                    lst = e.setdefault(k, [])
                    if v not in lst: lst.append(v)
    for i in range(0, len(ids), 60):
        vals = " ".join(f'"{x}"' for x in ids[i:i+60])
        rows = q(f"SELECT * WHERE {{ VALUES ?cbb {{ {vals} }} ?item wdt:P3696 ?cbb . {fields} }}")
        absorb(rows, lambda r: r["cbb"]["value"])
    vals = " ".join(f'"{x}"' for x in bb)
    rows = q(f"SELECT * WHERE {{ VALUES ?bb {{ {vals} }} ?item wdt:P2685 ?bb . {fields} }}")
    absorb(rows, lambda r: bb.get(r["bb"]["value"]))
    json.dump(out, open(os.path.join(CACHE, "wikidata_ids.json"), "w"), indent=1)
    print("wikidata items:", len(out), "nba ids:", sum(1 for v in out.values() if v.get("nba")),
          "espn:", sum(1 for v in out.values() if v.get("espn")), "P18:", sum(1 for v in out.values() if v.get("img")),
          "intl:", sum(1 for v in out.values() if v.get("intl")), "gl:", sum(1 for v in out.values() if v.get("gl")))

if __name__ == "__main__":
    main()
