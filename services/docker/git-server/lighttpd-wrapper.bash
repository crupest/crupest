#!/usr/bin/bash

set -e

touch -a /git/private/user-info

exec 3>&1
exec lighttpd -D -f /app/git-lighttpd.conf
