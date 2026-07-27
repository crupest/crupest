FROM denoland/deno
RUN apt update && apt-get install -y tini certbot unzip curl && rm -rf /var/lib/apt/lists/* && mkdir -p /app/state
COPY --from=deno . /app/deno/
WORKDIR /app/deno
RUN deno install
ADD mail-robots.txt /srv/mail/robots.txt
CMD ["deno", "task", "gateway:start"]
