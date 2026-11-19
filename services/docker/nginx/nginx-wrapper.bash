#!/usr/bin/env bash
set -euo pipefail

# The log directory is a bind mount and may be created by Docker as root:root.
# Make it writable for the nginx worker user before nginx opens its logs.
mkdir -p /var/log/nginx
chown -R nginx:nginx /var/log/nginx 2>/dev/null || true

/app/certbot.bash &
/app/housekeeping.bash &

# Run the official nginx entrypoint scripts (IPv6 check, envsubst, worker
# tuning) and then nginx itself. Worker autotuning stays off on purpose:
# nginx.conf pins one worker so that upstream max_conns is a global limit.
exec /docker-entrypoint.sh nginx -g "daemon off;"
