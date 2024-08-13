#! /usr/bin/env bash

set -e

dir=$(dirname "$0")

echo "Setting up apt source..."

if [[ -n $CRUPEST_DEBIAN_DEV_IN_CHINA ]]; then
    echo "In China, using China source..."
    "$dir/replace-domain.bash" "$(cat "$dir/china-source.txt")"
fi

"$dir/install-apt-https.bash"
"$dir/replace-http.bash"

echo "Setting up apt source done."
