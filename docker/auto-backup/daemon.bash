#!/usr/bin/env bash

set -e

# Check I'm root.
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi


# Check tar, zstd and coscli
tar --version
zstd --version
/app/coscli --version

function backup {
    # Output "Begin backup..." in yellow and restore default
    echo -e "\e[0;103m\e[K\e[1mBegin backup..." "\e[0m"

    # Get current time and convert it to YYYY-MM-DDTHH:MM:SSZ
    current_time="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "Current time UTC: $current_time"

    backup_file_ext="tar.zst"
    tmp_file="/tmp/data.$backup_file_ext"

    echo "Create $tmp_file for data..."
    tar -cp --zstd -f "$tmp_file" -C / data

    du -h "$tmp_file" | cut -f1 | xargs echo "Size of $tmp_file:"

    des_file_name="$current_time.$backup_file_ext"
    /app/coscli --init-skip \
      --secret-id "${CRUPEST_AUTO_BACKUP_COS_SECRET_ID}" \
      --secret-key "${CRUPEST_AUTO_BACKUP_COS_SECRET_KEY}" \
      --endpoint "cos.${CRUPEST_AUTO_BACKUP_COS_REGION}.myqcloud.com" \
      cp "$tmp_file" "cos://${CRUPEST_AUTO_BACKUP_BUCKET_NAME}/$des_file_name"

    echo "Remove tmp file..."
    # remove tmp
    rm "$tmp_file"

    echo "$des_file_name" >> /data/backup.log

    # echo "Backup finished!" in green and restore default
    echo -e "\e[0;102m\e[K\e[1mFinish backup!\e[0m"
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
