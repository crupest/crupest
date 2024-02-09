#! /usr/bin/env bash

set -e

dir=$(dirname "$0")

if [[ -n $IN_CHINA ]]; then
    "$dir/replace-domain.bash" "$(cat "$dir/china-source.txt")"
fi

"$dir/install-apt-https.bash"
"$dir/replace-http.bash"
