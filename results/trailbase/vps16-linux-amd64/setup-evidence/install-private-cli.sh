#!/usr/bin/env bash
set -euo pipefail
base=/opt/twelve-dollar-baas-benchmark-16g
test -f "$base/.benchmark-owned"
cd "$base/assets"
test ! -e "$base/.docker/cli-plugins/docker-compose"
test ! -e "$base/.docker/cli-plugins/docker-buildx"
curl -q -fsSL --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 300 https://github.com/docker/compose/releases/download/v5.5.0/docker-compose-linux-x86_64 -o docker-compose
curl -q -fsSL --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 300 https://github.com/docker/buildx/releases/download/v0.37.2/buildx-v0.37.2.linux-amd64 -o docker-buildx
printf '%s\n' 'c57ab918abd5b05ca7e7d0f275875dd1330a695074f309dc9eab1b49efafcd4b  docker-compose' '982ca20490b45ed1ec8d99795974d3d874a358f75938c9c237305010e6b7e548  docker-buildx' > CLI-SHA256SUMS
sha256sum -c CLI-SHA256SUMS
install -m 755 docker-compose "$base/.docker/cli-plugins/docker-compose"
install -m 755 docker-buildx "$base/.docker/cli-plugins/docker-buildx"
export DOCKER_CONFIG="$base/.docker"
{ docker compose version; docker buildx version; } > "$base/setup-evidence/private-cli-versions.txt"
cp CLI-SHA256SUMS "$base/setup-evidence/private-cli-checksums.txt"
echo VPS16_PRIVATE_CLI_VERIFIED
