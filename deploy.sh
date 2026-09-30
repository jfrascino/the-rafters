#!/bin/bash
# Commit current data + app, push main, and publish site/ to the gh-pages branch (GitHub Pages).
set -e
cd "$(dirname "$0")"
G="git -c user.name=jfrascino -c user.email=47570206+jfrascino@users.noreply.github.com"
git add -A
$G commit -qm "${1:-Update}" || true
git pull -q --rebase origin main || true
git push -q origin main
git branch -D pages-tmp -q 2>/dev/null || true
git subtree split --prefix site -b pages-tmp -q
git push -qf origin pages-tmp:gh-pages
echo "Deployed: https://jfrascino.github.io/the-rafters/"
