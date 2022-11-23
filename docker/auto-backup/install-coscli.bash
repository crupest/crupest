#!/usr/bin/env bash

set -e

# Check I'm root.
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

download_url=$(curl -s https://api.github.com/repos/tencentyun/coscli/releases/latest | jq -r ".assets[] | select(.name | test(\"coscli-linux\")) | .browser_download_url")

curl -L -o /coscli "$download_url"

chmod +x /coscli

/coscli --version
