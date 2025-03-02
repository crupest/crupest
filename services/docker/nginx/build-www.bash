#! /usr/bin/env bash

set -e -o pipefail

die() {
  echo -e "\033[31mError: " "$@" "\033[0m" >&2
  exit 1
}

note() {
  echo -e "\033[33mNote: " "$@" "\033[0m"
}

success() {
  echo -e "\033[32mSuccess: " "$@" "\033[0m"
}

apt-get update
apt-get install -y locales curl tar xz-utils
localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

www_dir="/app/www"
mkdir -p "$www_dir"

download_github_release() {
  local repo="$1"
  local artifact="$2"
  local output="$3"
  local version url

  note "Downloading release artifact $artifact of $repo to $output from GitHub..."
  version=$(curl -s https://api.github.com/repos/$repo/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
  echo "The latest version of $repo is $version."
  artifact="${artifact//VERSION/$version}"
  url="https://github.com/$repo/releases/download/v${version}/$artifact"
  curl -fL -o "$output" "$url"
  success "Downloaded successfully."
}

install_hugo() {
  note "Installing Hugo..."
  download_github_release "gohugoio/hugo" "hugo_extended_VERSION_linux-amd64.deb" "hugo_extended.deb"
  dpkg -i "hugo_extended.deb"
  rm "hugo_extended.deb"
  hugo version
  success "Hugo installed successfully."
}

build_www() {
  note "Begin to build hugo site..."
  cd /app/src/
  ls -l .
  [[ ! -d public ]] || rm -rf public
  hugo -d "$www_dir"
  success "Build hugo site successfully."
}

install_cppreference() {
  note "Installing cppreference..."
  download_github_release "PeterFeicht/cppreference-doc" "html-book-VERSION.tar.xz" "cppreference.tar.xz"
  local dir="$www_dir/ref/c"
  mkdir -p "$dir"
  tar -C -xJf "cppreference-${version}.tar.gz"
  success "Install cppreference successfully."
}