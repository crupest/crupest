FROM debian:11

ARG IN_CHINA=
ARG BUILD_FOR_ARCH=amd64
ENV IN_CHINA=${IN_CHINA}
ARG BUILD_FOR_ARCH=${BUILD_FOR_ARCH}

ADD bootstrap /bootstrap

RUN /bootstrap/setup.bash

VOLUME [ "/source", "/data" ]
CMD [ "bash", "-l" ]

