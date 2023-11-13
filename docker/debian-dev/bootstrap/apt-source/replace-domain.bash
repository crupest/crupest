#! /usr/bin/env bash

set -e

sed -i.bak "s|\(https\?://\)[-_.a-zA-Z0-9]\+/|\\1$1/|" /etc/apt/sources.list
apt-get update

