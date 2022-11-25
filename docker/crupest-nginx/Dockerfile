FROM node:latest AS build
RUN npm install -g pnpm
COPY sites/www /sites/www
WORKDIR /sites/www
RUN pnpm install --frozen-lockfile && pnpm run build

FROM nginx:latest
COPY --from=build /sites/www/dist /srv/www
