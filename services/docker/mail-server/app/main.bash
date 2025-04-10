#!/usr/bin/bash

set -e -o pipefail

die() {
  echo "$@" >&2
  exit 1
}

/app/crupest-relay init || die "crupest-relay failed to init."

/app/crupest-relay real-serve &
/dovecot/sbin/dovecot -F
