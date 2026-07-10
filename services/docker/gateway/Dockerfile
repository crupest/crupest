FROM node:24-bookworm-slim AS builder
COPY --from=app . /app/
WORKDIR /app
RUN npm ci
RUN npm run build && npm run www:generate

FROM node:24-bookworm-slim
RUN apt-get update && apt-get install -y tini certbot curl && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /app/state
COPY --from=builder /app /app
COPY --from=builder /app/www/dist /srv/www
ADD mail-robots.txt /srv/mail/robots.txt
WORKDIR /app
CMD ["tini", "--", "node", "gateway/build/main.js"]
