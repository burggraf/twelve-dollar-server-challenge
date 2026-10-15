# syntax=docker/dockerfile:1
FROM rust:1.91.1-bookworm@sha256:c1e5f19e773b7878c3f7a805dd00a495e747acbdc76fb2337a4ebf0418896b33 AS app
RUN rustup target add wasm32-wasip2
WORKDIR /build
ENV CARGO_BUILD_JOBS=2
COPY services/trailbase/app/Cargo.toml services/trailbase/app/Cargo.lock ./
COPY services/trailbase/app/src ./src
RUN cargo test --locked && cargo build --locked --release --target wasm32-wasip2

FROM trailbase/trailbase@sha256:ab8f6d9dc943520b3902cdb7e6a8bd07f7701d34eea003a00897790bdd56d11c
# Pinned v0.34.6 multi-arch index: original ARM64 child unchanged; native AMD64 also supported.
ARG APP_SOURCE_SHA
LABEL benchmark.source_sha256=$APP_SOURCE_SHA
COPY --from=app /build/target/wasm32-wasip2/release/feed_benchmark.wasm /app/wasm/feed.wasm
USER root
RUN mkdir -p /app/traildepot && chown -R 1000:1000 /app/traildepot
USER 1000:1000
COPY services/trailbase/migrations /app/migrations/main
COPY services/trailbase/config.textproto /app/config.textproto
COPY --chmod=755 services/trailbase/entrypoint.sh /app/feed-entrypoint.sh
ENTRYPOINT ["tini", "--", "/app/feed-entrypoint.sh"]
