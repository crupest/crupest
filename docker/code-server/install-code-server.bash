#! /usr/bin/env bash

set -e

apt-get update
apt-get install -y locales curl
rm -rf /var/lib/apt/lists/* \
localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

VERSION=$(curl -s https://api.github.com/repos/coder/code-server/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')

curl -fOL "https://github.com/coder/code-server/releases/download/v${VERSION}/code-server_${VERSION}_amd64.deb"
dpkg -i "code-server_${VERSION}_amd64.deb"
