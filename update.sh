#!/bin/bash
# Local refresh: pull the current season from ESPN and rebuild site/data.
set -e
cd "$(dirname "$0")"
/opt/homebrew/bin/python3 pipeline/espn_fetch.py --update
/opt/homebrew/bin/python3 pipeline/build.py | tail -3
