#! /usr/bin/env bash

set -e

dir=$(dirname $0)

if [[ -n $IN_CHINA ]]; then
    "$dir/replace-domain.bash" $(cat "$dir/china-source.txt")
fi

"$dir/replace-http.bash"

