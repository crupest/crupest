#! /usr/bin/env bash

set -e

export DEBIAN_FRONTEND=noninteractive

/bootstrap/apt-source/setup.bash
/bootstrap/setup-base.bash
/bootstrap/setup-dev.bash

. /bootstrap/func.bash

if is_true "$SETUP_SBUILD"; then
    echo "Setup sbuild..."
    /bootstrap/sbuild/setup.bash
else
    echo "Sbuild is disabled. Skipped."
fi

