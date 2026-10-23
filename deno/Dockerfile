FROM node:24-slim AS www-builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=www package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY --from=www . ./
RUN npm run build

FROM denoland/deno AS build
WORKDIR /app
COPY . .
RUN --mount=type=cache,target=/deno-dir deno install && deno task build

FROM denoland/deno AS gateway
# Local builds in China can switch apt to a mirror:
#   docker build --build-arg APT_MIRROR=mirrors.tuna.tsinghua.edu.cn ...
ARG APT_MIRROR=""
RUN if [ -n "${APT_MIRROR}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do \
            [ -f "$f" ] || continue; \
            sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g; s|archive.ubuntu.com|${APT_MIRROR}|g; s|security.ubuntu.com|${APT_MIRROR}|g" "$f"; \
        done; \
    fi \
    && apt-get update && apt-get install -y tini certbot unzip curl && rm -rf /var/lib/apt/lists/* && mkdir -p /app/state
COPY --from=build /app/gateway/out/crupest-gateway /app/
COPY --from=www-builder /app/out /srv/www
WORKDIR /app
ADD gateway/srv/. /srv/
CMD ["/app/crupest-gateway"]

FROM denoland/deno AS mail-server
# Local builds in China can switch apt to a mirror; empty keeps deb.debian.org.
ARG APT_MIRROR=""
RUN if [ -n "${APT_MIRROR}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do \
            [ -f "$f" ] || continue; \
            sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g; s|archive.ubuntu.com|${APT_MIRROR}|g; s|security.ubuntu.com|${APT_MIRROR}|g" "$f"; \
        done; \
    fi \
    && apt-get update && apt-get install -y tini ca-certificates curl \
    postfix postfix-pcre \
    dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd dovecot-sieve dovecot-managesieved dovecot-flatcurve dovecot-fts-xapian \
    spamassassin spamc spamd && \
    rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1000 vmail && useradd -u 1000 -g vmail -s /usr/sbin/nologin vmail
COPY --from=build /app/mail/out/crupest-mail /app/
ADD --chmod=u=rwX,go=rX mail/scripts/dovecot/. /etc/dovecot/
ADD --chmod=u=rwx,go=rx mail/scripts/dovecot-seive-bins/. /usr/lib/dovecot/
ADD --chmod=u=rwX,go=rX mail/scripts/postfix/. /etc/postfix/
ADD --chmod=u=rwX,go=rX mail/scripts/spamassassin/. /etc/spamassassin/
ADD --chmod=u=rwx,go=rx mail/scripts/app/. /app/
CMD ["/app/main.bash"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["/app/healthcheck.bash"]
