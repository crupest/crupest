#! /usr/bin/env bash

set -e

if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" = "debian" ]; then
        echo "$VERSION_ID"
        exit 0
    fi
fi

exit 1
