FROM alpine:latest

RUN apk add --no-cache alpine-sdk bash libstdc++ libc6-compat python3 curl nodejs npm && npm install -g n
RUN n 16 && npm config set python python3 && npm install --global code-server --unsafe-perm
ENV CODE_SERVER_CONFIG="/data/code-server-config.yaml"
WORKDIR /root
EXPOSE 8080
VOLUME [ "/data" ]
ENTRYPOINT [ "code-server", "--bind-addr", "0.0.0.0:8080" ]
