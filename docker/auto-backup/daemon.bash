#!/usr/bin/env bash

set -e

# Check I'm root.
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi


# Check xz, tar and coscmd
xz --version
tar --version

function backup {
    # Output "Begin backup..." in yellow and restore default
    echo -e "\e[0;103m\e[K\e[1mBegin backup..." "\e[0m"

    # Get current time and convert it to YYYY-MM-DDTHH:MM:SSZ
    current_time=$(date +%Y-%m-%dT%H:%M:%SZ)
    echo "Current time: $current_time"

    echo "Create tar.xz for data..."

    # tar and xz /data to tmp
    tar -cJf /tmp/data.tar.xz -C / data

    # Output /tmp/data.tar.xz size
    du -h /tmp/data.tar.xz | cut -f1 | xargs echo "Size of data.tar.xz:"

    destination="${current_time}.tar.xz"

    # upload to remote
    dotnet /AutoBackup/AutoBackup.dll /tmp/data.tar.xz "$destination" 

    echo "Remove tmp file..."
    # remove tmp
    rm /tmp/data.tar.xz

    echo "$destination" >> /data/backup.log

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
