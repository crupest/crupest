FROM alpine:latest
ARG CRUPEST_BLOG_UPDATE_INTERVAL=1d
ENV CRUPEST_BLOG_UPDATE_INTERVAL=${CRUPEST_BLOG_UPDATE_INTERVAL}
COPY install-hugo.bash daemon.bash update.bash /scripts/
RUN apk add --no-cache coreutils gzip tar tini curl bash git && /scripts/install-hugo.bash
VOLUME [ "/public" ]
ENTRYPOINT ["/sbin/tini", "--"]
CMD [ "/daemon.bash" ]
