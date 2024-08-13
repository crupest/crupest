#! /usr/bin/env bash

set -e

export DEBIAN_FRONTEND=noninteractive

echo "Setting up crupest-debian-dev..."

. /bootstrap/func.bash

/bootstrap/apt-source/setup.bash

echo "Updating apt source index..."
apt-get update
echo "Updating apt source index done."

/bootstrap/setup-user.bash
/bootstrap/setup-base.bash
/bootstrap/setup-dev.bash

if is_true "$CRUPEST_DEBIAN_DEV_SETUP_CODE_SERVER"; then
    echo "CRUPEST_DEBIAN_DEV_SETUP_CODE_SERVER is true, setting up code-server..."
    /bootstrap/setup-code-server.bash
fi

echo "Cleaning up apt source index..."
rm -rf /var/lib/apt/lists/*
echo "Cleaning up apt source index done."

echo "Setting up crupest-debian-dev done."
