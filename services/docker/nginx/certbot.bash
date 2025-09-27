#!/usr/bin/bash

set -e

echo "Sleep 5 seconds waiting for nginx to start."
sleep 5s

while true; do
    certbot renew --webroot -w /var/www/certbot --deploy-hook "nginx -s reload"
    echo "Sleep one day before next certbot renew."
    sleep 1d
done
