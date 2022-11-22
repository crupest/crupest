FROM certbot/certbot:latest
ARG CRUPEST_DOMAIN
ARG CRUPEST_CERTBOT_RENEW_COMMAND=""
# install bash
RUN apk add --no-cache bash
COPY daemon.bash /daemon.bash
VOLUME ["/var/www/certbot", "/etc/letsencrypt", "/var/lib/letsencrypt"]
ENTRYPOINT [ "/daemon.bash" ]
