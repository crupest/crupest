#! /usr/bin/env bash

set -e -o pipefail

china_mirror="mirrors.ustc.edu.cn"
try_files=("/etc/apt/sources.list" "/etc/apt/sources.list.d/debian.sources")
files=()

for try_file in "${try_files[@]}"; do
    if [[ -f "$try_file" ]]; then
        files+=("$try_file")
    fi
done

for file in "${files[@]}"; do
    echo "copy $file to $file.bak"
    cp "$file" "$file.bak"
done

if [[ -n "$CRUPEST_DEBIAN_DEV_CHINA" ]]; then
    echo "use China mirrors"
    for file in "${files[@]}"; do
        sed -i "s|deb.debian.org|${china_mirror}|g" "$file"
    done
fi

echo "use https"
apt-get update
apt-get install -y apt-transport-https ca-certificates

for file in "${files[@]}"; do
    sed -i 's|http://|https://|g' "$file"
done
