FROM debian
RUN apt-get update && apt-get install -y \
    tini curl openssl && \
    rm -rf /var/lib/apt/lists/*

COPY --chmod=755 install-dufs.bash main.bash /app/
COPY dufs-config.yaml.template /app/
RUN /app/install-dufs.bash

CMD [ "tini", "--", "/app/main.bash" ]
