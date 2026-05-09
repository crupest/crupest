ARG VERSION=latest
FROM debian:${VERSION}

ARG USER=
ARG CHINA=
ARG HERMES=

ENV CRUPEST_DEBIAN_DEV_USER=${USER}
ENV CRUPEST_DEBIAN_DEV_CHINA=${CHINA}
ENV CRUPEST_DEBIAN_DEV_HERMES=${HERMES}

ADD setup /setup
RUN chmod +x /setup/*.bash
RUN export DEBIAN_FRONTEND=noninteractive; \
    /setup/apt.bash && /setup/package.bash && \
    /setup/for-container.bash && \
    rm -rf /var/lib/apt/lists/*
RUN env DEBIAN_FRONTEND=noninteractive /setup/ttyd.bash

RUN if [ "${CRUPEST_DEBIAN_DEV_HERMES,,}" =~ ^(1|true|on)$ ]; then \
        curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | \
        env DEBIAN_FRONTEND=noninteractive bash; \
    fi

ENV LANG=en_US.utf8
USER ${USER}
WORKDIR /home/${USER}
RUN env DEBIAN_FRONTEND=noninteractive /setup/user.bash

VOLUME [ "/home/${USER}" ]
ENTRYPOINT [ "tini", "--" ]
CMD [ "bash", "/setup/main.bash" ]
