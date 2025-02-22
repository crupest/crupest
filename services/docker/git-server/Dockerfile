FROM debian:latest
RUN apt-get update && apt-get install -y \
    git cgit lighttpd apache2-utils python3-pygments python3-markdown \
    tar gzip bzip2 zip unzip tini && \
    rm -rf /var/lib/apt/lists/*

ADD git-lighttpd.conf git-auth.conf /app/
ADD --chmod=755 lighttpd-wrapper.bash /app/

VOLUME [ "/git" ]
CMD [ "tini", "--", "/app/lighttpd-wrapper.bash" ]
