#!/usr/bin/env bash
set -uo pipefail

# Keep one previous generation (*.old); checks once at startup, then daily.
LOG_DIR=/var/log/nginx
MAX_BYTES=1073741824
INTERVAL_SECONDS=86400

rotate() {
    local f size
    local rotated=0

    for f in "$LOG_DIR"/*-access.log; do
        [ -f "$f" ] || continue
        size=$(stat -c %s "$f" 2>/dev/null || echo 0)
        if [ "$size" -gt "$MAX_BYTES" ]; then
            mv -f "$f" "$f.old"
            rotated=1
        fi
    done

    if [ "$rotated" = 1 ]; then
        nginx -s reopen 2>/dev/null || true
    fi
}

while true; do
    rotate
    sleep "$INTERVAL_SECONDS"
done
