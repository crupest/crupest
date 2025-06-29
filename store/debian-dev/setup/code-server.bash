#! /usr/bin/env bash

set -e -o pipefail

if [[ $# != 1 ]]; then
    echo "Require exactly one argument, the password of the code server." >&2
    exit 1
fi

curl -fsSL https://code-server.dev/install.sh | sh

apt update && apt install argon2
mkdir -p "${HOME}/.config/code-server"
echo -e "auth: password\nhashed-password: " >> "${HOME}/.config/code-server/config.yaml"
echo -n "$1" | \
    argon2 "$(shuf -i 10000000-99999999 -n 1 --random-source /dev/urandom)" -e \
    >> "${HOME}/.config/code-server/config.yaml"
