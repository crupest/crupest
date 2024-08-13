#! /usr/bin/env bash

set -e

dir=$(dirname "$0")
domain=$("$dir/get-domain.bash")

cat <<EOF >> /etc/apt/sources.list.d/debian.sources

Types: deb-src
URIs: https://$domain/debian
Suites: bookworm bookworm-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb-src
URIs: https://$domain/debian-security
Suites: bookworm-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

EOF