#!/usr/bin/bash

set -e

# shellcheck source=../share/crupest/base.bash
. base.bash

envs=(CRUPEST_DOMAIN)
secrets=(CRUPEST_V2RAY_TOKEN CRUPEST_V2RAY_PATH)
import_docker_secrets v2ray "${secrets[@]}"
import_env ./crupest/base.env "${envs[@]}"
for template in /etc/nginx/conf.d/*.template; do
  instantiate_template "$template" "${envs[@]}" "${secrets[@]}"
done
clean_env "${secrets[@]}"

/app/certbot.bash &

nginx "-g" "daemon off;"
