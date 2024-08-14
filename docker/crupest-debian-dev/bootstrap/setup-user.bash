#! /usr/bin/env bash

set -e

echo "Setting up user..."

echo "Installing sudo..."
apt-get install -y sudo
echo "Installing sudo done."

echo "Setting up sudo..."
sed -i.bak 's|%sudo[[:space:]]\+ALL=(ALL:ALL)[[:space:]]\+ALL|%sudo ALL=(ALL:ALL) NOPASSWD: ALL|' /etc/sudoers
echo "Setting up sudo done."

echo "Adding user $CRUPEST_DEBIAN_DEV_USER ..."
useradd -m -G sudo -s /usr/bin/bash "$CRUPEST_DEBIAN_DEV_USER"
echo "Adding user done."

echo "Setting up user done."

