#! /usr/bin/env bash

set -e -o pipefail

CMAKE_VERSION=$(curl -s https://api.github.com/repos/Kitware/CMake/releases/latest | \
    grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')

curl -fsSL "https://github.com/Kitware/CMake/releases/download/v$CMAKE_VERSION/cmake-$CMAKE_VERSION-linux-x86_64.sh" | \
    sh -s -- --skip-license --prefix=/usr
