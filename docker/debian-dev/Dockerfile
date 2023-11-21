FROM debian:11

ARG IN_CHINA=
ENV IN_CHINA=${IN_CHINA}

ADD bootstrap /bootstrap

RUN /bootstrap/setup.bash

VOLUME [ "/source", "/data" ]
CMD [ "bash", "-l" ]

