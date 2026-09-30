# One publisher at a time (the photo watcher and manual deploys share this lock).
LOCKDIR=/tmp/the-rafters.publish.lock
lock() { local n=0; until mkdir "$LOCKDIR" 2>/dev/null; do n=$((n+1)); [ $n -gt 600 ] && { echo "lock stuck; removing"; rmdir "$LOCKDIR" 2>/dev/null; }; sleep 1; done; trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT; }
