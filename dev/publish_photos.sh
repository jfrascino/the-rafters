#!/bin/bash
# Publish Jason's photo drops: rebuild data, commit ONLY data + images (never in-progress code), push, update GitHub Pages.
cd "$(dirname "$0")/.."
source dev/lock.sh; lock
G="git -c user.name=jfrascino -c user.email=47570206+jfrascino@users.noreply.github.com"
OUT=$(/opt/homebrew/bin/python3 pipeline/build.py 2>&1)
echo "$OUT" | grep -E "photos-drop|^!" 
git add site/data site/assets pipeline/out pipeline/photo_rejects.json pipeline/manual_games.json 2>/dev/null
if git diff --cached --quiet; then echo "$(date '+%H:%M:%S') nothing new to publish"; exit 0; fi
NEW=$(echo "$OUT" | grep -E "^photos-drop: .* → " | sed -E 's/^photos-drop: (.*)\.[A-Za-z]+ → .*/\1/' | paste -sd, - | sed 's/,/, /g')
BAD=$(echo "$OUT" | grep -E "no player matches" | sed -E 's/.*matches "(.*)"/\1/' | paste -sd, - | sed 's/,/, /g')
$G commit -qm "Photo drop: ${NEW:-updated photos}"
git fetch -q origin main && [ "$(git rev-list --count HEAD..origin/main)" != 0 ] && git pull -q --rebase --autostash origin main   # only if someone else pushed
git push -q origin main
git branch -D pages-tmp -q 2>/dev/null || true
git subtree split --prefix site -b pages-tmp -q >/dev/null && git push -qf origin pages-tmp:gh-pages
echo "$(date '+%H:%M:%S') published: ${NEW:-(no renamed files)}${BAD:+ | NOT MATCHED: $BAD}"
MSG="Live in about a minute: ${NEW:-updated photos}"
[ -n "$BAD" ] && MSG="$MSG. No player named: $BAD (rename the file)"
osascript -e "display notification \"${MSG//\"/}\" with title \"The Rafters\" subtitle \"Photos published\"" 2>/dev/null || true
