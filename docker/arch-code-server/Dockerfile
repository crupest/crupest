FROM archlinux:latest

ARG CRUPEST_USER
ARG CRUPEST_GROUP
ARG CRUPEST_UID=1000
ARG CRUPEST_GID=1000
ARG CRUPEST_PACKAGES=""
ARG CRUPEST_AUR_PACKAGES=""
ARG USE_CHINA_MIRROR="false"
ARG CHINA_MIRROR_URL="https://mirrors.tuna.tsinghua.edu.cn/archlinux/\$repo/os/\$arch"

ADD ./archlinux-setup.bash ./archlinux-setup-user.bash ./restore-pacman-conf.py /tmp/

ENV CRUPEST_IN_DOCKER="true"
WORKDIR /tmp
RUN /tmp/archlinux-setup.bash
USER ${CRUPEST_UID}:${CRUPEST_GID}
WORKDIR /home/${CRUPEST_USER}
RUN /tmp/archlinux-setup-user.bash

VOLUME [ "/data" ]
EXPOSE 8080

ENV CODE_SERVER_CONFIG="/data/code-server-config.yaml"
ENTRYPOINT [ "code-server", "--bind-addr", "0.0.0.0:8080" ]
