#!/bin/bash
set -euo pipefail

INSTALL_DIR="/app"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

echo "Fetching latest dufs release info..."
API_URL="https://api.github.com/repos/sigoden/dufs/releases/latest"
RELEASE_JSON=$(curl -fsSL "$API_URL")

VERSION=$(echo "$RELEASE_JSON" | grep -o '"tag_name": "[^"]*"' | head -1 | sed 's/.*: "\(.*\)"/\1/')
echo "Latest version: $VERSION"

DOWNLOAD_URL=$(echo "$RELEASE_JSON" | grep -o '"browser_download_url": "[^"]*x86_64-unknown-linux-musl[^"]*"' | head -1 | sed 's/.*: "\(.*\)"/\1/')
if [ -z "$DOWNLOAD_URL" ]; then
    echo "Error: Could not find x86_64-unknown-linux-musl asset" >&2
    exit 1
fi

echo "Downloading: $DOWNLOAD_URL"
curl -fsSL "$DOWNLOAD_URL" -o "$TMPDIR/dufs.tar.gz"

echo "Extracting to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
tar -xzf "$TMPDIR/dufs.tar.gz" -C "$INSTALL_DIR"

echo "dufs $VERSION installed to $INSTALL_DIR"
"$INSTALL_DIR/dufs" --version
