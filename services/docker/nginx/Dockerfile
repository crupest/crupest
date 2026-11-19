FROM node:24-slim AS www-builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=www package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY --from=www . ./
RUN npm run build

FROM nginx:mainline
# Local builds in China can switch apt to a mirror:
#   docker build --build-arg APT_MIRROR=mirrors.tuna.tsinghua.edu.cn ...
ARG APT_MIRROR=""
RUN if [ -n "${APT_MIRROR}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/*; do \
            [ -f "$f" ] || continue; \
            sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g" "$f"; \
        done; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends tini certbot curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=www-builder /app/out /srv/www
COPY nginx.conf /etc/nginx/nginx.conf
ADD mail-robots.txt /srv/mail/robots.txt
ADD nginx-wrapper.bash certbot.bash housekeeping.bash /app/
RUN chmod 0755 /app/*.bash

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/nginx-wrapper.bash"]
