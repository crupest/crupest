FROM debian:11

ARG IN_CHINA=
ENV IN_CHINA=${IN_CHINA}

ADD bootstrap /bootstrap

ENV DEBIAN_FRONTEND=noninteractive
RUN /bootstrap/setup.bash

VOLUME [ "/source", "/data" ]
CMD [ "bash", "-l" ]

