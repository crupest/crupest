FROM golang:alpine AS build-hugo
ARG CRUPEST_BLOG_UPDATE_INTERVAL=1d
RUN apk add --no-cache build-base coreutils tini bash git
RUN CGO_ENABLED=1 go install --tags extended github.com/gohugoio/hugo@latest && hugo version
ENV CRUPEST_BLOG_UPDATE_INTERVAL=${CRUPEST_BLOG_UPDATE_INTERVAL}
COPY daemon.bash update.bash /scripts/
VOLUME [ "/public" ]
ENTRYPOINT ["/sbin/tini", "--"]
CMD [ "/scripts/daemon.bash" ]
