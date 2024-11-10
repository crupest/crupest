#! /usr/bin/env bash

set -e

grep -e 'URIs:' /etc/apt/sources.list.d/debian.sources | \
    sed -E 's|URIs:\s*https?://([-_.a-zA-Z0-9]+)/.*|\1|;q'
