FROM denoland/deno AS deno-build
COPY --from=deno . /workdir/
WORKDIR /workdir
RUN deno install
RUN deno task compile:mail

FROM dovecot/dovecot:latest-root
COPY --from=deno-build /workdir/mail/out/crupest-mail /app/
ADD dovecot.conf /etc/dovecot/dovecot.conf
ADD app/* /app/
CMD ["/app/main.bash"]
