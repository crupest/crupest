#!/usr/bin/env bash

# check if we are in docker by CRUPEST_IN_DOCKER
if [ "${CRUPEST_IN_DOCKER}" != "true" ]; then
    echo "This script is intended to be run in a docker container."
    exit 1
fi

# don't allow any error
set -e

cd ~

mkdir aur
cd aur

# install all aur packages
for aur_package in code-server ${CRUPEST_AUR_PACKAGES} ; do
    echo "Installing ${aur_package} from AUR..."
    git clone "https://aur.archlinux.org/${aur_package}.git" --depth 1
    pushd "${aur_package}"

    # do some magic thing for China
    if [ "${USE_CHINA_MIRROR}" = "true" ]; then
        mv PKGBUILD PKGBUILD.old
        /tmp/china-magic-for-pkgbuild.py < PKGBUILD.old > PKGBUILD
    fi

    makepkg -sr --noconfirm
    makepkg --packagelist | sudo pacman -U --noconfirm -
    popd
done

# finnally, test code-server
code-server --version
