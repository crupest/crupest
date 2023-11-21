#! /usr/bin/env bash

set -e

dpkg --add-architecture arm64
apt-get update

apt-get install -y crossbuild-essential-arm64
