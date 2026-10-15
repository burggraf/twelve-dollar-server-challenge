# TrailBase VPS preflight — read-only

The owner requested trying the benchmark on their existing Contabo VPS after the Mac runs were paused for host instability. SSH access succeeded using existing authentication and strict host-key checking. No credentials or SSH material were copied into this repository or uploaded.

## Observed inventory (2026-10-14 UTC)

| Item | Observation |
|---|---|
| OS / architecture | Ubuntu 24.04.4 LTS, native Linux x86-64 |
| Logical CPUs | 4 |
| Physical/guest memory | 8,326,942,720 bytes (about 7.76 GiB) |
| Available memory at first check | 6,945,439,744 bytes; point-in-time, not a reservation |
| Swap | None configured |
| Root filesystem available | 92,758,757,376 bytes (about 86.39 GiB) |
| Docker client/server | 29.1.3 |
| Compose / Buildx plugins | Not installed; no legacy `docker-compose` binary |
| Existing workloads | Five running containers, including TrailBase 0.33.11 application/control, backup, and edge services |
| TCP port 4000 | No listener at inspection |
| Needed host tools | Python 3, Git, curl, and tar available |

The full command output, including existing workload names, is retained privately under `.state/vps/preflight.txt`. Public evidence intentionally omits the SSH destination and service-specific names. No container environments, process arguments, bootstrap logs, tokens, or private keys were collected.

## Owner-approved isolated setup

- Dedicated `/opt/twelve-dollar-baas-benchmark` directory and a unique Compose project/resource namespace. Refuse collisions; never reset or remove existing TrailBase containers/volumes.
- Project-private, pinned, checksum-verified Compose and Buildx plugins; no system-package/global Docker changes.
- Native-amd64 pinned TrailBase v0.34.6 and runner images, not ARM64 emulation. Preserve the same application, data, supported APIs, serving tier, and workload; pass the complete native correctness suite before load.
- Port 4000 bound to loopback only, no public ingress/firewall changes.
- Small serving tier 1 CPU / 2 GiB plus k6 profile `k6-2cpu-4g-v2` (2 CPU / 4 GiB / no container swap). Bounded builds happen outside load runs. Recheck current headroom and monitor Linux resource/swap/pressure evidence.
- Adapt the currently Mac/OrbStack-specific inventory and monitoring harness to Linux before use. The existing scripts must not be run unchanged and represented as valid VPS measurements.
- Keep VPS/x86-64 results in a separate deployment/architecture track, never pool them with local ARM64 OrbStack holds. This VPS hosts existing services and is not a dedicated benchmark machine; interference and potential service impact need owner approval.

The owner approved the dedicated setup and bounded small-tier builds/tests alongside existing services, with reasonable memory use and an offer of a separate 16-GiB VPS if needed. Project-private Compose v5.5.0 and Buildx v0.37.2 were installed after published SHA256 verification; no global/system plugin configuration was changed. Linux monitoring/platform/namespace regression tests now pass locally. Sanitized source and its original shallow base commit have now been uploaded and checksum-verified after namespace collision checks. This historical 8-GiB host passed native correctness/calibration and 2,500/5,000-VU search holds before runner OOM at 10,000 paused the campaign. All raw artifacts were retrieved and checksummed; only the obsolete benchmark-owned target was stopped afterward, preserving its volume and every unrelated service. No maximum or final acceptance exists. The owner designated the [16-GiB host](vps16-linux-amd64/README.md) for all future product tests, now with a common 1-CPU/4-GiB serving budget and 2-CPU/8-GiB runner. See [historical evidence](vps-linux-amd64/README.md). See [the VPS operations guide](../../services/trailbase/VPS.md). Existing service containers have not been changed. Larger-tier testing is not proposed on this memory budget. No VPS score, cost claim, final outcome, or later-service progression is established.
