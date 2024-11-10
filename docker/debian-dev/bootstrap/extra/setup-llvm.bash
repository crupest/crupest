#! /usr/bin/env bash

set -e

LLVM_VERSION=18

. /bootstrap/func.bash

if is_true "$CRUPEST_DEBIAN_DEV_IN_CHINA"; then
    base_url=https://mirrors.tuna.tsinghua.edu.cn/llvm-apt
else
    base_url=https://apt.llvm.org
fi

wget "$base_url/llvm.sh"
chmod +x llvm.sh
./llvm.sh $LLVM_VERSION all -m "$base_url"
rm llvm.sh

update-alternatives --install /usr/bin/clang clang /usr/bin/clang-$LLVM_VERSION 100 \
    --slave /usr/bin/clang++ clang++ /usr/bin/clang++-$LLVM_VERSION \
    --slave /usr/bin/clangd clangd /usr/bin/clangd-$LLVM_VERSION \
    --slave /usr/bin/clang-format clang-format /usr/bin/clang-format-$LLVM_VERSION \
    --slave /usr/bin/clang-tidy clang-tidy /usr/bin/clang-tidy-$LLVM_VERSION \
    --slave /usr/bin/lldb lldb /usr/bin/lldb-$LLVM_VERSION \
    --slave /usr/bin/lld lld /usr/bin/lld-$LLVM_VERSION
