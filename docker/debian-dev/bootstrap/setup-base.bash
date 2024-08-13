#! /usr/bin/env bash

set -e

. /bootstrap/func.bash

apt-get install -y locales vim less man bash-completion rsync curl wget

localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

append-bash-profile bash-completion.bash
