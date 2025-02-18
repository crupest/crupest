FROM node:lts AS build-www
RUN npm install -g pnpm
COPY sites/www /sites/www
WORKDIR /sites/www
RUN pnpm install --frozen-lockfile && pnpm run build

FROM nginx:mainline
COPY --from=build-www /sites/www/dist /srv/www
ADD sites/www/favicon.ico /srv/www/favicon.ico
