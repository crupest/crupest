#! /usr/bin/env bash

set -e

. /bootstrap/func.bash

echo "Setting up dev function..."

echo "Installing dev packages..."
apt-get install -y build-essential git devscripts debhelper quilt
apt-get build-dep -y linux
echo "Installing dev packages done."

append-bashrc dquilt.bash
copy-home-dot-file devscripts
copy-home-dot-file quiltrc-dpkg

echo "Setting up dev function done."
