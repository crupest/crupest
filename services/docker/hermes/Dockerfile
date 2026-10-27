FROM python:3.13-slim-bookworm

ARG APT_MIRROR=""

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VENV=/opt/hermes/venv \
    HOME=/opt/data \
    HERMES_HOME=/opt/data/.hermes \
    PATH=/opt/hermes/venv/bin:$PATH

# System deps + the sudo/procps used by the terminal tool. One layer, cached
# until this ARG or the base image changes.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    if [ -n "${APT_MIRROR}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do \
            [ -f "$f" ] || continue; \
            sed -i "s|deb.debian.org|${APT_MIRROR}|g; s|security.debian.org|${APT_MIRROR}|g; s|archive.ubuntu.com|${APT_MIRROR}|g; s|security.ubuntu.com|${APT_MIRROR}|g" "$f"; \
        done; \
    fi \
    && apt-get -o Acquire::Retries=10 update \
    && apt-get -o Acquire::Retries=10 install -y --no-install-recommends \
        ffmpeg git curl ca-certificates tini gosu sudo procps \
    && rm -rf /var/lib/apt/lists/* \
    && printf 'hermes ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/hermes \
    && chmod 0440 /etc/sudoers.d/hermes

# Users and the data root never change: keep them in the first layer so no
# source edit invalidates them.
RUN groupadd --gid 1000 hermes \
    && useradd --uid 1000 --gid hermes --home-dir /opt/data --no-create-home --shell /bin/bash hermes \
    && mkdir -p /opt/data/.hermes \
    && chown -R hermes:hermes /opt/data

# Hermes itself is the expensive layer: install it before our sources so a
# code change never re-resolves or reinstalls the agent.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv "$VENV" \
    && "$VENV/bin/pip" install --upgrade pip setuptools wheel \
    && "$VENV/bin/pip" install "hermes-agent~=0.19.0" "aiohttp>=3.9,<4"

COPY hermes-chatbot/core /src/chatbot-core
COPY hermes-chatbot/plugin /src/chatbot-plugin

RUN "$VENV/bin/pip" install --no-deps /src/chatbot-core /src/chatbot-plugin

# Baked plugin directory; bootstrap copies it into $HERMES_HOME/plugins at boot
# (the home is a volume, so baking directly there would be masked). Kept out of
# /opt/chatbot because that path is the read-only config mount.
RUN mkdir -p /opt/chatbot-plugin \
    && cp -a /src/chatbot-plugin/src/crupest_chatbot_plugin/. /opt/chatbot-plugin/

# Bundled web provider: DeepSeek Search & Fetch (same DEEPSEEK_API_KEY).
COPY services/docker/hermes/web-plugin/crupest_deepseek ${VENV}/lib/python3.13/site-packages/plugins/web/crupest_deepseek

WORKDIR /opt/hermes
COPY services/docker/hermes/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY services/docker/hermes/bootstrap.py /opt/hermes/bootstrap.py
COPY services/docker/hermes/SOUL.md /opt/hermes/SOUL.md
RUN chmod 0755 /usr/local/bin/entrypoint.sh

VOLUME [ "/opt/data" ]

ENTRYPOINT [ "tini", "--", "/usr/local/bin/entrypoint.sh" ]
