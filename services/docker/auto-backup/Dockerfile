FROM debian
RUN apt-get update && apt-get install -y \
    tini ca-certificates coreutils bash tar zstd \
    && rm -rf /var/lib/apt/lists/*

ENV CRUPEST_AUTO_BACKUP_INIT_DELAY=
ENV CRUPEST_AUTO_BACKUP_INTERVAL=1d

ADD --chmod=755 https://github.com/tencentyun/coscli/releases/download/v1.0.3/coscli-v1.0.3-linux-amd64 /app/coscli
ADD --chmod=755 daemon.bash /app/

VOLUME [ "/data" ]

CMD [ "tini", "--", "/app/daemon.bash" ]
