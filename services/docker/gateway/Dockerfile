FROM ghcr.io/gohugoio/hugo AS build-www
COPY --from=www . /project/
RUN ls && hugo

FROM denoland/deno AS deno-build
COPY --from=deno . /workdir/
WORKDIR /workdir
RUN deno install
RUN deno task compile:gateway

FROM debian
RUN apt update && apt-get install -y tini certbot unzip curl && rm -rf /var/lib/apt/lists/* && mkdir -p /app/state
ADD mail-robots.txt /srv/mail/robots.txt
COPY --from=build-www /project/public /srv/www
COPY --from=deno-build /workdir/gateway/out/crupest-gateway /app/
CMD ["/usr/bin/tini", "--", "/app/crupest-gateway"]
