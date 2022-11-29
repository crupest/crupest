#! /usr/bin/env bash

set -e

VERSION=$(curl -s https://api.github.com/repos/coder/code-server/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')

curl -fOL "https://github.com/coder/code-server/releases/download/v${VERSION}/code-server_${VERSION}_amd64.deb"
dpkg -i "code-server_${VERSION}_amd64.deb"
