#! /usr/bin/env bash

set -e -o pipefail

# Map uname -m to ttyd's asset suffix.
arch_map() {
  local arch
  arch=$(uname -m)
  case "$arch" in
    x86_64|amd64)  echo "x86_64" ;;
    aarch64|arm64) echo "aarch64" ;;
    armv7l|armhf)  echo "arm" ;;
    i686|i386)     echo "i686" ;;
    *)
      echo "Unsupported architecture: $arch" >&2
      exit 1
      ;;
  esac
}

main() {
  local arch version
  arch=$(arch_map)
  version=$(curl -fsSL "https://api.github.com/repos/tsl0922/ttyd/releases/latest" \
    | grep -o '"tag_name": *"[^"]*"' \
    | grep -o '[0-9.]\+')

  echo "Installing ttyd v${version} for ${arch}..."

  local url="https://github.com/tsl0922/ttyd/releases/download/${version}/ttyd.${arch}"
  local tmpdir
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' EXIT

  curl -fsSL "$url" -o "$tmpdir/ttyd"
  chmod +x "$tmpdir/ttyd"

  sudo install -m 755 "$tmpdir/ttyd" /usr/local/bin/ttyd

  echo "ttyd $(/usr/local/bin/ttyd --version) installed to /usr/local/bin/ttyd"
}

main "$@"
