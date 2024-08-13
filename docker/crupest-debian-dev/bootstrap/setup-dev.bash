#! /usr/bin/env bash

set -e

. /bootstrap/func.bash

echo "Setting up dev function..."

echo "Installing dev packages..."
apt-get install -y build-essential git devscripts debhelper quilt \
    cpio kmod bc python3 bison flex libelf-dev libssl-dev libncurses-dev dwarves
echo "Installing dev packages done."

append-bash-profile dquilt.bash
copy-home-dot-file devscripts
copy-home-dot-file quiltrc-dpkg

echo "Setting up dev function done."
