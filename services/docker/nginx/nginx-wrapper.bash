#!/usr/bin/bash

set -e -o pipefail

die() {
  echo "$@" >&2
  exit 1
}

[[ -n "$MY_DOMAIN" ]] || die "MY_DOMAIN is not set. It is used as root domain."
[[ -n "$MY_GITHUB" ]] || die "MY_GITHUB is not set. It is used as GitHub redirection."
[[ -n "$MY_V2RAY_PATH" ]] || die "MY_V2RAY_PATH is not set. It is used as v2ray tunnel endpoint."

/app/certbot.bash &

/docker-entrypoint.sh nginx "-g" "daemon off;"
