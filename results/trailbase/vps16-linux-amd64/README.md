# TrailBase — current 16-GiB native AMD64 primary track

**Status: full five-minute holds passed through 15,000 VUs. All three additional independent 15,000-VU confirmation holds passed. Full artifact/checksum/source/resource review is complete: [verified lower-bound report](CONFIRMED_LOWER_BOUND.md) and [machine-readable result](confirmed-lower-bound.json). The owner authorized commit/push and progression to Supabase. No target maximum is claimed.**

The original four-attempt campaign paused invalid on generator OOM at 20,000. The full **15,000-VU** probe then passed as attempt **5 of the existing 12-attempt budget**, with no code/resource/threshold changes. Managed phase `trailbase-vps16-confirm-15000-three-holds` retained/verified that probe and completed **three additional independent full-protocol 15,000-VU holds**, all passing (attempts 6–8, one-hour hard cap). Any failed/invalid hold pauses the phase; no best-three selection. All three passing plus human/resource/continuity review can establish a **confirmed lower bound**, never a maximum, because 20,000 generator OOM supplies no target-failure bracket.

The owner designated this host for all BaaS tests moving forward and changed the common serving budget to **1 vCPU / 4 GiB aggregate RAM** (`standard`). The separate runner is **2 vCPUs / 8 GiB** (`k6-2cpu-8g-v3`); both have container swap disabled. This replaces, rather than pools with, the historical 2-GiB serving results.

## Full capacity campaign progress — not a final score

| VUs | Scored hold | Requests / throughput | p95 / p99 | Errors | Result |
|---:|---:|---:|---:|---:|---|
| [2,500](progress/20261015T012840173938Z-standard-2500vu-summary.json) | **300 s** | 79,401 / 264.67 requests/s | 0.95 / 2.44 ms | 0% request/schema | Pass; search attempt, not confirmation |
| [5,000](progress/20261015T013845471643Z-standard-5000vu-summary.json) | **300 s** | 158,849 / 529.50 requests/s | 1.23 / 8.06 ms | 0% request/schema | Pass; search attempt, not confirmation |
| [10,000](progress/20261015T014851697125Z-standard-10000vu-summary.json) | **300 s** | 317,156 / 1,057.19 requests/s | 7.15 / 21.76 ms | 0% request/schema | Pass; search attempt, not confirmation |
| [15,000](progress/20261015T021146350933Z-standard-15000vu-summary.json) | **300 s** | 475,756 / 1,585.85 requests/s | 23.05 / 65.35 ms | 0% request/schema | Pass; resource-backoff probe, not confirmation |

**20,000 VUs: invalid — k6 OOMKilled=true, exit 137, at its 8-GiB cap.** TrailBase remained running under 1 CPU/4 GiB, with no OOM/restart and unchanged start identity. This is a generator limitation, not a failing TrailBase capacity point. The post-campaign snapshot matched all 26 persistent system-service identities and the original port-4000 listener. Full campaign artifacts are now retained locally with verified source/log/run checksums; the 15,000-VU resource-validity probe passed at the same caps and full five-minute protocol. Its generator hold peak RAM was **87.07% of 8 GiB** and CPU peak **201.01%** (brief quota-level spikes; no three-consecutive-sample saturation invalidation). With limited generator headroom, the next phase confirms 15,000 rather than increasing allocation. Post-probe comparison again matched all 26 persistent services and the original port-4000 listener.

Unlike the earlier failed short 10,000-VU calibration, the full warmed/ramped 10,000-VU hold passed; both outcomes remain retained and are not pooled. This table is separate from the short calibration results below. Full raw attempts remain retained on the VPS; only small exact summaries are copied during load to avoid bulk transfer interference. Search, three independent confirmation holds, final resource/continuity review, and acceptance are still pending.

## Independent 15,000-VU confirmation holds — 3/3 passed

These are three **additional** full-protocol attempts, not reuse of the earlier search/probe hold.

| Hold | Requests | Throughput | p95 / p99 | Errors | Result |
|---|---:|---:|---:|---:|---|
| [1/3](progress/20261015T023034390461Z-standard-15000vu-summary.json) | 476,047 | 1,586.82 requests/s | 24.38 / 62.20 ms | 0% request/schema | Pass, 300-second scored hold |
| [2/3](progress/20261015T024045880287Z-standard-15000vu-summary.json) | 475,587 | 1,585.29 requests/s | 31.86 / 99.09 ms | 0% request/schema | Pass, 300-second scored hold |
| [3/3](progress/20261015T025057973204Z-standard-15000vu-summary.json) | 476,024 | 1,586.75 requests/s | 24.94 / 93.65 ms | 0% request/schema | Pass, 300-second scored hold |

Hold 2 recorded a **2,522.26-ms maximum** tail outlier and hold 3 a **2,192.65-ms maximum**, retained for final resource/tail review. The predefined latency gates are p95/p99, not maximum latency; all passed unchanged. The full post-phase snapshot matched all 26 persistent services and the original port-4000 listener; both owned systemd units are inactive after cleanup. Raw-resource/source/checksum review is complete and the owner authorized publication/progression. See the [final report](CONFIRMED_LOWER_BOUND.md); no maximum is claimed.

## Host and preservation

- Ubuntu 24.04.5 LTS, native AMD64, **4 vCPUs / 16,770,072,576 bytes RAM**, no swap; Docker 29.8.1.
- Initial available memory **15,549,947,904 bytes**, root disk available **383,377,321,984 bytes**; point-in-time load average 0.05/0.01/0.00.
- Existing services are not modified. A read-only baseline captured **27 running systemd service identities** and one process listening on **127.0.0.1:4000**. Private snapshots exclude process arguments, environments, and configuration. After setup/full correctness/initial calibration, all **26 persistent service identities** and the original port-4000 listener PID/start identity matched. The root login manager (`user@0.service`) changed PID between SSH sessions; `Linger=no`, success status, and private journal lifecycle records explain this normal session-bound difference. Benchmark commands did not stop or reconfigure existing application services; snapshots are retained, not rewritten to hide this distinction.
- Benchmark uses its own `baas-trailbase-vps16` project, volume/network/images/workspace, and **127.0.0.1:14000**. The existing port-4000 listener remains untouched.
- Global Compose 5.5.1 / Buildx 0.37.1 are untouched. Private pinned Compose 5.5.0 / Buildx 0.37.2 assets passed SHA256 verification.

## Current implementation evidence

The app/SDK/schema/data algorithm and native image inputs are unchanged. The prior native AMD64 serving/tools images were transferred, archive checksums verified, imported under new benchmark namespace tags, and source labels matched to the current sanitized source package. No runtime volume, database, token, key, or Docker credential configuration was transferred. Three Rust tests passed during that unchanged app's historical native build; this is not a claim of recompilation here.

Harness changes add the explicit `standard` tier, approved 8-GiB runner selection, per-host output separation, and CPU reserve preflight. **24 scoring/host tests and three resolved-Compose isolation tests passed under each runner profile**, plus four workload tests and syntax/diff checks. Red/green logs are retained in [implementation checks](../implementation-checks/). Fresh full API/native correctness passed on this host at the new standard tier. The first **unscored 10,000-VU** check completed with native images, matching kernel/Docker caps, no OOM/restart, and no guest swap-outs, but failed latency gates (p95 10,206.74 ms / p99 10,303.96 ms; one request error, zero schema errors). Its short 5-second ramp/20-second hold is not the full capacity warm-up/ramp or a maximum score. All evidence is retained. Runner peak RAM was 41.57% of 8 GiB; target peak was 45.50% of 4 GiB. The [follow-up 5,000-VU calibration](20261015T012102394670Z-standard-5000vu-k6-2cpu-8g-v3-smoke/report.md) passed: **11,106 hold requests / 555.30 requests/s**, p50 **0.67 ms**, p95 **7.39 ms**, p99 **31.59 ms**, zero request/schema errors. The [failed 10,000-VU short calibration](20261015T011353569718Z-standard-10000vu-k6-2cpu-8g-v3-smoke/report.md) remains unchanged. Neither is a scored hold; full capacity warm-up/ramp/search starts afresh. Workload/SLOs/data/auth/confirmation rules remain unchanged.

Current-source correctness/source/log hashes, all calibration checksums, selected native AMD64 k6 child digest, actual 4-/8-GiB limits, and unchanged target start identities were verified after retrieval. [Full native correctness](setup-evidence/correctness.log), [attestation](setup-evidence/correctness-manifest.json), and [persistent-service continuity summary](setup-evidence/continuity-5000-summary.json) are retained. No runtime state or issued tokens were published.

## Historical predecessor — not this score

The [8-GiB VPS campaign](../vps-linux-amd64/README.md) passed independent five-minute search holds at 2,500 and 5,000 VUs under **1 CPU/2 GiB serving + 2 CPU/4 GiB runner**. At 10,000 VUs the load generator was OOM-killed (exit 137); TrailBase remained running with no OOM/restart. The campaign paused invalid, not at a measured target maximum. All three attempts and raw/checksummed evidence are retained. Neither those holds nor the older Mac attempts supply confirmations here.

See [setup and safe lifecycle](../../../services/trailbase/VPS16.md), [benchmark contract](../../../contracts/BENCHMARK.md), and [master plan](../../../MASTER_PLAN.md). Full correctness, calibration review, bounded search, three independent five-minute confirmations, resource/service-continuity review, publication, and acceptance remain required. No later BaaS has been started; no commit/push/public release occurred.
