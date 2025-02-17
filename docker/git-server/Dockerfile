ARG DOMAIN
ARG PORT=80
ARG USERNAME
ARG PASSWORD

FROM debian:latest AS lighttpd-config-generator
RUN apt-get update && apt-get install -y apache2-utils
ENV USERNAME=${USERNAME} PASSWORD=${PASSWORD} DOMAIN=${DOMAIN} PORT=${PORT}
ADD git-lighttpd.conf.template git-auth.conf /etc/git-server/
RUN htpasswd -cb /etc/git-server/user-info ${USERNAME} ${PASSWORD}
RUN sed "s|@@DOMAIN@@|${DOMAIN}|g;s|@@PORT@@|${PORT}|g;" /etc/git-server/git-lighttpd.conf.template \
    > /etc/git-server/git-lighttpd.conf

FROM debian:latest
RUN apt-get update && apt-get install -y \
    git lighttpd apache2-utils python3-pygments python3-markdown \
    tar gzip bzip2 zip unzip && \
    rm -rf /var/lib/apt/lists/*
ADD cgitrc /etc/cgitrc
COPY --from=lighttpd-config-generator /etc/git-server /etc/git-server

ENV GIT_SERVER_DOMAIN=${DOMAIN} GIT_SERVER_PORT=${PORT}
VOLUME [ "/git" ]
CMD [ "/usr/sbin/lighttpd", "-D", "-f", "/etc/git-server/git-lighttpd.conf" ]
