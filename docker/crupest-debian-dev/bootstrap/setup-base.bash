#! /usr/bin/env bash

set -e

. /bootstrap/func.bash

echo "Setting up basic system function..."

echo "Installing basic packages..."
apt-get install -y apt-utils
apt-get install -y locales procps vim less man bash-completion software-properties-common rsync curl wget
echo "Installing basic packages done."

echo "Setting up locale..."
localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
echo "Setting up locale done."

echo "Creating data/state dir..."
mkdir -p /data /state
chown $CRUPEST_DEBIAN_DEV_USER:$CRUPEST_DEBIAN_DEV_USER /data /state
echo "Creating data dir done."

append-bash-profile bash-completion.bash

echo "Setting up basic system function done."