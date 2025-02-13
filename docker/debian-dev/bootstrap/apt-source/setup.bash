#! /usr/bin/env bash
# shellcheck disable=1090,1091

set -e

die() {
  echo "$@" >&2
  exit 1
}

if [[ $EUID -ne 0 ]]; then
    die "This script must be run as root."
fi

os_release_file="/etc/os-release"
if [[ -f "$os_release_file" ]]; then
    debian_version=$(source "$os_release_file"; echo "$VERSION_CODENAME")
    if [[ "$debian_version" != "bullseye|bookworm" ]]; then
        die "This script can only be run on Debian Bullseye or Bookworm. But it is $debian_version"
    fi
else
    die "$os_release_file not found. Failed to get debian version."
fi


apt_check_source() {
    global apt_repo_file
    old_one="/etc/apt/sources.list"
    new_one="/etc/apt/sources.list.d/debian.sources"
    if [[ -f "$old_one" ]]; then
        echo "Found old format apt repo file at $old_one"
        apt_repo_file="$old_one"
    elif [[ -f "new_one" ]]; then
        echo "Found new format apt 
}

apt_change_mirror() {
    apt_check_source
    echo "Change apt mirror to $1."
    sed -i.bak "s|\(https\?://\)[-_.a-zA-Z0-9]\+/|\\1$1/|" /etc/apt/sources.list
}

apt_change_https() {
    apt_check_source
    echo "Change apt to use https."
    sed -i 's|http://|https://|' /etc/apt/sources.list
}

echo "Setting up apt source..."

china_mirror="mirrors.ustc.edu.cn"

if [[ -n $CRUPEST_IN_CHINA ]]; then
    echo "In China, using China source..."
    "$setup_dir/replace-domain.bash" "$(cat "$dir/china-source.txt")"
fi

"$dir/install-apt-https.bash"
"$setup_dir/replace-http.bash"
"$setup_dir/add-deb-src.bash"

echo "Setting up apt source done."
