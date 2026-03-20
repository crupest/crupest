FROM debian:latest
RUN apt-get update && apt-get install -y \
    git cgit lighttpd apache2-utils python3-pygments python3-markdown \
    tar gzip bzip2 zip unzip tini curl && \
    rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1000 git && useradd -m -u 1000 -g 1000 -s /usr/bin/bash git

ENV GIT_CONFIG_SYSTEM=/app/git/gitconfig GIT_CONFIG_GLOBAL=/git/gitconfig

ADD app /app
USER git:git
VOLUME [ "/git" ]
EXPOSE 3636
CMD [ "tini", "--", "/app/lighttpd-wrapper.bash" ]

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=1 \
    CMD "curl","-f", "http://localhost:3636/git" || exit 1
