#!/usr/bin/env bash

set -e

# Check I'm root.
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

# Check certbot version.
certbot --version

# Check domain
if [[ -z "$CRUPEST_DOMAIN" ]]; then
    echo "CRUPEST_DOMAIN can't be empty!" 1>&2
    exit 1
fi

# Check email
if [[ -z "$CRUPEST_EMAIL" ]]; then
    echo "CRUPEST_EMAIL can't be empty!" 1>&2
    exit 2
fi

# Check CRUPEST_CERT_PATH, default to /etc/letsencrypt/live/$CRUPEST_DOMAIN/fullchain.pem
if [ -z "$CRUPEST_CERT_PATH" ]; then
    CRUPEST_CERT_PATH="/etc/letsencrypt/live/$CRUPEST_DOMAIN/fullchain.pem"
fi

# Check CRUPEST_CERT_PATH exists.
if [ ! -f "$CRUPEST_CERT_PATH" ]; then
    echo "Cert file does not exist. You may want to generate it manually with aio script." 1>&2
    exit 3
fi

echo "Root domain:" "$CRUPEST_DOMAIN"
echo "Email:" "$CRUPEST_EMAIL"
echo "Cert path: ${CRUPEST_CERT_PATH}"

# Check CRUPEST_AUTO_CERTBOT_RENEW_COMMAND is defined.
if [ -z "$CRUPEST_AUTO_CERTBOT_RENEW_COMMAND" ]; then
    echo "CRUPEST_AUTO_CERTBOT_RENEW_COMMAND is not defined or empty. Will use the default one."
else
    printf "CRUPEST_AUTO_CERTBOT_RENEW_COMMAND is defined as:\n%s\n" "$CRUPEST_AUTO_CERTBOT_RENEW_COMMAND"
fi

mapfile -t domains <<< "$(./get-cert-domains.py "${CRUPEST_CERT_PATH}")"

for domain in "${domains[@]}"; do
    domain_options=("${domain_options[@]}" -d "$domain") 
done

options=("${domain_options[@]}")
if [ -n "$CRUPEST_AUTO_CERTBOT_POST_HOOK" ]; then
    printf "You have defined a post hook:\n%s\n" "$CRUPEST_AUTO_CERTBOT_POST_HOOK"
    options=("${options[@]}" --post-hook "$CRUPEST_AUTO_CERTBOT_POST_HOOK")
fi

# Use test server to test.
certbot certonly  -n --agree-tos --test-cert --dry-run -m "$CRUPEST_EMAIL" --webroot -w /var/www/certbot "${options[@]}"

function check_and_renew_cert {
    expire_info=$(openssl x509 -enddate -noout -in "$CRUPEST_CERT_PATH")
    
    # Get ssl certificate expire date.
    expire_date=$(echo "$expire_info" | cut -d= -f2)

    echo "SSL certificate expire date: $expire_date"

    # Convert expire date to UNIX timestamp.
    expire_timestamp="$(date -d "$expire_date" +%s)"

    # Minus expire timestamp with 30 days in UNIX timestamp.
    renew_timestamp="$((expire_timestamp - 2592000))"
    echo "Renew SSL certificate at: $(date -d @$renew_timestamp)"

    # Get rest time til renew.
    rest_time_in_second="$((renew_timestamp - $(date +%s)))"
    rest_time_in_day=$((rest_time_in_second / 86400))
    echo "Rest time til renew: $rest_time_in_second seconds, aka, about $rest_time_in_day days"

    # Do we have rest time?
    if [ $rest_time_in_second -gt 0 ]; then
        # Sleep 1 hour.
        echo "I'm going to sleep for 1 day to check again."
        sleep 1d
    else
        # No, renew now.
        echo "Renewing now..."

        if [ -n "$CRUPEST_AUTO_CERTBOT_RENEW_COMMAND" ]; then
            $CRUPEST_AUTO_CERTBOT_RENEW_COMMAND
        else

            certbot renew -n --agree-tos -m "$CRUPEST_EMAIL" --webroot -w /var/www/certbot "${options[@]}"
        fi
    fi
}

# Run check_and_renew_cert in infinate loop.
while true; do
    check_and_renew_cert
done
