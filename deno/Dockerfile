FROM denoland/deno AS build
WORKDIR /app
COPY . .
RUN --mount=type=cache,target=/deno-dir deno install && deno task build

FROM denoland/deno AS gateway
RUN apt-get update && apt-get install -y tini certbot unzip curl && rm -rf /var/lib/apt/lists/* && mkdir -p /app/state
COPY --from=build /app/gateway/out/crupest-gateway /app/
WORKDIR /app
ADD gateway/srv/. /srv/
CMD ["/app/crupest-gateway"]

FROM denoland/deno AS mail-server
RUN apt-get update && apt-get install -y tini ca-certificates curl \
    postfix postfix-pcre \
    dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd dovecot-sieve dovecot-managesieved dovecot-flatcurve dovecot-fts-xapian \
    spamassassin spamc spamd && \
    rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1000 vmail && useradd -u 1000 -g vmail -s /usr/sbin/nologin vmail && \
    install -d -m 0755 /etc/dovecot/sieve
COPY --from=build /app/mail/out/crupest-mail /app/
ADD --chmod=644 mail/scripts/dovecot/. /etc/dovecot/
ADD --chmod=755 mail/scripts/dovecot-seive-bins/. /usr/lib/dovecot/
ADD --chmod=644 mail/scripts/postfix/. /etc/postfix/
ADD --chmod=644 mail/scripts/spamassassin/. /etc/spamassassin/
ADD --chmod=755 mail/scripts/app/main.bash /app/
CMD ["/app/main.bash"]
