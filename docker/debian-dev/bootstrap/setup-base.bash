#! /usr/bin/env bash

set -e

apt-get update
apt-get install -y vim less man curl bash-completion rsync

cat /bootstrap/bash-profile/bash-completion.bash >> /root/.bash_profile
