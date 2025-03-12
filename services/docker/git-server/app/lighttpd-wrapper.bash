#!/usr/bin/bash

set -e -o pipefail

die() {
  echo "$@" >&2
  exit 1
}

[[ -n "$MY_ROOT_URL" ]] || die "MY_ROOT_URL is not set. It is needed to create clone url of repos."
[[ -f /git/user-info ]] || touch -a /git/user-info || die "Failed to create /git/user-info to save user accounts. Permission problem?"

exec 3>&1
exec 4>&1
exec lighttpd -D -f /app/lighttpd/lighttpd.conf
