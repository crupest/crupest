#!/usr/bin/env bash

# Check I'm root.
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

# Check CRUPEST_CERTBOT_RENEW_COMMAND is defined.
if [ -z "$CRUPEST_CERTBOT_RENEW_COMMAND" ]; then
    echo "CRUPEST_CERTBOT_RENEW_COMMAND must be defined."
    exit 1
fi

# Check CRUPEST_CERT_PATH, default to /etc/letsencrypt/live/$CRUPEST_DOMAIN/fullchain.pem
if [ -z "$CRUPEST_CERT_PATH" ]; then
    CRUPEST_CERT_PATH="/etc/letsencrypt/live/$CRUPEST_DOMAIN/fullchain.pem"
fi

function check_and_renew_cert() {
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
    rest_time="$((renew_timestamp - $(date +%s)))"
    echo "Rest time til renew: $rest_time seconds"

    # Do we have rest time?
    if [ "$rest_time" -gt 0 ]; then
        # Check CRUPEST_GREEDY_CHECK is defined.
        if [ -z "$CRUPEST_GREEDY_CHECK" ]; then
            # Sleep til renew.
            echo "Sleeping til renew..."
            sleep "$rest_time"
        else
            # Sleep 1 hour.
            echo "Seems like CRUPEST_GREEDY_CHECK is defined, sleep 1 day and check again..."
            sleep 86400
        fi
    else
        # No, renew now.
        echo "Renewing now..."
        # Run CRUPEST_CERTBOT_RENEW_COMMAND
        $CRUPEST_CERTBOT_RENEW_COMMAND
    fi
}

# Run check_and_renew_cert in infinate loop.
while true; do
    check_and_renew_cert
done
