#! /usr/bin/env bash

set -e

export DEBIAN_FRONTEND=noninteractive

. /bootstrap/func.bash

/bootstrap/apt-source/setup.bash

apt-get update

/bootstrap/setup-user.bash
/bootstrap/setup-base.bash
/bootstrap/setup-dev.bash

if is_true "$SETUP_CODE_SERVER"; then
    /bootstrap/setup-code-server.bash
fi


rm -rf /var/lib/apt/lists/*
