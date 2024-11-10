#! /usr/bin/env bash

set -e

echo "Backup /etc/apt/sources.list to /etc/apt/sources.list.d/debian.sources.bak."
echo "Replace http to https in /etc/apt/sources.list.d/debian.sources."
sed -i.bak -E "s|(URIs:\\s*)https?(://[-_.a-zA-Z0-9]+/.*)|\\1https\\2|" /etc/apt/sources.list.d/debian.sources
