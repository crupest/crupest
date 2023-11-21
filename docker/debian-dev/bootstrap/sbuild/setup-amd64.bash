#! /usr/bin/env bash

set -e

SBUILD_ARCH="amd64"

sbuild-createchroot --include=eatmydata --command-prefix=eatmydata --arch=${SBUILD_ARCH} ${SBUILD_DIST} /srv/chroot/${SBUILD_DIST}-${SBUILD_ARCH}-sbuild "${SBUILD_MIRROR}"
