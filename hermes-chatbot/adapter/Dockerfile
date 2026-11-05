FROM python:3.14-slim-bookworm AS build

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_CACHE_DIR=/root/.cache/uv

WORKDIR /app

COPY pyproject.toml uv.lock /app/
COPY core /app/core
COPY adapter /app/adapter
COPY plugin /app/plugin
COPY config/config.example.toml /opt/chatbot-defaults/config.example.toml

RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-dev --package crupest-hermes-chatbot-adapter

FROM python:3.14-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/app/.venv/bin:$PATH

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/
COPY --from=build /app /app

RUN useradd --create-home --uid 1000 chatbot
USER 1000

EXPOSE 18800 18810

ENTRYPOINT ["crupest-chatbot-adapter"]
CMD ["--config", "/opt/chatbot/config.toml"]
