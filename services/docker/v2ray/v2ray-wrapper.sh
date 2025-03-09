#!/bin/sh

set -e

die() {
  echo "$@" >&2
  exit 1
}

[ -n "$CRUPEST_V2RAY_TOKEN" ] || die "CRUPEST_V2RAY_TOKEN is not set. It is used as password of v2ray tunnel."
[ -n "$CRUPEST_V2RAY_PATH" ] || die "CRUPEST_V2RAY_PATH is not set. It is used as the http endpoint."

sed -e "s|@@CRUPEST_V2RAY_TOKEN@@|$CRUPEST_V2RAY_TOKEN|" \
    -e "s|@@CRUPEST_V2RAY_PATH@@|$CRUPEST_V2RAY_PATH|" \
    "/app/config.json.template" > /app/config.json

exec /usr/bin/v2ray run -c /app/config.json
