#!/usr/bin/env bash
set -euo pipefail

ROLE="${ROLE:-hermes}"
case "${ROLE}" in
    adapter|hermes) ;;
    *) printf '[entrypoint] unknown ROLE=%s\n' "${ROLE}" >&2; exit 1 ;;
esac

export HOME=/opt/data
export PATH="/opt/hermes/venv/bin:${PATH}"
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

PYTHON=/opt/hermes/venv/bin/python
HERMES=/opt/hermes/venv/bin/hermes
ADAPTER=/opt/hermes/venv/bin/hermes-onebot-adapter
GOSU_BIN=""

if [ "$(id -u)" -eq 0 ]; then
    mkdir -p /opt/data
    chown -R hermes:hermes /opt/data
    GOSU_BIN="$(command -v gosu || command -v su-exec || true)"
    if [ -z "${GOSU_BIN}" ]; then
        printf '[entrypoint] neither gosu nor su-exec is available\n' >&2
        exit 1
    fi
fi

if [ "${ROLE}" = "adapter" ]; then
    export ONEBOT_ADAPTER_CONFIG="${ONEBOT_ADAPTER_CONFIG:-/opt/data/.onebot_adapter/config.json}"
    if [ -n "${GOSU_BIN}" ]; then
        "${GOSU_BIN}" hermes "${PYTHON}" /opt/hermes/bootstrap.py --role adapter
        exec "${GOSU_BIN}" hermes "${ADAPTER}" \
            --onebot-host 0.0.0.0 \
            --hermes-host 0.0.0.0 \
            --webui-host 0.0.0.0
    fi
    "${PYTHON}" /opt/hermes/bootstrap.py --role adapter
    exec "${ADAPTER}" \
        --onebot-host 0.0.0.0 \
        --hermes-host 0.0.0.0 \
        --webui-host 0.0.0.0
fi

export HERMES_HOME="${HERMES_HOME:-/opt/data/.hermes}"
if [ -n "${GOSU_BIN}" ]; then
    "${GOSU_BIN}" hermes "${PYTHON}" /opt/hermes/bootstrap.py --role hermes
else
    "${PYTHON}" /opt/hermes/bootstrap.py --role hermes
fi

ENV_FILE="${HERMES_HOME}/.entrypoint.env"
if [ ! -f "${ENV_FILE}" ]; then
    printf '[entrypoint] bootstrap did not write %s\n' "${ENV_FILE}" >&2
    exit 1
fi
set -a
# shellcheck disable=SC1090
. "${ENV_FILE}"
set +a
rm -f "${ENV_FILE}"

if [ -n "${GOSU_BIN}" ]; then
    exec "${GOSU_BIN}" hermes "${HERMES}" gateway run
fi
exec "${HERMES}" gateway run
