FROM golang:alpine AS build-hugo
RUN apk add --no-cache build-base git
RUN CGO_ENABLED=1 go install --tags extended github.com/gohugoio/hugo@latest
RUN /go/bin/hugo version

FROM alpine:latest
COPY --from=build-hugo /go/bin/hugo /usr/bin/
# check hugo
RUN hugo version
ARG CRUPEST_BLOG_UPDATE_INTERVAL=1d
ENV CRUPEST_BLOG_UPDATE_INTERVAL=${CRUPEST_BLOG_UPDATE_INTERVAL}
COPY daemon.bash update.bash /scripts/
RUN apk add --no-cache coreutils tini bash git
VOLUME [ "/public" ]
ENTRYPOINT ["/sbin/tini", "--"]
CMD [ "/scripts/daemon.bash" ]
