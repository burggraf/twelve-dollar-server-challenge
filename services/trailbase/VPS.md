# Native Linux VPS track

This is a separate deployment/architecture track from local ARM64 OrbStack. The owner approved an isolated setup on their existing x86-64 VPS and bounded small-tier tests alongside existing services. Do not stop those services or describe this as a dedicated machine. Monthly VPS price has not been supplied; do not invent cost/request or call it a $12 VM.

## Isolation and pins

- Workspace: `/opt/twelve-dollar-baas-benchmark/src`; parent ownership marker `.benchmark-owned` and mode 0700.
- Project-private Docker CLI config/plugins: `/opt/twelve-dollar-baas-benchmark/.docker`, never `/root/.docker` or system plugin paths.
- Compose **v5.5.0**, official `docker-compose-linux-x86_64`, SHA256 `c57ab918abd5b05ca7e7d0f275875dd1330a695074f309dc9eab1b49efafcd4b`.
- Buildx **v0.37.2**, official `buildx-v0.37.2.linux-amd64`, SHA256 `982ca20490b45ed1ec8d99795974d3d874a358f75938c9c237305010e6b7e548`.
- Both plugins are downloaded over verified HTTPS from their official versioned GitHub releases and checked against these published asset digests **before execution**. This is checksum verification, not a claim that signatures were verified.
- Native-amd64 BuildKit **v0.33.1**, `moby/buildkit@sha256:98cc6a3fc46220d00f8224ae483f3274fc874e9be8d7dd1e2e2c5481209228b5`.
- TrailBase v0.34.6 multi-arch index `sha256:ab8f6d9dc943520b3902cdb7e6a8bd07f7701d34eea003a00897790bdd56d11c`; AMD64 child `sha256:c35590c8016bda42aff7157aa617aa91301cd1f5e29a9db594519b05602b8de5`. The original ARM64 child is unchanged. Rust/Node/k6 pins already support native AMD64.
- Namespace: `baas-trailbase-vps`. Before first deployment, reject existing containers/volumes/networks/images with this namespace; do not adopt or replace unknown resources. New images are `baas-trailbase-vps-feed:0.1.0` and `baas-trailbase-vps-tools:0.1.0`. Database volume: `baas-trailbase-vps_data`.
- Bind HTTP only to host loopback port 4000; native admin remains unpublished. Check the port before deployment. No firewall/public-ingress changes.

## Build and lifecycle

After installing the private plugins and placing the sanitized source checkout in the workspace:

```bash
cd /opt/twelve-dollar-baas-benchmark/src
export DOCKER_CONFIG=/opt/twelve-dollar-baas-benchmark/.docker
export BENCHMARK_PROJECT=baas-trailbase-vps
export BENCHMARK_BUILDER=baas-trailbase-vps-builder

docker buildx create --name "$BENCHMARK_BUILDER" --driver docker-container \
  --driver-opt image=moby/buildkit@sha256:98cc6a3fc46220d00f8224ae483f3274fc874e9be8d7dd1e2e2c5481209228b5 \
  --driver-opt memory=2g,memory-swap=2g,cpu-quota=200000,cpu-period=100000,restart-policy=no
# Refuse an unexpected preexisting builder; verify the created container's kernel
# cpu.max, memory.max, memory.swap.max before compiling.
docker buildx inspect --builder "$BENCHMARK_BUILDER" --bootstrap
bash services/trailbase/run.sh build
docker buildx stop --builder "$BENCHMARK_BUILDER"
# Also stop this builder on build errors. Never run builds concurrently with load.

bash services/trailbase/run.sh test
bash services/trailbase/run.sh bench --smoke --vus 5000
# Only after reviewing valid calibration/resource evidence:
bash services/trailbase/run.sh bench --campaign --max-vus 20000 --max-attempts 12
```

BuildKit is bounded to 2 CPU / 2 GiB / no swap; Cargo build concurrency is two. The serving tier remains 1 CPU / 2 GiB, k6 remains separately 2 CPU / 4 GiB / no swap. Recheck memory/CPU headroom before each run. The owner allows reasonable memory use but asked to be told if the available 16-GiB VPS is needed; do not silently overcommit this shared 8-GiB host. Larger-tier runs do not fit the current preflight.

Use a managed remote job/log with completion notifications; do not run a load process that will silently disappear on an SSH disconnection. Retain complete available evidence if a job is interrupted. Source transfers must exclude local `.state`, private keys/tokens, database files, and build output. Initialize synthetic keys/tokens on the VPS rather than transferring private local state. Preserve the recorded shallow base Git commit plus source overlay for provenance; no new commit is needed.

## Linux measurements and results

The lifecycle detects native platform and rejects an emulated mismatch. Each inspected serving/load image must match it. The result root is `results/trailbase/vps-linux-amd64/`; local new runs use their own `local-orbstack-arm64/` track, while historical files remain unchanged.

The Linux monitor retains raw `/proc/vmstat`, `/proc/stat`, `/proc/meminfo`, `/proc/diskstats`, `/proc/loadavg`, `/proc/uptime`, and CPU/memory/I/O pressure files, alongside Docker samples. No process arguments/environments or bootstrap logs are collected. Swap-out checks use raw `pswpout`; missing counters, failed monitoring, generator saturation, and incomplete hold coverage remain invalid. Raw CPU steal/pressure must be reviewed for shared-VPS interference. Physical VPS thermals are not exposed; that limitation is disclosed, not replaced with fabricated readings.

The full native correctness suite and a valid calibration are prerequisites to capacity scoring. All data/reset/auth/workload/SLO/confirmation rules in [the benchmark contract](../../contracts/BENCHMARK.md) still apply. Keep Mac, original runner-v1, and VPS measurements separate; no maximum score exists until the required search, three independent holds, evidence review, and acceptance succeed.
