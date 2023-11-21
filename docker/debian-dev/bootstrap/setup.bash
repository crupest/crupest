#! /usr/bin/env bash

set -e

/bootstrap/apt-source/setup.bash
/bootstrap/setup-base.bash
/bootstrap/setup-dev.bash
/bootstrap/sbuild/setup.bash
