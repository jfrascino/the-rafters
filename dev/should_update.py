#!/usr/bin/env python3
"""Decide whether the hands-off updater should run now (exit 0 = run, 1 = skip).
  game window   from 3 h before tip to 6 h after: every run (launchd fires every 20 min)
  after a game  for 36 h: every 2 h (UConn posts stat corrections; polls and box scores settle)
  otherwise     every 6 h (schedule, tip times, TV, roster, polls)
  --force       always run"""
import datetime as dt, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, 'dev', '.update_state.json')
now = dt.datetime.now(dt.timezone.utc)


def last_run():
    try:
        return dt.datetime.fromisoformat(json.load(open(STATE))['last'])
    except Exception:
        return None


def tips():
    core = json.load(open(os.path.join(ROOT, 'site', 'data', 'core.json')))
    y = (core.get('current') or {}).get('season') or core['seasons'][-1]['y']
    out = []
    for g in json.load(open(os.path.join(ROOT, 'site', 'data', 'seasons', f'{y}.json'))).get('games') or []:
        d = g.get('date') or ''
        try:
            t = dt.datetime.fromisoformat(d.replace('Z', '+00:00')) if 'T' in d else dt.datetime.fromisoformat(d + 'T23:00:00+00:00')
        except ValueError:
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=dt.timezone.utc)
        out.append(t)
    return out


def main():
    if '--force' in sys.argv:
        return 0
    last = last_run()
    since = (now - last).total_seconds() / 3600 if last else 1e9
    for t in tips():
        hrs = (now - t).total_seconds() / 3600
        if -3 <= hrs <= 6:
            return 0                     # game window
        if 6 < hrs <= 36 and since >= 2:
            return 0                     # settling after a game
    return 0 if since >= 6 else 1


if __name__ == '__main__':
    sys.exit(main())
