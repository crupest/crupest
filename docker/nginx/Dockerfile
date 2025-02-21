FROM node:lts AS build-www
RUN npm install -g pnpm
COPY sites/www /sites/www
WORKDIR /sites/www
RUN pnpm install --frozen-lockfile && pnpm run build

FROM nginx:mainline
RUN apt update && apt-get install -y tini certbot && rm -rf /var/lib/apt/lists/*
COPY --from=build-www /sites/www/dist /srv/www
ADD sites/www/favicon.ico /srv/www/favicon.ico
COPY --from=share * /app/
ADD --chmod=755 certbot.bash nginx-wrapper.bash /app/
ADD nginx-conf/* /etc/nginx/
WORKDIR /app
CMD ["/usr/bin/tini", "--", "/app/nginx-wrapper.bash"]
