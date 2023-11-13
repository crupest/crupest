#! /usr/bin/env bash

set -e

cp /etc/apt/sources.list /etc/apt/sources.list.bak

cp /bootstrap/source-http.txt /etc/apt/sources.list
apt-get update
apt-get install -y apt-transport-https ca-certificates

cp /bootstrap/source-https.txt /etc/apt/sources.list
apt-get update

cp /bootstrap/source-link.txt /etc/crupest-apt-source

