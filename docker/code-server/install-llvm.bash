LLVM_VERSION=15
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
./llvm.sh $LLVM_VERSION all
rm llvm.sh
update-alternatives --install /usr/bin/clang clang /usr/bin/clang-$LLVM_VERSION 100 \
    --slave /usr/bin/clang++ clang++ /usr/bin/clang++-$LLVM_VERSION \
    --slave /usr/bin/clangd clangd /usr/bin/clangd-$LLVM_VERSION \
    --slave /usr/bin/lldb lldb /usr/bin/lldb-$LLVM_VERSION \
    --slave /usr/bin/lld lld /usr/bin/lld-$LLVM_VERSION
