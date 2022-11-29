FROM ubuntu:latest

ENV CODE_SERVER_CONFIG="/data/code-server-config.yaml"
WORKDIR /root
COPY install-code-server.bash /install-code-server.bash 
RUN /install-code-server.bash
EXPOSE 8080
VOLUME [ "/data" ]
ENTRYPOINT [ "code-server", "--bind-addr", "0.0.0.0:8080" ]
