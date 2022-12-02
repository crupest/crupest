#! /usr/bin/env bash

set -e

VERSION=$(curl -s https://api.github.com/repos/gohugoio/hugo/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
url="https://github.com/gohugoio/hugo/releases/download/v${VERSION}/hugo_extended_${VERSION}_linux-amd64.tar.gz"
curl -fL -o /root/hugo.tar.gz "${url}"
tar -xzf /root/hugo.tar.gz -C /usr/bin hugo

hugo version
