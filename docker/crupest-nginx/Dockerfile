FROM node:latest AS build-www
RUN npm install -g pnpm
COPY sites/www /sites/www
WORKDIR /sites/www
RUN pnpm install --frozen-lockfile && pnpm run build

FROM klakegg/hugo:ext-alpine AS build-blog
# install git
RUN apk add --no-cache git
RUN git submodule update --init --recursive
COPY sites/blog /hugo
WORKDIR /hugo
RUN hugo

FROM nginx:latest
COPY --from=build-www /sites/www/dist /srv/www
COPY --from=build-blog /hugo/public /srv/blog
