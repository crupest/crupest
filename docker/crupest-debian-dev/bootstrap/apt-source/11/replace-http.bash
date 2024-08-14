#! /usr/bin/env bash

set -e

echo "Backup /etc/apt/sources.list to /etc/apt/sources.list.bak."
echo "Replace http to https in /etc/apt/sources.list."
sed -i.bak 's/https\?/https/' /etc/apt/sources.list
