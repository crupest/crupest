#!/usr/bin/env bash
set -uo pipefail

# Give nginx time to bind its ports before the first attempt.
sleep 10

while true; do
    # Renewal failures must not kill the container; retry on the next tick.
    certbot renew --quiet --webroot -w /var/www/certbot \
        --deploy-hook "nginx -s reload" \
        || echo "certbot renew failed, will retry later" >&2
    sleep 1d
done
