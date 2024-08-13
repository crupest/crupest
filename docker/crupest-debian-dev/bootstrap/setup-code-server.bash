#! /usr/bin/env bash

set -e

. /bootstrap/func.bash

echo "Setting up code server..."

echo "Get latest version of code-server..."
VERSION=$(curl -s https://api.github.com/repos/coder/code-server/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
echo "Current latest version of code-server is $VERSION"

echo "Downloading code-server..."
url="https://github.com/coder/code-server/releases/download/v${VERSION}/code-server_${VERSION}_amd64.deb"
curl -sSfOL "$url"
echo "Downloading code-server done."

echo "Installing code-server..."
apt-get install -y "./code-server_${VERSION}_amd64.deb"
echo "Installing code-server done."

echo "Cleaning up deb..."
rm "code-server_${VERSION}_amd64.deb"
echo "Cleaning up deb done."

append-bash-profile code-server.bash

echo "Setting up code server done."
