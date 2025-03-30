#!/usr/bin/env bash

set -e

die() {
  echo -e "\033[31mError: " "$@" "\033[0m" >&2
  exit 1
}

note() {
  echo -e "\033[33mNote: " "$@" "\033[0m"
}

success() {
  echo -e "\033[32mSuccess: " "$@" "\033[0m"
}

if [[ -z "$CRUPEST_AUTO_BACKUP_INTERVAL" ]]; then
  die "Backup interval not set, please set it!"
fi

note "Checking secrets..."
[[ -n "$RCLONE_S3_PROVIDER" ]] || die "S3 provider not set!"
[[ -n "$RCLONE_S3_ENDPOINT" ]] || die "S3 endpoint not set!"
[[ -n "$RCLONE_S3_ACCESS_KEY_ID" ]] || die "S3 AccessKey ID not set!"
[[ -n "$RCLONE_S3_SECRET_ACCESS_KEY" ]] || die "S3 AccessKey Secret not set!"
[[ -n "$CRUPEST_AUTO_BACKUP_S3_BUCKET" ]] || die "S3 bucket not set!"
success "Secrets check passed."

note "Checking tools..."
tar --version
zstd --version
rclone --version
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
  echo "Upload $des_file_name to S3..."

  rclone --config=/app/rclone.conf copyto \
    "$tmp_file" "remote://${CRUPEST_AUTO_BACKUP_S3_BUCKET}/$des_file_name"

  echo "Remove tmp file..."
  rm "$tmp_file"

  echo "$des_file_name" >> /data/auto-backup/backup.log

  success "Finish backup!"
}

# forever loop
while true; do
  backup

  echo "Sleep for $CRUPEST_AUTO_BACKUP_INTERVAL for next backup..."
  sleep "$CRUPEST_AUTO_BACKUP_INTERVAL"
done
