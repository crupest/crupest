#! /usr/bin/env bash

set -e -o pipefail

ttyd_args=(
    -W
    -t enableZmodem=true
    -t enableTrzsz=true
    -t enableSixel=true
)

if [[ -n "$CRUPEST_TTYD_BASE_PATH" ]]; then
    ttyd_args+=( -b "$CRUPEST_TTYD_BASE_PATH" )
fi

ttyd "${ttyd_args[@]}" bash -l