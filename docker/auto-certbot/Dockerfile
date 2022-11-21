FROM certbot/certbot:latest
ARG CRUPEST_DOMAIN
ARG CRUPEST_CERTBOT_RENEW_COMMAND
COPY daemon.bash /daemon.bash
CMD [ "/daemon.bash" ]
