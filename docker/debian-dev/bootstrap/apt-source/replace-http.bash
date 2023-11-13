#! /usr/bin/env bash

set -e

apt-get update
apt-get install -y apt-transport-https ca-certificates

sed -i.bak 's/https?/https/' /etc/apt/sources.list
apt-get update

