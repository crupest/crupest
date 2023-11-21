#! /usr/bin/env bash

set -e

SBUILD_ARCH="amd64"
SBUILD_DIST="bullseye"

sbuild-createchroot --include=eatmydata --command-prefix=eatmydata --arch=${SBUILD_ARCH} ${SBUILD_DIST} /srv/chroot/${SBUILD_DIST}-${SBUILD_ARCH}-sbuild "http://$(/bootstrap/apt-source/get-domain.bash)/debian"
