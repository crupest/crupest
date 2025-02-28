FROM debian:latest
RUN apt-get update && apt-get install -y \
    git cgit lighttpd apache2-utils python3-pygments python3-markdown \
    tar gzip bzip2 zip unzip tini && \
    rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1000 git && useradd -m -u 1000 -g 1000 -s /usr/bin/bash git

ENV GIT_CONFIG_SYSTEM=/etc/gitconfig GIT_CONFIG_GLOBAL=/git/private/gitconfig

ADD gitconfig /etc/gitconfig
ADD hooks/* /etc/git/hooks/
ADD git-lighttpd.conf git-auth.conf lighttpd-wrapper.bash /app/

USER git:git
VOLUME [ "/git" ]
CMD [ "tini", "--", "/app/lighttpd-wrapper.bash" ]
