#! /usr/bin/env bash

set -e

sed "s|.*https\?://\([-_.a-zA-Z0-9]\+\)/.*|\\1|;q" /etc/apt/sources.list
