FROM alpine:edge

RUN apk add --no-cache tini v2ray

ADD config.json.template v2ray-wrapper.sh /app/

CMD [ "tini", "--", "/app/v2ray-wrapper.sh" ]
