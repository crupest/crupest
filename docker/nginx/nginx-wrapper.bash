#!/usr/bin/bash

set -e

/app/certbot.bash &

nginx "-g" "daemon off;"
