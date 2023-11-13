FROM debian:11

ARG IN_CHINA=
ENV IN_CHINA=${IN_CHINA}

ADD bootstrap /bootstrap

RUN /bootstrap/apt-source/setup.bash
RUN /bootstrap/setup-base.bash
RUN /bootstrap/setup-dev-tools.bash
RUN /bootstrap/setup-dev-tools-arm64.bash
# RUN /bootstrap/setup-sbuild.bash
# RUN /bootstrap/setup-sbuild-arm64.bash

VOLUME [ "/source", "/data" ]
CMD [ "bash", "-l" ]

