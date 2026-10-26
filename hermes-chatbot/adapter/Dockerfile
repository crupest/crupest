FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Third-party deps first: they never change with our code, so a source edit
# only re-runs the cheap install below.
RUN pip install "aiohttp>=3.9,<4" "pydantic>=2.6,<3"

WORKDIR /app

COPY core /app/core
COPY adapter /app/adapter
COPY config/config.example.toml /opt/chatbot-defaults/config.example.toml

RUN pip install --no-deps /app/core /app/adapter

RUN useradd --create-home --uid 1000 chatbot
USER 1000

EXPOSE 18800 18810

ENTRYPOINT ["crupest-chatbot-adapter"]
CMD ["--config", "/opt/chatbot/config.toml"]
