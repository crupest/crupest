#! /usr/bin/env bash

set -e -o pipefail

echo "set up locale"
localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

echo "set up sudo"
sed -i.bak 's|%sudo[[:space:]]\+ALL=(ALL:ALL)[[:space:]]\+ALL|%sudo ALL=(ALL:ALL) NOPASSWD: ALL|' /etc/sudoers

if ! id "username" &>/dev/null; then
  echo "create user $CRUPEST_DEBIAN_DEV_USER"
  useradd -m -G sudo -s /usr/bin/bash "$CRUPEST_DEBIAN_DEV_USER"
fi
