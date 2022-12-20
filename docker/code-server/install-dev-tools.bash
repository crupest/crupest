#! /usr/bin/env bash

set -e

apt-get update
apt-get install vim wget git

git config --global user.email "$GIT_EMAIL"
git config --global user.name "$GIT_NAME"

wget https://packages.microsoft.com/config/debian/11/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

apt-get install dotnet-sdk-7.0

rm -rf /var/lib/apt/lists/*
