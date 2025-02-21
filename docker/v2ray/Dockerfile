FROM debian
RUN apt update && apt-get install -y tini unzip curl && rm -rf /var/lib/apt/lists/*
ADD --chmod=755 v2ray-wrapper.bash /app/
ADD v2ray-config.json.template /app/
COPY --from=share * /app/
WORKDIR /app
CMD ["/usr/bin/tini", "--", "/app/v2ray-wrapper.bash"]
