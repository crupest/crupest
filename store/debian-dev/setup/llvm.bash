#! /usr/bin/env bash

set -e -o pipefail

if [[ -n "$CRUPEST_DEBIAN_DEV_CHINA" ]]; then
    base_url=https://mirrors.tuna.tsinghua.edu.cn/llvm-apt
else
    base_url=https://apt.llvm.org
fi

curl -fsSL "$base_url/llvm.sh" | sh -s -- all -m "$base_url"
