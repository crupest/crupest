#!/bin/sh

set -e

die() {
  echo "$@" >&2
  exit 1
}

[ -n "$MY_V2RAY_TOKEN" ] || die "MY_V2RAY_TOKEN is not set. It is used as password of v2ray tunnel."
[ -n "$MY_V2RAY_PATH" ] || die "MY_V2RAY_PATH is not set. It is used as the http endpoint."

sed -e "s|@@MY_V2RAY_TOKEN@@|$MY_V2RAY_TOKEN|" \
    -e "s|@@MY_V2RAY_PATH@@|$MY_V2RAY_PATH|" \
    "/app/config.json.template" > /app/config.json

exec /usr/bin/v2ray run -c /app/config.json
