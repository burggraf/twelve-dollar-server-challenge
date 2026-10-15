# The native CGO-disabled executable is compiled/tested in the separately
# bounded, pinned Go builder. Build context: .state/pocketbase/build (feed only).
FROM debian:bookworm-slim@sha256:a4672c0cb26fbdde88e38fa2dfb6c681942306680e41e4378b28770b6e79ee91
ARG APP_SOURCE_SHA256
LABEL org.opencontainers.image.title="PocketBase native feed extension" \
      org.opencontainers.image.version="0.40.5" \
      org.opencontainers.image.revision="6f370ea741f33adf889eef02e3c1b884a47aa522" \
      benchmark.app-source-sha256="${APP_SOURCE_SHA256}"
RUN mkdir /data && chown 1000:1000 /data
COPY --chmod=0555 feed /usr/local/bin/feed
USER 1000:1000
EXPOSE 4000
ENTRYPOINT ["/usr/local/bin/feed"]
