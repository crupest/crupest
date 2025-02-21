#!/usr/bin/bash

set -e

# shellcheck source=../share/crupest/base.bash
. base.bash

my_config="my-config.json"
secrets=(CRUPEST_V2RAY_TOKEN CRUPEST_V2RAY_PATH)
import_docker_secrets v2ray "${secrets[@]}"
file_replace_vars "$my_config" "${secrets[@]}"
clean_env "${secrets[@]}"
check_template_instantiation "$my_config"

if ./crupest/download-github-release.bash "v2fly/v2ray-core" "v2ray-linux-64.zip"; then
  unzip crupest/v2ray-linux-64.zip || die "Failed to unzip!"
  chmod +x ./v2ray
else
  note "Failed to download, try to use a installed one."
fi

[[ -f ./v2ray ]] || die "v2ray failed to download and there is no installed one!"

./v2ray -version

V2RAY_LOCATION_ASSET="$(pwd)"
export V2RAY_LOCATION_ASSET
exec ./v2ray run -c "$(pwd)/my-config.json"
