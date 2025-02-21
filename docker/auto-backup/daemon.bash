#!/usr/bin/env bash

set -e
set -o pipefail

# shellcheck source=../share/crupest/base.bash
. base.bash

secrets=(
  CRUPEST_AUTO_BACKUP_COS_ENDPOINT
  CRUPEST_AUTO_BACKUP_COS_BUCKET
  CRUPEST_AUTO_BACKUP_COS_SECRET_ID
  CRUPEST_AUTO_BACKUP_COS_SECRET_KEY
)
import_docker_secrets auto-backup "${secrets[@]}"
check_env CRUPEST_AUTO_BACKUP_INTERVAL

note "Checking tools..."
tar --version
zstd --version
/app/coscli --version
success "Tools check passed."

echo "Backup interval set to $CRUPEST_AUTO_BACKUP_INTERVAL..."

if [[ -z "$CRUPEST_AUTO_BACKUP_INIT_DELAY" ]]; then
  echo "Initial delay not set, will do a backup immediately!"
else
  echo "Initial delay set to $CRUPEST_AUTO_BACKUP_INIT_DELAY ..."
  sleep "$CRUPEST_AUTO_BACKUP_INIT_DELAY"
fi

function backup {
  note "Begin backup..."

  # Get current time and convert it to YYYY-MM-DDTHH:MM:SSZ
  current_time="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Current time UTC: $current_time"

  backup_file_ext="tar.zst"
  tmp_file="/tmp/data.$backup_file_ext"

  echo "Create $tmp_file for data..."
  tar -cp --zstd -f "$tmp_file" -C / data

  du -h "$tmp_file" | cut -f1 | xargs echo "Size of $tmp_file:"

  des_file_name="$current_time.$backup_file_ext"
  echo "Upload $des_file_name to COS..."

  /app/coscli --init-skip \
    --secret-id "${CRUPEST_AUTO_BACKUP_COS_SECRET_ID}" \
    --secret-key "${CRUPEST_AUTO_BACKUP_COS_SECRET_KEY}" \
    --endpoint "${CRUPEST_AUTO_BACKUP_COS_ENDPOINT}" \
    cp "$tmp_file" "cos://${CRUPEST_AUTO_BACKUP_COS_BUCKET}/$des_file_name"

  echo "Remove tmp file..."
  rm "$tmp_file"

  echo "$des_file_name" >>/data/backup.log

  success "Finish backup!"
}

# forever loop
while true; do
  backup

  note "Sleep for $CRUPEST_AUTO_BACKUP_INTERVAL for next backup..."
  sleep "$CRUPEST_AUTO_BACKUP_INTERVAL"
done
