FROM debian:latest

ARG GIT_NAME=crupest
ARG GIT_EMAIL=${CRUPEST_EMAIL}
ENV GIT_NAME=$GIT_NAME
ENV GIT_EMAIL=$GIT_EMAIL

WORKDIR /scripts
COPY install-code-server.bash install-dev-tools.bash /scripts/
RUN /scripts/install-code-server.bash && /scripts/install-dev-tools.bash && rm -r /scripts

ENV LANG en_US.utf8
ENV CODE_SERVER_CONFIG="/data/code-server-config.yaml"
EXPOSE 8080
VOLUME [ "/root", "/data" ]
CMD [ "code-server", "--bind-addr", "0.0.0.0:8080" ]
