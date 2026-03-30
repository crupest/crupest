FROM denoland/deno AS deno-build
COPY --from=deno . /workdir/
WORKDIR /workdir
RUN deno install
RUN deno task compile:mail

FROM debian
RUN apt-get update && apt-get install -y tini ca-certificates curl \
    postfix postfix-pcre \
    dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd dovecot-sieve dovecot-managesieved dovecot-flatcurve dovecot-fts-xapian && \
    rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1000 vmail && useradd -u 1000 -g vmail -s /usr/sbin/nologin vmail
COPY --from=deno-build /workdir/mail/out/crupest-mail /app/
COPY --from=generated --chmod=644 postfix-main.cf /etc/postfix/main.cf
ADD --chmod=644 dovecot.conf /etc/dovecot/dovecot.conf
ADD --chmod=644 postfix-master.cf /etc/postfix/master.cf
ADD app/* /app/
CMD ["tini", "--", "/app/main.bash"]
