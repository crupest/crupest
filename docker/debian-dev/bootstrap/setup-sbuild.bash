#! /usr/bin/env bash

set -e

if [[ -f /etc/crupest-apt-source ]]; then
    CRUPEST_DEB_MIRROR=$(cat /etc/crupest-apt-source)
fi

if [[ -z "${SBUILD_ARCH}" ]]; then
    SBUILD_ARCH="amd64"
fi

apt-get install -y sbuild schroot debootstrap

cp /bootstrap/sbuildrc /root/.sbuildrc

sbuild-createchroot --arch=${SBUILD_ARCH} bullseye /srv/chroot/bullseye-${SBUILD_ARCH}-sbuild ${CRUPEST_DEB_MIRROR}

