#!/usr/bin/bash

set -e

while true; do
    certbot renew --deploy-hook "nginx -s reload"
    echo "Sleep one day before next certbot renew."
    sleep 1d
done
