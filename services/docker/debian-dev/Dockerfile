FROM debian:latest

ARG USER=crupest
ARG IN_CHINA=

ENV CRUPEST_DEBIAN_DEV_USER=${USER}
ENV CRUPEST_DEBIAN_DEV_IN_CHINA=${IN_CHINA}

ADD bootstrap /bootstrap
RUN /bootstrap/setup.bash

ENV LANG=en_US.utf8
USER ${USER}
WORKDIR /home/${USER}

RUN --mount=type=secret,id=code-server-password,required=true,env=CRUPEST_CODE_SERVER_PASSWORD \
    mkdir -p ${HOME}/.config/code-server && \
    echo -e "auth: password\nhashed-password: " >> ${HOME}/.config/code-server/config.yaml && \
    echo -n "$CRUPEST_CODE_SERVER_PASSWORD" | argon2 $(shuf -i 10000000-99999999 -n 1 --random-source /dev/urandom) -e >> ${HOME}/.config/code-server/config.yaml

EXPOSE 4567
VOLUME [ "/home/${USER}" ]

CMD [ "tini", "--", "/usr/bin/code-server", "--bind-addr", "0.0.0.0:4567" ]
