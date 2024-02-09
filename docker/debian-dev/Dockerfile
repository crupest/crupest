FROM debian:11

ARG USERNAME=
ARG IN_CHINA=
ARG SETUP_SBUILD=

ENV USERNAME=${USERNAME}
ENV IN_CHINA=${IN_CHINA}
ENV SETUP_SBUILD=${SETUP_SBUILD}

ADD bootstrap /bootstrap

RUN /bootstrap/setup.bash

USER ${USERNAME}

VOLUME [ "/source", "/data", "/share" ]
CMD [ "bash", "-l" ]
