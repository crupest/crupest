#! /usr/bin/env bash

/bootstrap/sbuild/setup-sbuild-base.bash

if [[ "$BUILD_FOR_ARCH" == "amd64" ]]; then
    /bootstrap/sbuild/setup-sbuild-amd64.bash
fi

if [[ "$BUILD_FOR_ARCH" == "arm64" ]]; then
    /bootstrap/sbuild/setup-sbuild-arm64.bash
fi
