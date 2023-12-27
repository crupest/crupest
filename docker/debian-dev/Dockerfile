FROM debian:11

ARG IN_CHINA=
ARG SETUP_SBUILD=

ENV IN_CHINA=${IN_CHINA}
ENV SETUP_SBUILD=${SETUP_SBUILD}

ADD bootstrap /bootstrap

RUN /bootstrap/setup.bash

VOLUME [ "/source", "/data" ]
CMD [ "bash", "-l" ]

