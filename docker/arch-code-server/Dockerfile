FROM node:alpine

RUN apk add --no-cache alpine-sdk bash libstdc++ libc6-compat && npm config set python python3 && npm install --global code-server --unsafe-perm
WORKDIR /root
EXPOSE 8080
VOLUME [ "/data" ]
ENV CODE_SERVER_CONFIG="/data/code-server-config.yaml"
ENTRYPOINT [ "code-server", "--bind-addr", "0.0.0.0:8080" ]
