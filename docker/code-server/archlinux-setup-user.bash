#!/usr/bin/env bash

# check if we are in docker by CRUPEST_IN_DOCKER
if [ "${CRUPEST_IN_DOCKER}" != "true" ]; then
    echo "This script is intended to be run in a docker container."
    exit 1
fi

cd ~ || exit 1

mkdir data

mkdir aur
cd aur || exit 1

# install all aur packages
for aur_package in ${CRUPEST_AUR_PACKAGES} ; do
    echo "Installing ${aur_package} from AUR..."
    git clone "https://aur.archlinux.org/${aur_package}.git" --depth 1
    pushd "${aur_package}" || exit 1
    makepkg -sr --noconfirm
    makepkg --packagelist | sudo pacman -U --noconfirm -
    popd || exit 1
done
