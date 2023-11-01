#! /usr/bin/env bash

set -e

cp /etc/apt/sources.list /etc/apt/sources.list.bak

cp /bootstrap/tuna-source-http.txt /etc/apt/sources.list
apt-get update
apt-get install -y apt-transport-https ca-certificates

cp /bootstrap/tuna-source-https.txt /etc/apt/sources.list
apt-get update

