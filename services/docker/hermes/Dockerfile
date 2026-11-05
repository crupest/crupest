# Hermes 0.22 gateway, built from the tagged source without the desktop,
# browser, Node, TUI, or bundled tool-store payloads.

ARG APT_MIRROR=""
ARG HERMES_VERSION=v0.22.7
ARG HERMES_COMMIT=b200f5bc60e31588ba2cb60e288029c4a54ba5fa
ARG NODE_VERSION=lts
ARG SQLITE_AUTOCONF_VERSION=3530400
ARG SQLITE_SHA256=0e9483900e92cd5de8fd48d16bf9200145a61f7fd5be542a5ac81d8a9516eb9c

FROM debian:bookworm-slim AS sqlite-build
ARG APT_MIRROR
ARG SQLITE_AUTOCONF_VERSION
ARG SQLITE_SHA256
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    if [ -n "${APT_MIRROR}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do \
            [ -f "$f" ] || continue; \
            sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g" "$f"; \
        done; \
    fi \
    && apt-get -o Acquire::Retries=10 update \
    && apt-get -o Acquire::Retries=10 install -y --no-install-recommends \
        build-essential ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && (curl -fsSL --retry 2 --connect-timeout 15 --max-time 300 \
            -o /tmp/sqlite.tar.gz \
            "https://sqlite.org/2026/sqlite-autoconf-${SQLITE_AUTOCONF_VERSION}.tar.gz" \
        || curl -fsSL --retry 3 --connect-timeout 15 --max-time 300 \
            -o /tmp/sqlite.tar.gz \
            "https://sources.buildroot.net/sqlite/sqlite-autoconf-${SQLITE_AUTOCONF_VERSION}.tar.gz") \
    && printf '%s  %s\n' "${SQLITE_SHA256}" /tmp/sqlite.tar.gz > /tmp/sqlite.sha256 \
    && sha256sum -c /tmp/sqlite.sha256 \
    && tar -xzf /tmp/sqlite.tar.gz -C /tmp \
    && cd "/tmp/sqlite-autoconf-${SQLITE_AUTOCONF_VERSION}" \
    && CFLAGS="-O2 \
        -DSQLITE_ENABLE_FTS3 \
        -DSQLITE_ENABLE_FTS3_PARENTHESIS \
        -DSQLITE_ENABLE_FTS4 \
        -DSQLITE_ENABLE_FTS5 \
        -DSQLITE_ENABLE_RTREE \
        -DSQLITE_ENABLE_COLUMN_METADATA \
        -DSQLITE_ENABLE_UNLOCK_NOTIFY \
        -DSQLITE_ENABLE_DBSTAT_VTAB \
        -DSQLITE_ENABLE_DBPAGE_VTAB \
        -DSQLITE_ENABLE_MATH_FUNCTIONS \
        -DSQLITE_ENABLE_PREUPDATE_HOOK \
        -DSQLITE_ENABLE_SESSION \
        -DSQLITE_SECURE_DELETE \
        -DSQLITE_THREADSAFE=1" \
        ./configure --prefix=/opt/sqlite-fixed --disable-static \
    && make -j"$(nproc)" \
    && make install

FROM python:3.14-slim-bookworm AS hermes-build
ARG HERMES_VERSION
ARG HERMES_COMMIT
ARG APT_MIRROR
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/root/.cache/uv \
    UV_PROJECT_ENVIRONMENT=/opt/hermes/venv

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    if [ -n "${APT_MIRROR}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do \
            [ -f "$f" ] || continue; \
            sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g" "$f"; \
        done; \
    fi \
    && apt-get -o Acquire::Retries=10 update \
    && apt-get -o Acquire::Retries=10 install -y --no-install-recommends \
        build-essential ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch "${HERMES_VERSION}" \
        https://github.com/NousResearch/hermes-agent.git /opt/hermes \
    && test "$(git -C /opt/hermes rev-parse HEAD)" = "${HERMES_COMMIT}"

WORKDIR /opt/hermes

RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-dev --python 3.14

RUN python scripts/write_install_stamp.py \
        --output /opt/hermes/install-stamp.json \
        --commit "${HERMES_COMMIT}" \
        --branch "${HERMES_VERSION}" \
        --base-version "${HERMES_VERSION#v}" \
        --distance 0 \
        --source ci \
        --distribution docker \
        --update-mechanism external

COPY hermes-chatbot/core /src/chatbot-core
COPY hermes-chatbot/plugin /src/chatbot-plugin

RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv pip install --python /opt/hermes/venv/bin/python \
        --no-deps /src/chatbot-core \
    && uv pip install --python /opt/hermes/venv/bin/python \
        "aiohttp>=3.9,<4"

# Bundled DeepSeek web provider: loaded from the source plugin tree.
COPY services/docker/hermes/web-plugin/crupest_deepseek \
    /opt/hermes/plugins/web/crupest_deepseek

# Keep only what the gateway needs. The browser/desktop/Node payloads are
# deliberately absent from this image.
RUN rm -rf \
        /opt/hermes/.git \
        /opt/hermes/tests \
        /opt/hermes/evals \
        /opt/hermes/apps \
        /opt/hermes/ui-tui \
        /opt/hermes/web \
        /opt/hermes/website \
        /opt/hermes/native \
    && mkdir -p /opt/chatbot-plugin \
    && cp -a /src/chatbot-plugin/src/crupest_chatbot_plugin/. /opt/chatbot-plugin/

FROM node:${NODE_VERSION}-bookworm-slim AS node

FROM python:3.14-slim-bookworm

ARG APT_MIRROR

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/opt/data/.cache/uv \
    NPM_CONFIG_CACHE=/opt/data/.cache/npm \
    VENV=/opt/hermes/venv \
    HOME=/opt/data \
    HERMES_HOME=/opt/data/.hermes \
    PATH=/opt/hermes/venv/bin:/usr/local/bin:$PATH

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    if [ -n "${APT_MIRROR}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do \
            [ -f "$f" ] || continue; \
            sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g" "$f"; \
        done; \
    fi \
    && apt-get -o Acquire::Retries=10 update \
    && apt-get -o Acquire::Retries=10 install -y --no-install-recommends \
        ffmpeg git curl ca-certificates tini gosu sudo procps ripgrep libatomic1 \
    && rm -rf /var/lib/apt/lists/* \
    && printf 'hermes ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/hermes \
    && chmod 0440 /etc/sudoers.d/hermes

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && node --version \
    && npm --version

RUN groupadd --gid 1000 hermes \
    && useradd --uid 1000 --gid hermes --home-dir /opt/data --no-create-home --shell /bin/bash hermes \
    && mkdir -p /opt/data/.hermes \
    && chown -R hermes:hermes /opt/data

COPY --from=sqlite-build /opt/sqlite-fixed/lib/libsqlite3.so.3.53.4 /usr/local/lib/
RUN ln -sf libsqlite3.so.3.53.4 /usr/local/lib/libsqlite3.so.0 \
    && ln -sf libsqlite3.so.3.53.4 /usr/local/lib/libsqlite3.so \
    && printf '/usr/local/lib\n' > /etc/ld.so.conf.d/000-sqlite-fixed.conf \
    && ldconfig \
    && python -c "import sqlite3, sys; print('sqlite', sqlite3.sqlite_version); \
        sys.exit(0 if sqlite3.sqlite_version_info >= (3, 51, 3) else 1)"

COPY --from=hermes-build /opt/hermes /opt/hermes
COPY --from=hermes-build /opt/chatbot-plugin /opt/chatbot-plugin
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/

COPY services/docker/hermes/SOUL.md /opt/hermes/SOUL.md
COPY services/docker/hermes/bootstrap.py /opt/hermes/bootstrap.py
COPY services/docker/hermes/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN printf 'docker\n' > /opt/hermes/.install_method \
    && chmod 0755 /usr/local/bin/entrypoint.sh

WORKDIR /opt/hermes

VOLUME [ "/opt/data" ]

ENTRYPOINT [ "tini", "--", "/usr/local/bin/entrypoint.sh" ]
