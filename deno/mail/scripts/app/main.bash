#!/usr/bin/bash

set -e -o pipefail

# clean stale dovecot pid file if exists
if [[ -f /var/run/dovecot/master.pid ]]; then
  dovecot_pid="$(cat /var/run/dovecot/master.pid)"
  if [[ ! "$dovecot_pid" =~ ^[0-9]+$ || ! -d "/proc/$dovecot_pid" ]]; then
    rm -f /var/run/dovecot/master.pid
  fi
fi

mkdir -p /var/spool/postfix/private
chown postfix:postfix /var/spool/postfix/private

install -d -m 0770 -o vmail -g vmail /data/spamassassin /run/spamd

for script in /etc/dovecot/sieve/*.sieve; do
  sievec -c /etc/dovecot/dovecot.conf "$script"
done

/usr/sbin/spamd \
  --listen=127.0.0.1 \
  --allow-tell \
  --username=vmail \
  --groupname=vmail \
  --nouser-config \
  --helper-home-dir=/data/spamassassin \
  --max-children=5 \
  --pidfile=/run/spamd/spamd.pid \
  --syslog=stderr &

tries=0
until /usr/bin/spamc -K >/dev/null 2>&1; do
  if [[ $tries -ge 10 ]]; then
    echo "Error: SpamAssassin is not ready after 10 seconds!"
    exit 1
  fi
  sleep 1
  ((++tries))
done

postconf "myhostname=mail.${CRUPEST_MAIL_SERVER_MAIL_DOMAIN}"
postconf "mydomain=${CRUPEST_MAIL_SERVER_MAIL_DOMAIN}"
postconf "virtual_mailbox_domains=${CRUPEST_MAIL_SERVER_MAIL_DOMAIN}"

if [[ ! -f /data/postfix-virtual ]]; then
  touch /data/postfix-virtual
  chmod 644 /data/postfix-virtual
fi

postmap /data/postfix-virtual

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

postfix start-fg
