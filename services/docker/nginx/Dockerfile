FROM ghcr.io/gohugoio/hugo AS build-www
COPY --from=www . /project/
RUN ls && hugo

FROM nginx:mainline
RUN apt update && apt-get install -y tini certbot && rm -rf /var/lib/apt/lists/*
ADD mail-robots.txt /srv/mail/robots.txt
ADD certbot.bash nginx-wrapper.bash /app/
COPY configs/. /etc/nginx/
COPY --from=build-www /project/public /srv/www
CMD ["/usr/bin/tini", "--", "/app/nginx-wrapper.bash"]
