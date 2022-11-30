FROM klakegg/hugo:ext-alpine
# install git
ARG CRUPEST_BLOG_UPDATE_INTERVAL=1d
RUN apk add --no-cache coreutils tini bash git
ENV CRUPEST_BLOG_UPDATE_INTERVAL=${CRUPEST_BLOG_UPDATE_INTERVAL}
COPY daemon.bash update.bash /
VOLUME [ "/blog/public" ]
ENTRYPOINT ["/sbin/tini", "--"]
CMD [ "/daemon.bash" ]
