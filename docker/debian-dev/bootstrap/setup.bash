#! /usr/bin/env bash

set -e

/bootstrap/apt-source/setup.bash
/bootstrap/setup-base.bash
/bootstrap/setup-dev-tools.bash
/bootstrap/sbuild/setup-sbuild.bash

rm -rf /var/lib/apt/lists/*
