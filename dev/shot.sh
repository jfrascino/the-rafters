#!/bin/bash
# Headless screenshot: dev/shot.sh <hash-route> <out.png> [WxH] [wait-ms]
# Chrome's --screenshot sometimes never exits, so we kill it once the PNG lands.
ROUTE="$1"; OUT="$2"; SIZE="${3:-1440,1000}"; WAIT="${4:-6000}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE=$(mktemp -d)
rm -f "$OUT"
"$CHROME" --headless=new --disable-gpu-sandbox --use-angle=swiftshader --enable-unsafe-swiftshader \
  --hide-scrollbars --user-data-dir="$PROFILE" --window-size="$SIZE" --virtual-time-budget="$WAIT" \
  --screenshot="$OUT" "http://localhost:8786/?shot=1#${ROUTE}" >/dev/null 2>&1 &
PID=$!
for i in $(seq 1 90); do
  if [ -s "$OUT" ]; then sleep 0.5; break; fi
  sleep 0.5
done
kill $PID 2>/dev/null; sleep 0.3; kill -9 $PID 2>/dev/null
rm -rf "$PROFILE"
[ -s "$OUT" ] && echo "ok $OUT" || echo "FAILED $OUT"
