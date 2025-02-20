
FROM debian:latest AS lighttpd-config-generator
RUN apt-get update && apt-get install -y apache2-utils
RUN --mount=type=secret,id=git-server,required=true \
  . /run/secrets/git-server && \
  htpasswd -cb /user-info ${CRUPEST_GIT_SERVER_USERNAME} ${CRUPEST_GIT_SERVER_PASSWORD}
ARG ROOT_URL
ADD cgitrc.template /cgitrc.template
RUN sed "s|@@CRUPEST_ROOT_URL@@|${ROOT_URL}|g" /cgitrc.template > /cgitrc

FROM debian:latest
RUN apt-get update && apt-get install -y \
    git cgit lighttpd apache2-utils python3-pygments python3-markdown \
    tar gzip bzip2 zip unzip tini && \
    rm -rf /var/lib/apt/lists/*

COPY --from=lighttpd-config-generator /user-info /app/
COPY --from=lighttpd-config-generator /cgitrc /etc/cgitrc
ADD git-lighttpd.conf git-auth.conf /app/
ADD --chmod=755 lighttpd-wrapper /app/

VOLUME [ "/git" ]
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD [ "/app/lighttpd-wrapper" ]
