ARG SERVER USERNAME PASSWORD

FROM debian:latest AS lighttpd-config-generator
ARG USERNAME PASSWORD
RUN apt-get update && apt-get install -y apache2-utils
RUN htpasswd -cb /user-info ${USERNAME} ${PASSWORD}

FROM debian:latest
ARG SERVER
RUN apt-get update && apt-get install -y \
    git lighttpd apache2-utils python3-pygments python3-markdown \
    tar gzip bzip2 zip unzip tini && \
    rm -rf /var/lib/apt/lists/*
ADD cgitrc /etc/cgitrc
ADD git-lighttpd.conf git-auth.conf /git-server/
ADD --chmod=755 lighttpd-wrapper /git-server/
COPY --from=lighttpd-config-generator /user-info /git-server/

ENV GIT_SERVER=${SERVER}
VOLUME [ "/git" ]
ENTRYPOINT ["/tini", "--"]
CMD [ "/git-server/lighttpd-wrapper" ]
