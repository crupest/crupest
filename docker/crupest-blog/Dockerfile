FROM debian:latest
ARG CRUPEST_BLOG_UPDATE_INTERVAL=1d
COPY install-hugo.bash /install-hugo.bash
RUN /install-hugo.bash && rm /install-hugo.bash
ENV CRUPEST_BLOG_UPDATE_INTERVAL=${CRUPEST_BLOG_UPDATE_INTERVAL}
COPY daemon.bash update.bash /scripts/
VOLUME [ "/public" ]
ENTRYPOINT ["tini", "--"]
CMD [ "/scripts/daemon.bash" ]
