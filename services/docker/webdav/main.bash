#!/bin/bash
set -euo pipefail

mkdir -p /data/file

if [ -f /data/auth ]; then
    auth_content=$(cat /data/auth)
else
    auth_content='admin:admin@/:rw'
fi

auth_lines=''
while IFS= read -r line; do
    auth_lines="${auth_lines}  - '${line}'"$'\n'
done <<< "$auth_content"

while IFS= read -r line || [ -n "$line" ]; do
    if [ "$line" = "@@AUTH@@" ]; then
        printf '%s' "$auth_lines"
    else
        printf '%s\n' "$line"
    fi
done < /app/dufs-config.yaml.template > /app/dufs-config.yaml

exec /app/dufs --config /app/dufs-config.yaml
