#! /usr/bin/env bash

set -e

apt-get install vim less man bash-completion

cat /bootstrap/bash-profile-bash-completion.bash > /root/.bash_profile

