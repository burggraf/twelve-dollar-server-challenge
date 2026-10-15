# TrailBase — native AMD64 shared VPS track

**Status: 8-GiB host campaign paused at 10,000 VUs due to load-generator OOM; no target maximum measured. Historical track; all future product tests move to the 16-GiB host.**

The owner approved a new primary **1 CPU/4 GiB serving + 2 CPU/8 GiB runner** baseline on the [16-GiB native host](../vps16-linux-amd64/README.md). Full correctness, calibration, search, and confirmations restart there; no holds are pooled across hosts, tiers, or runner profiles. All completed attempts and raw/checksummed artifacts here are retained. No later BaaS has been started.

## Capacity campaign progress — not a final score

| Attempt | Hold | Requests / throughput | p95 / p99 | Errors | Outcome |
|---|---:|---:|---:|---:|---|
| [2,500 VUs](20261015T002336457284Z-small-2500vu-k6-2cpu-4g-v2/report.md) | 300 s | 79,424 / 264.75 requests/s | 4.63 / 15.12 ms | 0% request/schema | Automatic gates passed; not confirmation |
| [5,000 VUs](20261015T003407762465Z-small-5000vu-k6-2cpu-4g-v2/report.md) | 300 s | 158,750 / 529.17 requests/s | 7.54 / 24.09 ms | 0% request/schema | Automatic gates passed; not confirmation |
| [10,000 VUs](20261015T004436971373Z-small-10000vu-k6-2cpu-4g-v2/report.md) | Incomplete evidence | Not scored | Not scored | Not scored | **Invalid: k6 OOMKilled, exit 137** |

All full raw artifacts were retrieved after pause and every attempt checksum verified. At 10,000 VUs k6 reached a sampled 91.69% of its 4-GiB cap before OOM; TrailBase stayed running with no OOM/restart. Target start identity stayed unchanged during all three attempts. Runner peak RAM was 28.24% at 2,500 and 55.21% at 5,000. No failing target bracket or three-hold confirmation exists; neither 5,000 nor 10,000 is an established maximum. This track has not received final acceptance.

## Deployment and correctness

- Native Linux AMD64, Ubuntu 24.04.4, Docker 29.1.3; 4 logical CPUs and 8,326,942,720 bytes RAM; no guest swap. Existing application/control/backup/edge workloads share the VPS.
- TrailBase **v0.34.6**, published WASM SDK **0.6.1**, pinned native image/compiler/tooling inputs. Timed path remains k6 → native TrailBase WASM HTTP handlers → TrailBase query/transaction API → platform-owned SQLite.
- Small serving tier: **1 CPU / 2 GiB / no container swap**. Load generator: **`k6-2cpu-4g-v2`, 2 CPU / 4 GiB / no swap**. These are separate cgroups on the same host, not dedicated physical cores.
- Native build used a verified **2-CPU / 2-GiB / no-swap** BuildKit container, stopped before correctness/load. [Kernel limit evidence](setup-evidence/builder-cgroups.txt), [full build log](setup-evidence/native-build.log), and [job log](setup-evidence/native-job.log) are retained.
- [Current-source full native correctness](setup-evidence/revalidated-correctness.log) and [source/image attestation](setup-evidence/revalidated-correctness-manifest.json): 42 inherited checks, six API regressions, native Record API permissions, storage failure/recovery, actual restart persistence, four workload tests, seed privacy, **20 scoring/host/profile/native-boundary tests**, and two Compose isolation tests all passed. Three Rust contract tests passed during the unchanged app's image build. Initial pre-fix logs/attestation remain retained separately.
- Canonical dataset counts/hash match the original algorithm. Only the benchmark's application data/volume is reset; existing services are outside its namespace.

See [VPS setup and exact pins](../../../services/trailbase/VPS.md), [preflight/approval](../vps-preflight.md), and [the protocol](../../../contracts/BENCHMARK.md).

## Unscored calibration

| Run | Hold | Hold requests | Throughput | p50 / p95 / p99 | Errors | Outcome |
|---|---:|---:|---:|---:|---:|---|
| [Initial 5,000 VUs](20261015T000151314741Z-small-5000vu-k6-2cpu-4g-v2-smoke/report.md) | 20 s | 10,918 | 545.90 requests/s | 2.37 / 85.25 / 137.39 ms | 0% request/schema | Historical pass, **unscored**, pre-fix metadata caveat below |
| [Revalidated direct-controller 5,000 VUs](20261015T001908243915Z-small-5000vu-k6-2cpu-4g-v2-smoke/report.md) | 20 s | 11,089 | 554.45 requests/s | 2.00 / 57.78 / 88.51 ms | 0% request/schema | Pass, **unscored**, selected native manifests verified |

Both inspected serving/load images are `linux/amd64`. Target kernel limits read `100000 100000`, `2147483648`, `0`. Whole-attempt sampled peaks: runner CPU 198.56% and RAM 47.70% of its 4-GiB limit; target CPU 95.17% and RAM 13.17% of its 2-GiB limit. The sustained hold-saturation gate passed; a whole-attempt CPU peak is not a steady-state average. Raw guest swap-outs remained zero; sampled whole-attempt CPU steal delta was zero. These initial-run observations do not prove absence of provider-level interference or establish maximum capacity. The **revalidated** run sampled runner peaks of 148.74% CPU / 48.97% RAM and target peaks of 80.09% CPU / 12.42% RAM, with zero guest swap-outs. Its selected k6 manifest digest matches the pinned AMD64 child (`sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656`); its serving manifest also reports native AMD64. Correctness/source/log hashes and all run checksums were verified after retrieval. Neither short calibration is a score or a statistical comparison between revisions.

The run directory retains raw compressed k6 samples, endpoint summaries, resource JSONL, full correctness/reset logs, source snapshot/patch, manifests, and SHA256 checksums. Retrieved files and the current-source correctness attestation were verified locally. No token/key/database/bootstrap-log transfer or public upload was performed.

## Capacity launcher fault — retained invalid attempt

The [first 2,500-VU attempt](20261015T001026590201Z-small-2500vu-k6-2cpu-4g-v2/report.md) never ran the workload: k6 exited **255**, with `exec /usr/bin/k6: exec format error`. No runner OOM occurred. The original missing-clock reason and all raw artifacts remain unchanged; no hold or capacity conclusion can be drawn.

The direct Python controller inferred native AMD64 but did not export that choice to Compose, which fell back to the YAML's historical ARM64 default. A create-only ARM64 probe also demonstrated a Docker 29 metadata trap: `.Image` named a multi-arch index, and `docker image inspect` reported its default AMD64 choice even though the actual container's `ImageManifestDescriptor.platform` was ARM64. The diagnostic probe was never started and was removed.

The fix explicitly propagates platform/project to every Compose subprocess and uses the **container-selected manifest** for architecture verification, retaining its digest. An incomplete descriptor fails closed; concrete-image inspection is only a legacy-engine fallback. Two regressions first reproduced the missing subprocess environment and wrong-architecture verdict, then passed with the fix (20 scoring/host tests total; two isolation and four workload tests also pass). Full native correctness and direct-controller calibration were rerun successfully after the verification inputs changed; the app/image inputs were unchanged, so no image rebuild was needed.

The earlier calibration's wrapper explicitly selected native AMD64, but its `platform` field alone should not be used as authoritative selected-manifest proof. It remains historical and unscored; the new calibration retains the selected digest and successfully exercises the formerly failing direct-controller path. No historical manifest was rewritten.

## Existing-service continuity and shared-host caveats

The bounded campaign lifecycle log recorded **one pre-existing unrelated container** receiving SIGTERM/clean exit 0 and stop/start during the campaign. Its cause is unknown; benchmark lifecycle commands targeted only benchmark-owned containers. Passing automatic gates do not establish uninterrupted unrelated services or absence of shared-host interference. The original minimal lifecycle stream is retained in setup evidence, without process arguments or environments.


The existing five containers' IDs/start times/restart counts matched immediately before and after the build. A later audit found one pre-existing application had a newer start time, **00:05:32 UTC**, after calibration finished at **00:03:57 UTC**. Available lifecycle events show SIGTERM and exit 0, not an OOM. The cause is unknown; the benchmark setup issued no modify/stop/restart operation against that application. Do **not** interpret the build-only continuity check as proof that all five services remained unchanged throughout the wider review period, or infer absence of other activity from partial event history.

The capacity job now records container **start/stop/die/kill only** in an owned, bounded-lifetime event logger for later review. Exec events are excluded because they can contain command arguments. Raw CPU/steal/memory/I/O/pressure metrics remain necessary; changes/interference must be reviewed before accepting a score. Physical provider thermals and hypervisor-host swap are not observable from this guest. Shared production services remain untouched by our lifecycle commands, but shared CPU/I/O contention can still affect them and the measurement.

Monthly VPS price/region have not been supplied, so cloud cost/request is **not calculated** and no original `$12` equivalence is claimed. Mac ARM64, historical 2-GiB-runner, and VPS holds are separate cohorts, never pooled into confirmation. Larger-tier benchmarking does not fit this VM's reserved-headroom preflight; the owner offered a 16-GiB VPS if needed.

Publication is local repository evidence only. No commit, push, public release, accepted final outcome, or PocketBase work has occurred.
