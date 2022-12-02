FROM golang:alpine AS builder
RUN go install -tags extended github.com/gohugoio/hugo@latest && /root/go/hugo version

FROM alpine:latest
ARG CRUPEST_BLOG_UPDATE_INTERVAL=1d
ENV CRUPEST_BLOG_UPDATE_INTERVAL=${CRUPEST_BLOG_UPDATE_INTERVAL}
COPY --from=builder /root/go/hugo /usr/bin
RUN hugo version
COPY daemon.bash update.bash /scripts/
RUN apk add --no-cache coreutils tini bash git
VOLUME [ "/public" ]
ENTRYPOINT ["/sbin/tini", "--"]
CMD [ "/daemon.bash" ]
