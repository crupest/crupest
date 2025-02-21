#!/usr/bin/bash

set -e

while true; do
    certbot renew --deploy-hook "nginx -s reload"
    echo -e "\e[33mSleep one day before next certbot renew.\e[39m"
    sleep 1d
done
