FROM alpine:latest
ARG CRUPEST_BLOG_UPDATE_INTERVAL=1d
ENV CRUPEST_BLOG_UPDATE_INTERVAL=${CRUPEST_BLOG_UPDATE_INTERVAL}
COPY daemon.bash update.bash /scripts/
RUN apk add --no-cache coreutils tini bash git hugo
VOLUME [ "/public" ]
ENTRYPOINT ["/sbin/tini", "--"]
CMD [ "/scripts/daemon.bash" ]
