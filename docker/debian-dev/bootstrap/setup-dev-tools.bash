#! /usr/bin/env bash

set -e

apt-get install -y build-essential git devscripts debhelper quilt \
    cpio kmod bc python bison flex rsync libelf-dev libssl-dev libncurses-dev dwarves

cat /bootstrap/bash-profile/dev.bash >> /root/.bash_profile
cat /bootstrap/bash-profile/dquilt.bash >> /root/.bash_profile

for f in /bootstrap/home-dot/*; do
    filename=$(basename "$f")
    cp "$f" "/root/.$filename"
done

if [[ "$BUILD_FOR_ARCH" == "arm64" ]]; then
    /bootstrap/setup-dev-tools-arm64.bash
fi
