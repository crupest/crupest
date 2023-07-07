#! /usr/bin/env bash

set -e

apt-get update
apt-get install -y vim lsb-release wget git software-properties-common gnupg
apt-get install -y gcc g++ make gdb

# git config --global user.email "$GIT_EMAIL"
# git config --global user.name "$GIT_NAME"

source ./install-llvm.bash
source ./install-cmake.bash
source ./install-dotnet.bash
