#!/usr/bin/bash

# shellcheck source=../share/crupest/base.bash
. base.bash

envs=(CRUPEST_DOMAIN)
secrets=(CRUPEST_V2RAY_TOKEN CRUPEST_V2RAY_PATH)
import_docker_secrets v2ray "${secrets[@]}"
import_env ./crupest/base.env "${envs[@]}"
for template in /etc/nginx/conf.d/*.template; do
  instantiate_template "$template" "${envs[@]}" "${secrets[@]}"
done

envs=(CRUPEST_ROOT_URL)
import_env ./crupest/base.env "${envs[@]}"
instantiate_template ./cgitrc CRUPEST_ROOT_URL
check_template_instantiation ./cgitrc
cp ./cgitrc /etc/cgitrc

secrets=(CRUPEST_GIT_SERVER_USERNAME CRUPEST_GIT_SERVER_PASSWORD)
import_docker_secrets git-server "${secrets[@]}"
htpasswd -cb ./user-info "${CRUPEST_GIT_SERVER_USERNAME}" "${CRUPEST_GIT_SERVER_PASSWORD}"

clean_env "${envs[@]}" "${secrets[@]}"

exec 3>&1
lighttpd -D -f /app/git-lighttpd.conf
