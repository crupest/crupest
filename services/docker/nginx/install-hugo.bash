#! /usr/bin/env bash

set -e

apt-get update
apt-get install -y locales curl
localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

VERSION=$(curl -s https://api.github.com/repos/gohugoio/hugo/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
echo "The latest version of hugo is $VERSION."
url="https://github.com/gohugoio/hugo/releases/download/v${VERSION}/hugo_extended_${VERSION}_linux-amd64.deb"
curl -fOL "$url"
dpkg -i "hugo_extended_${VERSION}_linux-amd64.deb"
rm "hugo_extended_${VERSION}_linux-amd64.deb"
hugo version
