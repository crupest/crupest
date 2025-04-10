FROM denoland/deno AS deno-build
ADD relay /app/
WORKDIR /app
RUN deno install
RUN deno task compile

FROM dovecot/dovecot:latest-root
COPY --from=deno-build /app/out/crupest-relay /app/
ADD dovecot.conf /etc/dovecot/dovecot.conf
ADD app/* /app/
CMD ["/app/main.bash"]
