#! /usr/bin/env bash

set -e

echo "Backup /etc/apt/sources.list to /etc/apt/sources.list.bak."
echo "Replace source domain in /etc/apt/sources.list to $1."
sed -i.bak "s|\(https\?://\)[-_.a-zA-Z0-9]\+/|\\1$1/|" /etc/apt/sources.list
