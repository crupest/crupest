#! /usr/bin/env bash
# shellcheck disable=1090,1091

set -e

if [[ $EUID -ne 0 ]]; then
    die "This script must be run as root."
fi

script_dir=$(dirname "$0")

old_one="/etc/apt/sources.list"
new_one="/etc/apt/sources.list.d/debian.sources"

echo "Setup apt sources ..."

echo "Backup old ones to .bak ..."
if [[ -f "$old_one" ]]; then
    mv "$old_one" "$old_one.bak"
fi

if [[ -f "$new_one" ]]; then
    mv "$new_one" "$new_one.bak"
fi

echo "Copy the new one ..."
cp "$script_dir/official.sources" "$new_one"

if [[ -n "$CRUPEST_DEBIAN_DEV_IN_CHINA" ]]; then
    echo "Replace with China mirror ..."
    china_mirror="mirrors.ustc.edu.cn"
    sed -i "s|deb.debian.org|${china_mirror}|" "$new_one"
fi

echo "Try to use https ..."
apt-get update
apt-get install -y apt-transport-https ca-certificates

sed -i 's|http://|https://|' "$new_one"

echo "APT source setup done!"
