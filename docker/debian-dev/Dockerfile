FROM debian:11

ADD bootstrap /bootstrap

RUN /bootstrap/replace-mirrors.bash
RUN /bootstrap/setup-base.bash
RUN /bootstrap/setup-dev-tools.bash
RUN /bootstrap/setup-dev-tools-arm64.bash
RUN /bootstrap/setup-sbuild.bash
RUN /bootstrap/setup-sbuild-arm64.bash

VOLUME [ "/data" ]
CMD [ "bash", "-l" ]

