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

# Check I'm root.
if [[ $EUID -ne 0 ]]; then
  die "This script must be run as root"
fi

if [[ ! -f /run/secrets/auto-backup ]]; then
  die "/run/secrets/auto-backup not found, please use docker secrets to set it."
fi

if [[ -z "$CRUPEST_AUTO_BACKUP_INTERVAL" ]]; then
  die "Backup interval not set, please set it!"
fi

# shellcheck source=/dev/null
. /run/secrets/auto-backup

note "Checking secrets..."
[[ -n "$CRUPEST_AUTO_BACKUP_COS_ENDPOINT" ]] || die "COS endpoint not set!"
[[ -n "$CRUPEST_AUTO_BACKUP_COS_BUCKET" ]] || die "COS bucket not set!"
[[ -n "$CRUPEST_AUTO_BACKUP_COS_SECRET_ID" ]] || die "COS secret ID  not set!"
[[ -n "$CRUPEST_AUTO_BACKUP_COS_SECRET_KEY" ]] || die "COS secret key not set!"
success "Secrets check passed."

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

  echo "Sleep for $CRUPEST_AUTO_BACKUP_INTERVAL for next backup..."
  sleep "$CRUPEST_AUTO_BACKUP_INTERVAL"
done
