"""CLI to add one verified photo candidate to a candidate file (used for manual / web-research finds).

Usage:
  python3 photos_add.py --file manual_a --id chris-smith-1 --url URL --kind nba-headshot \
      --source PAGE_URL --credit "..." --license "..." --caption "..." [--cutout]

The URL is probed with Referer https://jfrascino.github.io/ ; it is only saved if it returns 200 with an
image content-type and parseable dimensions. Prints the result as JSON.
List a file:   python3 photos_add.py --file manual_a --list
Remove entry:  python3 photos_add.py --file manual_a --id X --url URL --remove
"""
import argparse
import json
import sys

from photos_common import load_candidates, save_candidates, probe, save_probes, load_players

KINDS = ("uconn-headshot", "uconn-action", "uconn-team", "nba-headshot", "pro-other", "other")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--id")
    ap.add_argument("--url")
    ap.add_argument("--kind", choices=KINDS)
    ap.add_argument("--source")
    ap.add_argument("--credit", default="")
    ap.add_argument("--license", default="")
    ap.add_argument("--caption", default="")
    ap.add_argument("--cutout", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    data = load_candidates(a.file)
    if a.list:
        print(json.dumps(data, indent=1))
        return
    ids = {p["id"] for p in load_players()}
    if a.id not in ids:
        print(json.dumps({"ok": False, "error": f"unknown sr id {a.id}"}))
        sys.exit(1)
    if a.remove:
        data[a.id] = [c for c in data.get(a.id, []) if c["url"] != a.url]
        if not data[a.id]:
            del data[a.id]
        save_candidates(a.file, data)
        print(json.dumps({"ok": True, "removed": a.url}))
        return
    if not (a.url and a.kind and a.source):
        print(json.dumps({"ok": False, "error": "--url --kind --source required"}))
        sys.exit(1)
    pr = probe(a.url, force=True)
    save_probes()
    if not pr["ok"]:
        print(json.dumps({"ok": False, "error": "probe failed", "probe": pr}))
        sys.exit(2)
    c = {"url": a.url, "kind": a.kind, "cutout": bool(a.cutout or (pr.get("alpha") and a.kind.endswith("headshot"))),
         "w": pr["w"], "h": pr["h"], "source": a.source, "credit": a.credit, "license": a.license,
         "caption": a.caption}
    lst = [x for x in data.get(a.id, []) if x["url"] != a.url]
    lst.append(c)
    data[a.id] = lst
    save_candidates(a.file, data)
    print(json.dumps({"ok": True, "saved": c}))


if __name__ == "__main__":
    main()
