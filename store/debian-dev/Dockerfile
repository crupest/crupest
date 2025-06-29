ARG VERSION=latest
FROM debian:${VERSION}

ARG USER=
ARG CHINA=

ENV CRUPEST_DEBIAN_DEV_USER=${USER}
ENV CRUPEST_DEBIAN_DEV_CHINA=${CHINA}

ADD setup /setup
RUN env DEBIAN_FRONTEND=noninteractive /setup/apt.bash
RUN env DEBIAN_FRONTEND=noninteractive /setup/package.bash
RUN env DEBIAN_FRONTEND=noninteractive /setup/for-container.bash

ENV LANG=en_US.utf8
USER ${USER}
WORKDIR /home/${USER}
RUN env DEBIAN_FRONTEND=noninteractive /setup/user.bash

VOLUME [ "/home/${USER}" ]
