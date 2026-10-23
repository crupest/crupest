FROM debian
# Local builds in China can switch apt to a mirror:
#   docker build --build-arg APT_MIRROR=mirrors.tuna.tsinghua.edu.cn ...
# Leave empty for the default (production) mirrors.
ARG APT_MIRROR=""
RUN if [ -n "${APT_MIRROR}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do \
            [ -f "$f" ] || continue; \
            sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g; s|archive.ubuntu.com|${APT_MIRROR}|g; s|security.ubuntu.com|${APT_MIRROR}|g" "$f"; \
        done; \
    fi \
    && apt-get update && apt-get install -y \
    tini ca-certificates coreutils tar zstd rclone \
    && rm -rf /var/lib/apt/lists/*

ENV CRUPEST_AUTO_BACKUP_INIT_DELAY=
ENV CRUPEST_AUTO_BACKUP_INTERVAL=1d

ADD daemon.bash rclone.conf exclude.txt /app/

VOLUME [ "/data" ]

CMD [ "tini", "--", "/app/daemon.bash" ]
