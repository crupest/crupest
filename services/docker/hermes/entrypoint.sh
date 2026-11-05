#!/usr/bin/env bash
set -euo pipefail

GOSU_BIN=""

if [ "$(id -u)" -eq 0 ]; then
    mkdir -p /opt/data /opt/data/share
    # Create the Hermes home before handing the tree to the service user:
    # on a fresh volume the mount root may be root-owned, and bootstrap runs
    # as `hermes`.
    mkdir -p "${HERMES_HOME:-/opt/data/.hermes}/plugins"
    chown -R hermes:hermes /opt/data
    GOSU_BIN="$(command -v gosu || command -v su-exec || true)"
    if [ -z "${GOSU_BIN}" ]; then
        printf '[entrypoint] neither gosu nor su-exec is available\n' >&2
        exit 1
    fi
fi

export HERMES_HOME="${HERMES_HOME:-/opt/data/.hermes}"
mkdir -p "${HERMES_HOME}"

if [ -n "${GOSU_BIN}" ]; then
    "${GOSU_BIN}" hermes python /opt/hermes/bootstrap.py
else
    python /opt/hermes/bootstrap.py
fi

if [ -n "${GOSU_BIN}" ]; then
    exec "${GOSU_BIN}" hermes hermes gateway run
fi
exec hermes gateway run
