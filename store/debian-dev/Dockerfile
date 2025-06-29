ARG VERSION=latest
FROM debian:${VERSION}

ARG USER=
ARG CHINA=

ENV CRUPEST_DEBIAN_DEV_USER=${USER}
ENV CRUPEST_DEBIAN_DEV_CHINA=${CHINA}

ADD setup /setup
RUN export DEBIAN_FRONTEND=noninteractive; \
  /setup/apt.bash && /setup/package.bash && \
  /setup/for-container.bash && \
  rm -rf /var/lib/apt/lists/*


ENV LANG=en_US.utf8
USER ${USER}
WORKDIR /home/${USER}
RUN env DEBIAN_FRONTEND=noninteractive /setup/user.bash

VOLUME [ "/home/${USER}" ]
