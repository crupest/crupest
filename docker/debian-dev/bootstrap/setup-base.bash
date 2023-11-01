#! /usr/bin/env bash

set -e

apt-get install -y vim less man curl bash-completion rsync

cat /bootstrap/bash-profile/bash-completion.bash >> /root/.bash_profile
cat /bootstrap/bash-profile/cp-no-git.bash >> /root/.bash_profile

