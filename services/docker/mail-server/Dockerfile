FROM denoland/deno
RUN apt-get update && apt-get install -y tini ca-certificates curl \
    postfix postfix-pcre \
    dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd dovecot-sieve dovecot-managesieved dovecot-flatcurve dovecot-fts-xapian && \
    rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1000 vmail && useradd -u 1000 -g vmail -s /usr/sbin/nologin vmail

COPY --from=deno . /app/deno/
WORKDIR /app/deno
RUN deno install

ADD --chmod=644 postfix/* /etc/postfix/
ADD --chmod=644 dovecot.conf /etc/dovecot/dovecot.conf
ADD app/* /app/
CMD ["tini", "--", "/app/main.bash"]
