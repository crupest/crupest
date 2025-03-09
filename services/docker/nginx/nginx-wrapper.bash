#!/usr/bin/bash

set -e -o pipefail

die() {
  echo "$@" >&2
  exit 1
}

[[ -n "$CRUPEST_DOMAIN" ]] || die "CRUPEST_DOMAIN is not set. It is used as root domain."
[[ -n "$CRUPEST_GITHUB" ]] || die "CRUPEST_GITHUB is not set. It is used as GitHub redirection."
[[ -n "$CRUPEST_V2RAY_PATH" ]] || die "CRUPEST_V2RAY_PATH is not set. It is used as v2ray tunnel endpoint."

/app/certbot.bash &

/docker-entrypoint.sh nginx "-g" "daemon off;"
