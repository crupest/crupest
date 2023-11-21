#! /usr/bin/env bash

set -e

SBUILD_ARCH="arm64"
SBUILD_DIST="bullseye"

sbuild-createchroot --include=eatmydata --command-prefix=eatmydata --foreign --arch=${SBUILD_ARCH} ${SBUILD_DIST} /srv/chroot/${SBUILD_DIST}-${SBUILD_ARCH}-sbuild "http://$(/bootstrap/apt-source/get-domain.bash)/debian"
