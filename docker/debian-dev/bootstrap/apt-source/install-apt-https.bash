#! /usr/bin/env bash

set -e

echo "Install apt https transport."
apt-get update
apt-get install -y apt-transport-https ca-certificates
