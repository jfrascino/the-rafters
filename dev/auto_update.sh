#!/bin/bash
# Hands-off updater (launchd runs this every 20 minutes; dev/should_update.py decides if anything could have changed).
# Pulls the current season from ESPN plus UConn's official roster and stat pages, rebuilds, and publishes
# DATA ONLY (site/data, site/assets, pipeline/out). Code is published only by deploy.sh.
cd "$(dirname "$0")/.."
PY=/opt/homebrew/bin/python3
G="git -c user.name=jfrascino -c user.email=47570206+jfrascino@users.noreply.github.com"
stamp() { date '+%Y-%m-%d %H:%M:%S'; }
notify() { osascript -e "display notification \"${2//\"/}\" with title \"Storrs Lore\" subtitle \"$1\"" 2>/dev/null || true; }
$PY dev/should_update.py "$@" || exit 0
# a code change in progress (Kai mid-edit) must not be built into published data
if [ -n "$(git status --porcelain -- pipeline/*.py site/js site/css site/index.html 2>/dev/null)" ]; then
  echo "$(stamp) skipped: uncommitted code changes in progress"; exit 0
fi
source dev/lock.sh; lock
BEFORE=$($PY -c "import json;c=json.load(open('site/data/core.json'));print(json.dumps((c.get('current') or {}).get('last')))" 2>/dev/null)
$PY pipeline/espn_fetch.py --update --quiet >/dev/null 2>&1 || echo "$(stamp) ESPN fetch had errors (continuing with cached data)"
$PY pipeline/official_roster.py >/dev/null 2>&1 || echo "$(stamp) official roster fetch failed; keeping the last copy"
$PY pipeline/official_current_stats.py >/dev/null 2>&1 || echo "$(stamp) official stats fetch failed; keeping the last copy"
if ! OUT=$($PY pipeline/build.py 2>&1); then
  echo "$(stamp) BUILD FAILED"; echo "$OUT" | tail -20
  notify "Update failed" "The data build failed; the live site is unchanged. Ask Kai to look at dev/logs/update.log."
  exit 1
fi
echo "$OUT" | grep -E "official check|play-by-play hidden|jersey numbers|!!" | sed "s/^/$(stamp) /"
$PY -c "import json,datetime;json.dump({'last':datetime.datetime.now(datetime.timezone.utc).isoformat()},open('dev/.update_state.json','w'))"
git add site/data site/assets pipeline/out 2>/dev/null
# the build stamps core.json with the time it ran; that alone is not news
if git diff --cached --quiet -- . ':!site/data/core.json' && $PY - <<'PYEOF'
import json, subprocess, sys
old = json.loads(subprocess.run(['git', 'show', 'HEAD:site/data/core.json'], capture_output=True, text=True).stdout or '{}')
new = json.load(open('site/data/core.json'))
old.pop('updated', None); new.pop('updated', None)
sys.exit(0 if old == new else 1)
PYEOF
then
  git reset -q site/data/core.json && git checkout -q -- site/data/core.json
  echo "$(stamp) no changes"; exit 0
fi
AFTER=$($PY -c "import json;c=json.load(open('site/data/core.json'));print(json.dumps((c.get('current') or {}).get('last')))" 2>/dev/null)
$G commit -qm "Data update $(date '+%Y-%m-%d %H:%M')"
git fetch -q origin main && [ "$(git rev-list --count HEAD..origin/main)" != 0 ] && git pull -q --rebase --autostash origin main
if ! git push -q origin main; then echo "$(stamp) push failed"; notify "Update failed" "Couldn't push to GitHub (network or login)."; exit 1; fi
git branch -D pages-tmp -q 2>/dev/null || true
git subtree split --prefix site -b pages-tmp -q >/dev/null && git push -qf origin pages-tmp:gh-pages
echo "$(stamp) published"
if [ "$BEFORE" != "$AFTER" ] && [ "$AFTER" != "null" ]; then
  MSG=$($PY -c "import json;g=json.loads('''$AFTER''');print(f\"UConn {g['pts']}, {g['opp']['name']} {g['opp_pts']} ({g['res']}). Box score and stats are live.\")" 2>/dev/null)
  [ -n "$MSG" ] && notify "Final" "$MSG"
fi
