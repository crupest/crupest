FROM debian AS build-www
ADD install-hugo.bash build-www.bash /app/
COPY --from=www . /app/src/
WORKDIR /app
RUN /app/install-hugo.bash
RUN /app/build-www.bash

FROM nginx:mainline
COPY --from=build-www /app/src/public /srv/www
RUN apt update && apt-get install -y tini certbot && rm -rf /var/lib/apt/lists/*
ADD mail-robots.txt /srv/mail/robots.txt
ADD certbot.bash nginx-wrapper.bash /app/
CMD ["/usr/bin/tini", "--", "/app/nginx-wrapper.bash"]
