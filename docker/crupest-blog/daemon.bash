#! /usr/bin/env bash

set -e

# Check I'm root.
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

hugo --version

while true; do
    /scripts/update.bash

    # sleep for CRUPEST_AUTO_BACKUP_INTERVAL
    echo "Sleep for $CRUPEST_BLOG_UPDATE_INTERVAL for next build..."
    sleep "$CRUPEST_BLOG_UPDATE_INTERVAL"
done
