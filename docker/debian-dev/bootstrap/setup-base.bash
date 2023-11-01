#! /usr/bin/env bash

set -e

apt-get install -y vim less man curl bash-completion

cat /bootstrap/bash-profile/bash-completion.bash >> /root/.bash_profile

