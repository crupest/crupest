#! /usr/bin/env bash
# shellcheck disable=1090,1091

set -e -o pipefail

die() {
  echo "$@" >&2
  exit 1
}

if [[ $EUID -ne 0 ]]; then
    die "This script must be run as root."
fi

script_dir=$(dirname "$0")

os_release_file="/etc/os-release"
if [[ -f "$os_release_file" ]]; then
    debian_version=$(. "$os_release_file"; echo "$VERSION_CODENAME")
    if [[ "$debian_version" != "bookworm" ]]; then
        die "This script can only be run on Debian Bookworm. But it is $debian_version"
    fi
else
    die "$os_release_file not found. Failed to get debian version."
fi

script_dir=$(dirname "$0")

export DEBIAN_FRONTEND=noninteractive

echo "Begin to setup debian..."

bash "$script_dir/setup-apt.bash"

echo "Installing packages..."
apt-get update
apt-get install -y \
    tini locales procps sudo vim less man bash-completion curl wget \
    build-essential git devscripts debhelper quilt argon2

echo "Setting up locale..."
localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

echo "Setting up sudo..."
sed -i.bak 's|%sudo[[:space:]]\+ALL=(ALL:ALL)[[:space:]]\+ALL|%sudo ALL=(ALL:ALL) NOPASSWD: ALL|' /etc/sudoers

echo "Creating user $CRUPEST_DEBIAN_DEV_USER ..."
useradd -m -G sudo -s /usr/bin/bash "$CRUPEST_DEBIAN_DEV_USER"

echo "Setting up code-server..."
curl -fsSL https://code-server.dev/install.sh | sh

echo "Cleaning up apt source index..."
rm -rf /var/lib/apt/lists/*

echo "Setup debian done."
