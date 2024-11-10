#! /usr/bin/env bash

set -e

dir=$(dirname "$0")
domain=$("$dir/get-domain.bash")

cat <<EOF >> /etc/apt/sources.list

deb-src https://$domain/debian/ bullseye main
deb-src https://$domain/debian-security/ bullseye-security main
deb-src https://$domain/debian-updates/ bullseye-updates main

EOF
