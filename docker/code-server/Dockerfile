FROM debian:latest

WORKDIR /root
COPY install-code-server.bash /install-code-server.bash
RUN /install-code-server.bash

ENV LANG en_US.utf8
ENV CODE_SERVER_CONFIG="/data/code-server-config.yaml"
EXPOSE 8080
VOLUME [ "/data" ]
ENTRYPOINT [ "code-server", "--bind-addr", "0.0.0.0:8080" ]
