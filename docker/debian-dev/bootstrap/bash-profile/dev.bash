alias apt-get-dep-build-arm64="apt-get build-dep -aarm64 --arch-only"
alias dpkg-buildpackage-arm64="CONFIG_SITE=/etc/dpkg-cross/cross-config.arm64  DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -aarm64 -Pcross,nocheck"
