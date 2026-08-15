#!/usr/bin/bash

set -e -o pipefail

check() {
  local service="$1"
  shift

  if ! "$@" >/dev/null; then
    echo "Health check failed: $service" >&2
    return 1
  fi
}

check spamassassin /usr/bin/spamc -K
check dovecot /usr/bin/doveadm service status
check postfix /usr/sbin/postfix status
check crupest-mail /usr/bin/curl --fail --silent --show-error --max-time 5 \
  http://127.0.0.1:2345/health
