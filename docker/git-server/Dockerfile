FROM debian:latest
RUN apt-get update && apt-get install -y \
    git cgit lighttpd apache2-utils python3-pygments python3-markdown \
    tar gzip bzip2 zip unzip tini && \
    rm -rf /var/lib/apt/lists/*

COPY --from=share * /app/
ADD git-lighttpd.conf git-auth.conf cgitrc.template /app/
ADD --chmod=755 lighttpd-wrapper /app/

WORKDIR /app
VOLUME [ "/git" ]
CMD [ "/usr/bin/tini", "--", "/app/lighttpd-wrapper.bash" ]
