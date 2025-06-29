#! /usr/bin/env bash

set -e -o pipefail

base_dir="$(dirname "$0")"
dot_files=("bashrc" "quiltrc-dpkg")

for file in "${dot_files[@]}"; do
    echo "copy $base_dir/$file $HOME/.$file"
    cp "$base_dir/$file" "$HOME/.$file"
done
