#! /usr/bin/env bash

set -e

dir=/bootstrap/apt-source

echo "Getting debian version..."
debian_version=$(bash "$dir/../get-debian-version.bash")

if [[ -z $debian_version ]]; then
    echo "Debian version not found."
    exit 1
else
    echo "Debian version: $debian_version"
fi

if [[ $debian_version -ge 12 ]]; then
    setup_dir=$dir/12
else
    setup_dir=$dir/11
fi

echo "Setting up apt source..."

if [[ -n $CRUPEST_DEBIAN_DEV_IN_CHINA ]]; then
    echo "In China, using China source..."
    "$setup_dir/replace-domain.bash" "$(cat "$dir/china-source.txt")"
fi

"$dir/install-apt-https.bash"
"$setup_dir/replace-http.bash"

echo "Setting up apt source done."
