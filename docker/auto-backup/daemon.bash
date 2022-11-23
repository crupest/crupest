#!/usr/bin/env bash

set -e

# Check I'm root.
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

# Check if CRUPEST_AUTO_BACKUP_BUCKET_NAME is defined.
if [[ -z "$CRUPEST_AUTO_BACKUP_BUCKET_NAME" ]]; then
    echo "CRUPEST_AUTO_BACKUP_BUCKET_NAME is not defined or empty"
    exit 1
fi

rclone --version

# Check xz and tar
xz --version
tar --version

function backup {
    # Output "Begin backup..." in yellow and restore default
    echo -e "\e[0;103m\e[K\e[1mBegin backup..." "\e[0m"

    # Get current time and convert it to YYYY-MM-DDTHH.MM.SS
    current_time=$(date +%Y-%m-%dT%H.%M.%S)
    echo "Current time: $current_time"
    echo "Create tar.xz for data..."

    # tar and xz /data to tmp
    tar -cJf /tmp/data.tar.xz -C / data

    echo "Use rclone to upload data..."
    # upload to remote
    rclone --progress copyto /tmp/data.tar.xz "mycos:$CRUPEST_AUTO_BACKUP_BUCKET_NAME/$current_time.tar.xz"

    echo "Remove tmp file..."
    # remove tmp
    rm /tmp/data.tar.xz

    # echo "Backup finished!" in green and restore default
    echo -e "\e[0;102m\e[K\e[1mFinish backup!" "\e[0m"
}

echo "Initial delay: $CRUPEST_AUTO_BACKUP_INIT_DELAY"
sleep "$CRUPEST_AUTO_BACKUP_INIT_DELAY"

# forever loop
while true; do
    backup

    # sleep for CRUPEST_AUTO_BACKUP_INTERVAL
    echo "Sleep for $CRUPEST_AUTO_BACKUP_INTERVAL for next backup..."
    sleep "$CRUPEST_AUTO_BACKUP_INTERVAL"
done
