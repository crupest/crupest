#!/usr/bin/env bash

# check if we are in docker by CRUPEST_IN_DOCKER
if [ "${CRUPEST_IN_DOCKER}" != "true" ]; then
    echo "This script is intended to be run in a docker container."
    exit 1
fi

# check if we are root
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root."
    exit 1
fi

# CRUPEST_USER, CRUPEST_UID, CRUPEST_GID must be defined
if [ -z "$CRUPEST_USER" ] || [ -z "$CRUPEST_UID" ] || [ -z "$CRUPEST_GID" ]; then
    echo "CRUPEST_USER, CRUPEST_UID, CRUPEST_GID must be defined."
    exit 1
fi

# if we are in China (by checking USE_CHINA_MIRROR), use the mirror in China
if [ "$USE_CHINA_MIRROR" = "true" ]; then
    echo "You have set USE_CHINA_MIRROR to true, using mirror ${CHINA_MIRROR_URL} (set by CHINA_MIRROR_URL) in China."
    echo "Server = ${CHINA_MIRROR_URL}" > /etc/pacman.d/mirrorlist
fi

# from now on, we don't allow error
set -e

# Update the system and I need python3
pacman -Syu --noconfirm python

# execute the restore pacman config script
python3 ./restore-pacman-conf.py

# reinstall all installed packages
pacman -Qnq | pacman -S --noconfirm --overwrite=* -

# install new packages
echo "base-devel git ${CRUPEST_PACKAGES}" | tr " " "\n" | pacman -S --noconfirm --needed -

# if GROUP not defined, set it the same to USER
if [ -z "$CRUPEST_GROUP" ]; then
    CRUPEST_GROUP="$CRUPEST_USER"
fi

# check if GROUP exists. if not create it with GID
if ! grep -q "^${CRUPEST_GROUP}:" /etc/group; then
    groupadd -g "$CRUPEST_GID" "$CRUPEST_GROUP"
fi

# create user for UID and GID
useradd -m -u "${CRUPEST_UID}" -g "${CRUPEST_GID}" "${CRUPEST_USER}"

# add the user to sudo
echo "${CRUPEST_USER} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# create data directory and change the permission
mkdir -p /data
chown "${CRUPEST_USER}":"${CRUPEST_GROUP}" /data
chmod 700 /data
