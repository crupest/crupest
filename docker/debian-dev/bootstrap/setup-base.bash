#! /usr/bin/env bash

set -e

. /bootstrap/func.bash

apt-get update
apt-get install -y vim less man curl bash-completion rsync

append-bash-profile bash-completion.bash
