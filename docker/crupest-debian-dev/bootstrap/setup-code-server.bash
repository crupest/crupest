#! /usr/bin/env bash

set -e

. /bootstrap/func.bash

VERSION=$(curl -s https://api.github.com/repos/coder/code-server/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
url="https://github.com/coder/code-server/releases/download/v${VERSION}/code-server_${VERSION}_amd64.deb"

curl -sSfOL "$url"
apt install "./code-server_${VERSION}_amd64.deb"
rm "code-server_${VERSION}_amd64.deb"

append-bash-profile code-server.bash
