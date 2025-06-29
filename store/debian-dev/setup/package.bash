#! /usr/bin/env bash

set -e -o pipefail

echo "install packages"
apt-get update
apt-get install -y \
    locales lsb-release software-properties-common  \
    sudo procps bash-completion man less gnupg curl wget \
    vim build-essential git devscripts debhelper quilt
