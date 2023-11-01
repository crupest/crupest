#! /usr/bin/env bash

set -e

if [[ -f /etc/crupest-apt-source ]]; then
    CRUPEST_DEB_MIRROR=$(cat /etc/crupest-apt-source)
fi

apt-get install -y sbuild schroot debootstrap
sbuild-createchroot bullseye /srv/chroot/bullseye-amd64-sbuild ${CRUPEST_DEB_MIRROR}

