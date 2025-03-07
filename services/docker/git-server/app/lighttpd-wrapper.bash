#!/usr/bin/bash

set -e

[[ -f /git/user-info ]] || touch -a /git/user-info

exec 3>&1
exec 4>&1
exec lighttpd -D -f /app/lighttpd/lighttpd.conf
