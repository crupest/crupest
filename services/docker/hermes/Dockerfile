# One frontend build feeds the image; the adapter wheel is built once.
FROM node:22-slim AS frontend

WORKDIR /src/frontend
COPY services/onebot-adapter/frontend/package.json services/onebot-adapter/frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY services/onebot-adapter/frontend/ ./
RUN npm run build


FROM python:3.11-slim-bookworm AS base

ARG APT_MIRROR=""
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN if [ -n "${APT_MIRROR}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do \
            [ -f "$f" ] || continue; \
            sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g; s|archive.ubuntu.com|${APT_MIRROR}|g; s|security.ubuntu.com|${APT_MIRROR}|g" "$f"; \
        done; \
    fi \
    && apt-get -o Acquire::Retries=10 update && apt-get -o Acquire::Retries=10 install -y --no-install-recommends \
        ffmpeg git curl ca-certificates tini gosu \
    && rm -rf /var/lib/apt/lists/*


FROM base AS adapter-build

# setuptools-scm cannot see the submodule's .git inside the build context.
# Keep this in sync with the services/onebot-adapter CHANGELOG version.
ARG ONEBOT_ADAPTER_VERSION=1.8.0

WORKDIR /src/adapter
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel setuptools-scm

COPY services/onebot-adapter/pyproject.toml services/onebot-adapter/MANIFEST.in \
     services/onebot-adapter/README.md services/onebot-adapter/CHANGELOG.md \
     services/onebot-adapter/LICENSE ./
COPY services/onebot-adapter/onebot_adapter ./onebot_adapter
COPY --from=frontend /src/frontend/dist/ ./onebot_adapter/webui/static/

RUN --mount=type=cache,target=/root/.cache/pip \
    SETUPTOOLS_SCM_PRETEND_VERSION="$ONEBOT_ADAPTER_VERSION" \
    pip wheel --no-deps --wheel-dir /wheels .


FROM base AS runtime

ENV APP_DIR=/opt/hermes \
    VENV=/opt/hermes/venv \
    HOME=/opt/data \
    HERMES_HOME=/opt/data/.hermes \
    PATH=/opt/hermes/venv/bin:$PATH

COPY --from=adapter-build /wheels /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv "$VENV" \
    && "$VENV/bin/pip" install --upgrade pip setuptools wheel \
    && "$VENV/bin/pip" install "hermes-agent~=0.19.0" \
    && "$VENV/bin/pip" install /wheels/*.whl

# Bundled web provider: DeepSeek Search & Fetch (same DEEPSEEK_API_KEY).
COPY services/docker/hermes/web-plugin/crupest_deepseek ${VENV}/lib/python3.11/site-packages/plugins/web/crupest_deepseek

RUN groupadd --gid 1000 hermes \
    && useradd --uid 1000 --gid hermes --home-dir /opt/data --no-create-home --shell /bin/bash hermes \
    && chown -R hermes:hermes /opt/hermes \
    && mkdir -p /opt/data/.hermes /opt/data/.onebot_adapter \
    && chown -R hermes:hermes /opt/data

WORKDIR /opt/hermes
COPY services/docker/hermes/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY services/docker/hermes/bootstrap.py /opt/hermes/bootstrap.py
COPY services/docker/hermes/SOUL.md /opt/hermes/SOUL.md
RUN chmod 0755 /usr/local/bin/entrypoint.sh

VOLUME [ "/opt/data" ]

ENTRYPOINT [ "tini", "--", "/usr/local/bin/entrypoint.sh" ]


# Thin wrappers: both share every runtime layer; only role/env/expose/health
# differ. The adapter image is the only one that listens on exposed ports.
FROM runtime AS adapter
ENV ROLE=adapter \
    ONEBOT_HANDOFF_FILE=/opt/data/handoff/hermes_ws_token
EXPOSE 18800 18810 18820
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:18820/api/v1/health || exit 1


FROM runtime AS hermes
ENV ROLE=hermes \
    ONEBOT_HANDOFF_FILE=/opt/onebot-adapter/hermes_ws_token

