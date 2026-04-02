#!/usr/bin/bash

set -e -o pipefail

mkdir -p /var/spool/postfix/private
chown postfix:postfix /var/spool/postfix/private

postconf "myhostname=mail.${CRUPEST_MAIL_SERVER_MAIL_DOMAIN}"
postconf "mydomain=${CRUPEST_MAIL_SERVER_MAIL_DOMAIN}"
postconf "virtual_mailbox_domains=${CRUPEST_MAIL_SERVER_MAIL_DOMAIN}"

/app/crupest-mail serve --real &

/usr/sbin/dovecot -F &

tries=0
while [[ ! -S /var/spool/postfix/private/auth || ! -S /var/spool/postfix/private/dovecot-lmtp ]]; do
  if [[ $tries -ge 10 ]]; then
    echo "Error: Dovecot auth and lmtp sockets are not found after 10 seconds!"
    exit 1
  fi
  sleep 1
  ((tries++))
done

if [[ ! -f /data/postfix-virtual ]]; then
  touch /data/postfix-virtual
  chmod 644 /data/postfix-virtual
fi

postmap /data/postfix-virtual

postfix start-fg
