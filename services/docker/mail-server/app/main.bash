#!/usr/bin/bash

set -e -o pipefail

die() {
  echo "$@" >&2
  exit 1
}

# TODO: restore this.
# /app/crupest-mail serve --real &

/dovecot/sbin/dovecot -F
