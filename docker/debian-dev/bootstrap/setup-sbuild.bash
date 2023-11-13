#! /usr/bin/env bash

set -e

if [[ -z "${SBUILD_ARCH}" ]]; then
    SBUILD_ARCH="amd64"
fi

apt-get install -y sbuild schroot debootstrap

cp /bootstrap/sbuildrc /root/.sbuildrc

sbuild-createchroot --arch=${SBUILD_ARCH} bullseye /srv/chroot/bullseye-${SBUILD_ARCH}-sbuild "https://$(/bootstrap/apt-source/get-domain.bash)/debian"

