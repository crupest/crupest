#!/usr/bin/bash

set -e
set -o pipefail

script_dir=$(dirname "$0")

# shellcheck source=base.bash
. "$script_dir/base.bash"

des_dir="$script_dir"
mkdir -p "$des_dir"
note "Downloading artifacts" "${@:2}" " of latest release in Github repo $1 to $des_dir"

repo="${1//\//.}"
version_url="https://api.github.com/repos/$1/releases/latest"
echo "Get version from $version_url"
version=$(curl "$version_url" |
grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/') || die "Failed to get latest version."
echo "The latest version of $1 is $version, been written to $des_dir/$repo.version"
echo "$version" > "$des_dir/$repo.version"

base_url="https://github.com/$1/releases/download/v${version}/"
for artifact in "${@:2}"; do
  real_name=${artifact//@@VERSION@@/$version}
  url="$base_url$real_name"
  echo "Downloading $artifact from $url ..."
  curl -L -o "$des_dir/$real_name" "$url" || die "Failed to download artifact $artifact."
  echo "$real_name" >> "$des_dir/$repo.list"
done

success "Downloaded artifacts of latest release. File list is saved to $des_dir/$repo.list"
