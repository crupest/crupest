FROM ubuntu:latest

RUN curl -fsSL https://code-server.dev/install.sh | sh
ENV CODE_SERVER_CONFIG="/data/code-server-config.yaml"
WORKDIR /root
EXPOSE 8080
VOLUME [ "/data" ]
ENTRYPOINT [ "/usr/bin/code-server", "--bind-addr", "0.0.0.0:8080" ]
