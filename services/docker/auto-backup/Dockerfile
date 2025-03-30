FROM debian
RUN apt-get update && apt-get install -y \
    tini ca-certificates coreutils tar zstd rclone \
    && rm -rf /var/lib/apt/lists/*

ENV CRUPEST_AUTO_BACKUP_INIT_DELAY=
ENV CRUPEST_AUTO_BACKUP_INTERVAL=1d

ADD daemon.bash rclone.conf /app/

VOLUME [ "/data" ]

CMD [ "tini", "--", "/app/daemon.bash" ]
