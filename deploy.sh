#!/bin/bash
# Commit current data + app, push main (private backup), and publish site/ to Cloudflare Pages
# (https://storrs-lore.pages.dev/). The gh-pages branch push is a leftover from GitHub Pages and harmless.
set -e
cd "$(dirname "$0")"
source dev/lock.sh; lock   # never deploy while the photo watcher is publishing
G="git -c user.name=jfrascino -c user.email=47570206+jfrascino@users.noreply.github.com"
/opt/homebrew/bin/python3 pipeline/stamp.py   # fingerprint JS/CSS so browsers never mix old and new files
git add -A
$G commit -qm "${1:-Update}" || true
git pull -q --rebase origin main || true
git push -q origin main
git branch -D pages-tmp -q 2>/dev/null || true
git subtree split --prefix site -b pages-tmp -q
git push -qf origin pages-tmp:gh-pages
/opt/homebrew/bin/python3 $HOME/.local/bin/cf-pages-deploy site storrs-lore
