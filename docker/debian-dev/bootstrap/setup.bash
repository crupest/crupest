#! /usr/bin/env bash

set -e

is_true() {
    if [[ "$1" =~ 1|on|true ]]; then
        return 0
    else
        return 1
    fi
}

if [ ! -v CRUPEST_DEV ]; then
    echo "CRUPEST_DEV is not set, defaulting to 1."
    CRUPEST_DEV=1
elif is_true $CRUPEST_DEV; then
    echo "CRUPEST_DEV is set to true."
else
    echo "CRUPEST_DEV is set to false."
fi

echo "Begin to setup debian..."

if [ -t 1 ]; then
    echo "Looks like we are in a non-interactive environment. Setting DEBIAN_FRONTEND to noninteractive."
    export DEBIAN_FRONTEND=noninteractive
fi

append-bash-profile() {
    cat "/bootstrap/bash/$1" >> /home/$CRUPEST_DEBIAN_DEV_USER/.bash_profile
}

append-bashrc() {
    cat "/bootstrap/bash/$1" >> /home/$CRUPEST_DEBIAN_DEV_USER/.bashrc
}

copy-home-dot-file() {
    cp "/bootstrap/home-dot/$1" "/home/$CRUPEST_DEBIAN_DEV_USER/.$1"
}

/bootstrap/apt-source/setup.bash

echo "Updating apt source index..."
apt-get update
echo "Updating apt source index done."

/bootstrap/setup-user.bash
/bootstrap/setup-base.bash
/bootstrap/setup-dev.bash

if is_true "$CRUPEST_FOR_DEV"; then
    echo "CRUPEST_FOR_DEV is true, setting up dev environment..."
    /bootstrap/setup-dev.bash
fi

if is_true "$CRUPEST_DEBIAN_DEV_SETUP_CODE_SERVER"; then
    echo "CRUPEST_DEBIAN_DEV_SETUP_CODE_SERVER is true, setting up code-server..."
    /bootstrap/setup-code-server.bash
fi

echo "Cleaning up apt source index..."
rm -rf /var/lib/apt/lists/*
echo "Cleaning up apt source index done."

echo "Setting up crupest-debian-dev done."
