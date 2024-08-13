#! /usr/bin/env bash

set -e

apt-get install -y sudo

sed -i.bak 's|%sudo[[:space:]]\+ALL=(ALL:ALL)[[:space:]]\+ALL|%sudo ALL=(ALL:ALL) NOPASSWD: ALL|' /etc/sudoers

useradd -m -G sudo -s /usr/bin/bash "$USERNAME"
