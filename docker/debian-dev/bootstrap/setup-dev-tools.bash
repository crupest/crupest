#! /usr/bin/env bash

set -e

apt-get install -y build-essential devscripts debhelper quilt cpio kmod git bc python bison flex rsync libelf-dev libssl-dev libncurses-dev dwarves

cp /bootstrap/quiltrc-dpkg /root/.quiltrc-dpkg
cat /bootstrap/bash-profile/dquilt.bash >> /root/.bash_profile

