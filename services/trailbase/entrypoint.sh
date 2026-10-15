#!/bin/sh
set -eu
umask 077
mkdir -p /runtime
cp /run/secrets/jwt_secret /runtime/jwt-secret
date +%s > /runtime/started-at
# The depot lives in a named Docker volume. Baked app assets are immutable/read-only.
mkdir -p /app/traildepot/wasm /app/traildepot/migrations/main
cp /app/wasm/feed.wasm /app/traildepot/wasm/feed.wasm
cp /app/migrations/main/*.sql /app/traildepot/migrations/main/
cp /app/config.textproto /app/traildepot/config.textproto
exec /app/trail --data-dir /app/traildepot run --address 0.0.0.0:4000 \
  --admin-address 127.0.0.1:4001 --runtime-root-fs /runtime \
  --runtime-threads "${RUNTIME_THREADS:-1}"
