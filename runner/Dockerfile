FROM rust:1.91.1-bookworm@sha256:c1e5f19e773b7878c3f7a805dd00a495e747acbdc76fb2337a4ebf0418896b33 AS certificates
FROM node:22.20.0-bookworm-slim@sha256:b21fe589dfbe5cc39365d0544b9be3f1f33f55f3c86c87a76ff65a02f8f5848e
# The slim Node image has no CA package: bootstrap trust from another pinned image,
# not by disabling certificate or package-signature verification.
COPY --from=certificates /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
# Freeze apt resolution too, rather than taking today's drifting package set.
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf 'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20251210T000000Z bookworm main\ndeb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/20251210T000000Z bookworm-security main\n' > /etc/apt/sources.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends bash ca-certificates curl jq openssl python3 sqlite3 \
 && dpkg-query -W > /tool-packages.txt \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["bash"]
