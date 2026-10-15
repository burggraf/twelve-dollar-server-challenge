# TrailBase: verified lower bound of 15,000 VUs

**Date:** 2026-10-15. **Outcome:** maximum discovery **blocked by the load generator**, with a verified **confirmed lower bound of 15,000 concurrent VUs** under the frozen workload/SLOs. **Not a maximum-capacity score. Owner authorized publication and progression to Supabase on 2026-10-15.**

Machine-readable result: [confirmed-lower-bound.json](confirmed-lower-bound.json). The owner authorized repository commit/push; publication of these artifacts is being executed. No release or unrelated upload is authorized.

## Result: three additional independent confirmations

Each attempt reset the canonical dataset, warmed for two minutes after the initial ramp, gradually ramped to 15,000 VUs over 60 seconds, scored a **300-second hold**, and drained. The initial 15,000-VU probe is **not** one of these three confirmations. No best-three selection or pooled/averaged latency quantiles.

| Confirmation | Hold requests | Requests/s | p50 ms | p95 ms | p99 ms | Maximum ms | Request/schema errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| [1](20261015T023034390461Z-standard-15000vu-k6-2cpu-8g-v3/report.md) | 476,047 | 1,586.82 | 0.91 | 24.38 | 62.20 | 229.95 | 0% / 0% |
| [2](20261015T024045880287Z-standard-15000vu-k6-2cpu-8g-v3/report.md) | 475,587 | 1,585.29 | 0.90 | 31.86 | 99.09 | 2,522.26 | 0% / 0% |
| [3](20261015T025057973204Z-standard-15000vu-k6-2cpu-8g-v3/report.md) | 476,024 | 1,586.75 | 0.90 | 24.94 | 93.65 | 2,192.65 | 0% / 0% |

**Total: 1,427,658 scored requests across 900 scored seconds**, zero request/schema errors. Per-hold throughput range **1,585.29–1,586.82 requests/s**. [Per-endpoint counts, errors, and p50/p95/p99](endpoint-confirmations.md) cover all four timed endpoint types in each hold.

All three passed the unchanged gates: **p95 <500 ms, p99 <1,000 ms, request errors <1%, zero malformed successful responses**. The multi-second maximum outliers remain in the raw evidence. A percentile pass does not mean every response took less than one second; these observations have not been causally attributed to the server, generator, storage, or shared host.

## What this does—and does not—establish

- Full five-minute search holds passed at **2,500, 5,000, 10,000**, then the backoff probe passed at **15,000**, all on this host/profile.
- The [20,000-VU attempt](20261015T015900985056Z-standard-20000vu-k6-2cpu-8g-v3/report.md) is **invalid**: k6 was OOM-killed, exit 137, under its **8-GiB limit**. TrailBase remained running without OOM/restart and with unchanged start identity. This supplies **no failing target bracket**.
- The short 10,000-VU calibration failed latency, while its later full warm/ramp/five-minute hold passed. Both protocols/outcomes are retained, not pooled or rewritten.
- Eight capacity attempts were used within the original 12-attempt/20,000-VU safety budget: four automatic search attempts, one backoff probe, three confirmations. No resource/code/threshold increase was made during this cohort.
- **15,000 is a confirmed tested lower bound, not a discovered TrailBase ceiling.** There is no maximum-VU ranking or numeric maximum score. Prior Mac/8-GiB-host/runner-v1/v2 measurements contribute no confirmations.

See [complete attempt/calibration history](README.md), the [original paused campaign](setup-evidence/campaign-job.log), and [confirmation role/state](setup-evidence/confirmation15000-state.json).

## Serving path, deployment, and resource contract

```text
k6 (separate 2-CPU / 8-GiB container)
  -> direct HTTP/1.1 over the owned Compose bridge
  -> TrailBase 0.34.6 native Rust WASM routes (published SDK 0.6.1)
  -> TrailBase-owned db::query / Transaction APIs
  -> SQLite WAL, synchronous=NORMAL, foreign keys enabled
```

There is no generic external application server/database driver, application response cache, materialized like counter, or JWT-verification cache. Normalized users/posts/likes and request-time counts are used; committed writes precede success. The five-endpoint common contract is implemented; health is used for readiness, not counted as a timed user-journey action.

- **Serving stack:** `standard`, **1 CPU / 4 GiB total**, no container swap. One TrailBase container includes platform storage, APIs, and WASM application work.
- **Runner:** `k6-2cpu-8g-v3`, **2 CPUs / 8 GiB**, no container swap; k6 1.3.0 pinned by image digest. Both requested limits and selected native AMD64 child manifests were checked; actual serving cgroups are retained.
- **Host:** owner-designated `azabab.com`, Ubuntu 24.04.5 LTS, native x86-64, **4 CPUs / 16,770,072,576 bytes RAM**, no swap, Docker 29.8.1. Container quota ceilings total 3 CPUs / 12 GiB; preflight reserves at least 1 CPU / 1 GiB and reviews existing workload headroom. Quotas are not dedicated physical cores or a dedicated-machine equivalent.
- **Isolation:** project `baas-trailbase-vps16`, owned volume/network/images. Benchmark host ingress is **127.0.0.1:14000**, leaving the pre-existing port-4000 listener untouched. No TLS, ingress proxy, or compression in the measured path.
- **Auth:** pre-issued synthetic HS256 identities; each write verifies the signature/expiry/payload inside the native handler. Native login/session throughput is not measured. Native Record APIs are read-only, with direct writes denied. No admin/signing credential is mounted into k6.
- **Workload:** feed/detail journeys with the original think/idle times, 15% like probability and 2% create probability per journey; real committed writes. Default 10-second timeout, no client retries/redirects. This is the stricter fork harness, not an unchanged upstream scoring script.

## Resource and shared-host review

The exact original scoring and monitoring functions were replayed against all three retained summaries/resource streams. Every run passed; source/image/log/checksum/native-platform/actual-limit proofs matched. Each hold has **50 generator monitoring samples**, spanning approximately **295.65–295.71 seconds**, satisfying the frozen boundary/gap checks.

| Hold | Runner CPU mean / peak (% of one core) | Runner peak RAM (% of 8 GiB) | Target peak CPU | Target peak RAM (% of 4 GiB) | Minimum host available RAM (KiB) | Host steal |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 103.00 / 201.36 | 87.54% | 90.59% | 14.23% | 7,177,676 | 0.0147% |
| 2 | 102.53 / 202.31 | 87.03% | 88.30% | 14.20% | 7,222,852 | 0.0104% |
| 3 | 98.28 / 200.07 | 87.11% | 87.24% | 14.82% | 7,170,056 | 0.0128% |

Runner quota is **200%**, not 100%; short Docker-stat spikes slightly above 200% are sampling observations, not increased quotas. None triggered the fixed **three consecutive samples >=180%** CPU rule or the **any hold sample >=90%** memory rule. Generator RAM is nevertheless close to its validity ceiling, so extrapolating to larger loads is not justified.

Host swap-outs remained **0→0** in every attempt. Aggregate host I/O wait was approximately **0.21%**; CPU pressure `some` was approximately **18.22–18.31%**, I/O pressure `some` approximately **0.34–0.35%**, and memory pressure effectively zero over the sampled hold spans. These raw counters are retained, not interpreted as proof of zero contention. No additional invalidating condition was identified in this evidence review. Provider scheduling/thermals and transient unobserved interference cannot be ruled out.

The final snapshot matched **all 26 pre-existing persistent service identities and the original port-4000 listener**. Root `user@0.service` SSH-session-manager PID changes are separately disclosed (`Linger=no`); this is not a broad application-service exception. Both owned confirmation/logger units are inactive after cleanup. [Machine-readable resource review](setup-evidence/confirmation15000-resource-review.json) and raw per-run `resources.jsonl` preserve exact values.

## Correctness and provenance

Fresh full native correctness passed at **1 CPU / 4 GiB** before this cohort: all **42 inherited checks**, six API/concurrency/auth/Unicode tests, native Record API permissions, storage failure/recovery and actual restart persistence, seed privacy, four workload tests, 24 scoring/host tests, and three isolation tests. The exact correctness log, attestation, log hash and verification-input hash accompany every run and were reverified after retrieval. The three Rust build tests are historical native build evidence; no new compilation on this host is claimed.

Canonical reset: **50,000 users / 500,000 posts / 2,016,005 likes**, SHA256 **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`**. Each attempt independently resets and validates application data before warm-up. Signing keys and time-dependent tokens are excluded from the data hash/publication.

TrailBase is pinned to **v0.34.6**, commit `8359b240cc4ae1d229738385bf42f8f40d5d59af`, Rust **1.91.1**, published SDK **0.6.1**, and locked dependencies. The unchanged native AMD64 app/tools images were hash-checked and reused from the earlier host, without transferring any runtime state/volume/credential. Full correctness and every scored hold were rerun on this host. Actual selected k6 AMD64 child digest: `sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656`.

The original Git base is `026bdb68d94d0d932bb5981321ad82c70618d752`, **not the complete uncommitted implementation**. Each run's `source.tar.gz` is a source overlay on that base, with `working-tree.patch`, source/image hashes and all raw checksums. Backend, benchmark, and verification source bytes in the three snapshots were compared to current frozen inputs. Issued-token patterns were excluded from reviewed text logs/manifests/patches; no credentials, environment dumps, bootstrap logs, or database volumes are published. GitHub CI has not been run in this session.

## Reproduction and retained evidence

Follow [the safe native-host guide](../../../services/trailbase/VPS16.md) for isolated setup, pinned images/private CLI, memory/CPU preflight, and bounded build options. Do not run this blindly on an unrelated host or overwrite existing services.

After setup, image/source validation and canonical full correctness, the same full-protocol single hold is:

```bash
cd /opt/twelve-dollar-baas-benchmark-16g/src
export DOCKER_CONFIG=/opt/twelve-dollar-baas-benchmark-16g/.docker
export BENCHMARK_PROJECT=baas-trailbase-vps16
export BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3
export TIER=standard TRAILBASE_PORT=14000
bash services/trailbase/run.sh test
python3 -u scripts/benchmark.py --vus 15000
```

For confirmation, run **three independent** single holds sequentially, without editing source or caps, stopping/reviewing on any failure or invalidity. Each command resets the data and runs the full timing sequence. The retained [bounded confirmation wrapper](setup-evidence/confirm-15000-remote.sh) records roles/budget/continuity and guards cleanup to owned resources; it is a record of this campaign, not an idempotent rerun command (it deliberately rejects changed attempt history/existing phase state).

Every run retains `report.md`, `summary.json`, full `k6-summary.json`, compressed **raw** `samples.json.gz`, raw resource JSONL, dataset/reset/correctness logs, source overlay, tracked patch, selected image/container limits/state, disk-growth observations, and original `SHA256SUMS`. Endpoint summaries and the final JSON are derived companions; raw artifacts were not rewritten or filtered. Final derived files have a separate report checksum manifest.

## Cost, limitations, and acceptance

Monthly price and region were not supplied; no cost/request figure or **$12 VM equivalence** is calculated. This is application throughput under a specific shared-host/container budget—not a comprehensive BaaS feature comparison, dedicated-server result, native auth/RLS benchmark, or proof of power-loss durability. WAL/NORMAL writes survived tested normal restarts; power-loss guarantees were not measured.

**Evidence review is complete. The owner authorized commit/push and direct progression to Supabase**, retaining this accurately labelled generator-limited outcome and the same serving/runner configuration. Maximum discovery remains blocked; this is not a numerical maximum score. PocketBase is deferred until after Supabase; no PocketBase application has been started.
