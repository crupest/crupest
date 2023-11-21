#! /usr/bin/env bash

set -e

dir=$(dirname $0)

. /bootstrap/func.bash

apt-get install -y sbuild schroot debootstrap

copy-home-dot-file sbuildrc

# setup apt-cacher-ng
apt-get install -y apt-cacher-ng
append-bash-profile auto-start-apt-cacher.bash
apt-cacher-ng
export SBUILD_MIRROR="http://127.0.0.1:3142/$(/bootstrap/apt-source/get-domain.bash)/debian"

export SBUILD_DIST="bullseye"

"$dir/setup-amd64.bash"

if [[ "$BUILD_FOR_ARCH" == "arm64" ]]; then
    "$dir/setup-arm64.bash"
fi
