# Current primary host: isolated 16-GiB native AMD64 VPS

The owner designated this host for **all future BaaS product tests**, preserving its existing services. The SSH destination is kept in private operator state, not published here. The earlier Mac/8-GiB VPS measurements remain historical, unpooled tracks.

## Frozen primary budget

| Component | CPU quota | RAM | Container swap |
|---|---:|---:|---|
| Entire serving stack, `TIER=standard` | **1** | **4 GiB** | Disabled |
| k6, `k6-2cpu-8g-v3` | **2** | **8 GiB** | Disabled |

This is the owner-approved replacement primary baseline, not a claim that every BaaS will fit. Multi-container products must divide the **aggregate** serving budget among database, APIs, required functions/adapters/caches, and ingress. The older `small` (1 CPU/2 GiB) and `large` (4 CPU/4 GiB) tiers remain explicit historical configurations; never pool their holds with standard.

Read-only inventory: Ubuntu 24.04.5 LTS, native x86_64, **4 vCPUs**, **16,770,072,576 bytes RAM**, no swap; Docker client/server **29.8.1**. Initial available memory was **15,549,947,904 bytes** and root-disk available space **383,377,321,984 bytes**. The load average was 0.05/0.01/0.00. These are point-in-time observations, not dedicated-host guarantees.

The two load-time containers have combined ceilings of 3 CPUs/12 GiB. Preflight requires an additional **1 CPU and 1 GiB OS reserve**, rejecting insufficient CPU or memory before reset. Existing workloads must also have headroom. The four-CPU legacy serving tier cannot coexist fairly with this two-CPU runner on a four-CPU host; it is rejected, not silently oversubscribed.

## Isolation and preservation

- Workspace: `/opt/twelve-dollar-baas-benchmark-16g`, mode 0700, benchmark ownership marker.
- Project: `baas-trailbase-vps16`; images `baas-trailbase-vps16-{feed,tools}:0.1.0`; volume/network stay in that project namespace.
- Results: `results/trailbase/vps16-linux-amd64/`, separate from `vps-linux-amd64`.
- The existing **127.0.0.1:4000 listener is left untouched**. Benchmark HTTP is published only on **127.0.0.1:14000**, after checking availability. Container-internal HTTP remains port 4000. Admin ingress is not published.
- No existing service/container is stopped, restarted, reconfigured, adopted, or deleted. No host package installation, global Docker/plugin/power/firewall change, or global pruning.
- Read-only before/after snapshots retain existing systemd service identities/start times/restart counters and the port-4000 listener PID/start identity. Snapshots are private; summaries disclose any changes without claiming an unexplained change was caused by the benchmark.

The host already has global Compose 5.5.1/Buildx 0.37.1. They remain untouched. Project-private Compose **5.5.0** and Buildx **0.37.2**, matching the earlier host, are installed under the workspace `.docker/cli-plugins` after verifying the recorded official asset SHA256 digests. `DOCKER_CONFIG` applies only to benchmark commands. Digest verification is not a signature-verification claim.

## Native images and source

The application, SDK, schema, data algorithm, and app image inputs are unchanged. We transfer the **already built native AMD64 serving/tools images** from the earlier benchmark workspace, verifying archive SHA256 and the serving image's source label. No runtime volume, database, key, token, Docker credential configuration, or bootstrap log is transferred. New namespace tags are created only after collision checks.

Three Rust contract tests passed when that unchanged native app was compiled. That historical build evidence is retained; image reuse is not represented as a fresh compiler run on this host. All correctness and scored measurements are rerun here. This differs from the original upstream rule requiring a source build on each target, just as using pinned upstream BaaS images differs; this fork permits verified image reuse. If rebuilding is necessary, use the prior guide's pinned BuildKit image under a new benchmark-owned builder with **2 CPU/2 GiB/no swap**, stop it before tests/load, and record fresh build evidence.

Upload a sanitized source overlay on the recorded original Git base, excluding private/generated state and original Git remote/credential configuration. Verify transferred source checksums and `app_source_sha256` / `verification_source_sha256`. Never carry correctness attestations across hosts or profiles.

## Lifecycle environment

After isolated setup and verified image import, run in the source checkout:

```bash
export DOCKER_CONFIG=/opt/twelve-dollar-baas-benchmark-16g/.docker
export BENCHMARK_PROJECT=baas-trailbase-vps16
export BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3
export TIER=standard
export TRAILBASE_PORT=14000

bash services/trailbase/run.sh test
bash services/trailbase/run.sh bench --smoke --vus 10000  # unscored runner calibration
# Only after reviewing calibration and current-service continuity:
bash services/trailbase/run.sh bench --campaign --max-vus 20000 --max-attempts 12
```

The wrapper detects native AMD64 and derives the runner memory setting from the versioned profile. Direct Python benchmark invocations also explicitly propagate platform/project/profile/memory to Compose. Actual selected container manifest architecture/digest is recorded; Docker image-index inspection alone cannot establish the selected architecture.

Use bounded transient systemd units with durable private logs; no builds or competing tests during load. Full correctness must pass for the current source/image/tier before calibration/capacity. Each attempt resets the canonical data and retains source, attestation, raw compressed k6 samples, Linux host/resource counters, limits, and checksums. Invalid generator/monitor/host measurements pause the campaign, not define target failure. Search/three independent five-minute confirmations and human artifact review remain mandatory.

See [the benchmark contract](../../contracts/BENCHMARK.md) and [current results](../../results/trailbase/vps16-linux-amd64/README.md). No result from an earlier host, tier, or runner supplies a confirmation here. Monthly cost/region are not supplied, so no $12 equivalence or cost/request ranking is claimed.
