FROM debian:latest

WORKDIR /scripts
COPY *.bash /scripts/
RUN /scripts/install-code-server.bash

ENV LANG en_US.utf8
ENV CODE_SERVER_CONFIG="/data/code-server-config.yaml"
EXPOSE 8080
VOLUME [ "/root", "/data" ]
CMD [ "code-server", "--bind-addr", "0.0.0.0:8080" ]
