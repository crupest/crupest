#!/usr/bin/bash

set -e -o pipefail

die() {
  echo "$@" >&2
  exit 1
}

/app/certbot.bash &

/docker-entrypoint.sh nginx "-g" "daemon off;"
