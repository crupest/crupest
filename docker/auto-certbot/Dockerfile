FROM certbot/certbot:latest

ARG CRUPEST_AUTO_CERTBOT_ADDITIONAL_PACKAGES=""
RUN apk add --no-cache tini coreutils bash ${CRUPEST_AUTO_CERTBOT_ADDITIONAL_PACKAGES} && python -m pip install cryptography


ARG CRUPEST_DOMAIN
ARG CRUPEST_ADDITIONAL_DOMAIN_LIST=""
ARG CRUPEST_EMAIL
ARG CRUPEST_AUTO_CERTBOT_POST_HOOK=""
# install bash
ENV CRUPEST_DOMAIN=${CRUPEST_DOMAIN}
ENV CRUPEST_ADDITIONAL_DOMAIN_LIST=${CRUPEST_ADDITIONAL_DOMAIN_LIST}
ENV CRUPEST_EMAIL=${CRUPEST_EMAIL}
ENV CRUPEST_AUTO_CERTBOT_POST_HOOK=${CRUPEST_AUTO_CERTBOT_POST_HOOK}
COPY daemon.bash /daemon.bash
COPY get-cert-domains.py /get-cert-domains.py
VOLUME ["/var/www/certbot", "/etc/letsencrypt", "/var/lib/letsencrypt"]
ENTRYPOINT ["tini", "--"]
CMD [ "/daemon.bash" ]
