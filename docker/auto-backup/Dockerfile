FROM alpine:latest AS coscli-downloader
RUN apk add --no-cache bash curl jq
COPY install-coscli.bash /install-coscli.bash
RUN /install-coscli.bash

FROM alpine:latest
RUN apk add --no-cache coreutils bash tar xz yq
ARG CRUPEST_AUTO_BACKUP_INIT_DELAY=0
ARG CRUPEST_AUTO_BACKUP_INTERVAL=1d
ENV CRUPEST_AUTO_BACKUP_INIT_DELAY=${CRUPEST_AUTO_BACKUP_INIT_DELAY}
ENV CRUPEST_AUTO_BACKUP_INTERVAL=${CRUPEST_AUTO_BACKUP_INTERVAL}
COPY --from=coscli-downloader /coscli /coscli
COPY daemon.bash /daemon.bash
VOLUME [ "/data", "/root/.cos.yaml" ]
ENTRYPOINT [ "/daemon.bash" ]
