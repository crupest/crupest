#! /usr/bin/env bash

set -e

echo "Backup /etc/apt/sources.list.d/debian.sources to /etc/apt/sources.list.d/debian.sources.bak."
echo "Replace source domain in /etc/apt/sources.list.d/debian.sources to $1."
sed -i.bak -E "s|(URIs:\\s*https?://)[-_.a-zA-Z0-9]+(/.*)|\\1$1\\2|" /etc/apt/sources.list.d/debian.sources
