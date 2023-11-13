alias cp-no-git="rsync -a --exclude='**/.git'"

alias apt-get-build-dep-arm64="apt-get build-dep -a arm64 --arch-only"
alias apt-get-build-dep-indep="apt-get build-dep --indep-only"
alias dpkg-buildpackage-build="dpkg-buildpackage -j$(nproc) -nc -b"
alias dpkg-buildpackage-clean="dpkg-buildpackage -T clean"
alias dpkg-buildpackage-arm64="CONFIG_SITE=/etc/dpkg-cross/cross-config.arm64 DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -aarm64 -Pcross,nocheck"
alias dpkg-buildpackage-arm64-build="dpkg-buildpackage-arm64 -j$(nproc) -nc -T binary-arch"
alias dpkg-buildpackage-arm64-clean="dpkg-buildpackage-arm64 -T clean"
alias dpkg-buildpackage-indep-build="dpkg-buildpackage -j$(nproc) -nc -T binary-indep"

