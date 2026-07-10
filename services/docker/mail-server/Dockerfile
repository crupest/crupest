FROM node:24-bookworm-slim AS builder
RUN apt-get update && apt-get install -y python3 make g++ && \
    rm -rf /var/lib/apt/lists/*
COPY --from=app . /app/
WORKDIR /app
RUN npm ci
RUN npm run build

FROM node:24-bookworm-slim
RUN apt-get update && apt-get install -y tini ca-certificates curl \
    postfix postfix-pcre \
    dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd dovecot-sieve dovecot-managesieved dovecot-flatcurve dovecot-fts-xapian && \
    rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1000 vmail && useradd -u 1000 -g vmail -s /usr/sbin/nologin vmail

COPY --from=builder /app /app
WORKDIR /app

ADD --chmod=644 postfix/* /etc/postfix/
ADD --chmod=644 dovecot.conf /etc/dovecot/dovecot.conf
ADD --chmod=755 app/* /app/
CMD ["tini", "-g", "--", "/app/main.bash"]
