# Tested software and VPS slice

Convex **precompiled-2026-10-06-a3538c6**, upstream **`a3538c6d212948f20726868e41d155d2534cd130`**, SDK/CLI **1.46.0**, native AMD64 image **`sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`**; bundled Node **22.22.2**, tools Node **22.20.0**. Backend `/version` literally **`unknown`**. Official PostgreSQL **17.11-bookworm / Debian17.11-1.pgdg12+2**, native AMD64 image **`sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`**.

Entire serving **1 vCPU / 4 GiB (4,294,967,296 bytes) / zero swap**, backend/executor **3 GiB (3,221,225,472 bytes)** and PostgreSQL **1 GiB (1,073,741,824 bytes)** sharing one aggregate parent. Separate **k6 1.3.0 / 2 vCPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, `k6-2cpu-8g-v3`, native AMD64 manifest **`sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656`**. Actual version `v1.3.0+dirty`, commit `5870e99ae8-dirty`, Go1.25.1. Untimed tools/controller each separately2CPU/4GiB/zero swap. Native `claudius.azabab.com`, shared-host slices, not dedicated/measured $12/month offerings; price/region unknown.

**These are short, unscored calibrations: neither a passing100 VUs nor a failing1,000 VUs establishes a capacity bound. Clean SIGINT shutdown remains FAILED139 under the explicit owner serving-path capacity exception.**

## Observations

The unchanged common smoke uses5-second initial ramp /20-second hold /5-second drain, ordinary original think times/endpoint mix/validation, ten-second request timeout and unchanged strict SLOs. Startup/in-flight mix differs from the full warmup/target ramp/300-second scored hold; do not compare or pool smoke quantiles with full campaigns.

| Unscored run | Hold requests / all-request RPS | p50 /p95 /p99 /max (ms) | Request errors / malformed successes | Outcome |
|---|---:|---|---|---|
| `20261016T014201034037Z-standard-1000vu-k6-2cpu-8g-v3-smoke` |1,492 /74.6 |10,000.310958999999 /10,000.9493206 /10,001.165257800001 /10,002.139757 |1,175 /0 |Valid completed measurement, **failed latency/error gates**, k6 threshold exit99 |
| `20261016T015709588263Z-standard-100vu-k6-2cpu-8g-v3-smoke` |220 /11.0 |13.1452135 /34.76025679999987 /97.40511321000004 /111.549268 |0 /0 |**Passed calibration**, k6 exit0 |

RPS counts **all requests, including errors**, not successful-throughput promises. Both original bundles and initial failure remain unchanged; no silent retry/reseed/redeploy/restart/resource/native-limit/SLO/cache change. The second run deliberately used a lower calibration load, not an independent same-VU confirmation or a search-bracket update. Initial launcher typo `--vus1000` was rejected before any attempt/reset/k6 and separately preserved in [preflight evidence](RUNNER_RESERVE_PREFLIGHT.md); it is not a third calibration.

### Endpoint evidence

All1,175 first-run hold errors carried raw HTTP status0, matching client timeout warnings—not inferred HTTP500s or a diagnosis of internal native errors:

- Feed1,186 requests:149status200 /1,037status0.
- Detail292:167status200 /125status0.
- Like10:one201 /nine status0.
- Createfour:all status0.

The whole preserved k6 log contains1,398 lines:1,394 exact request-timeout warnings across all phases, container creation lines, the explicit latency/error threshold failure and blank line. All other lines were reviewed; no filtering/rewrite of the170,208-byte original derivative was used to obtain a result. Hold counts differ correctly from all-phase log counts. A timed-out write is not proof it did not commit: the next native reset found exactly **seven posts /28 likes**, deleted those bounded application deltas and restored allocation500000, with all canonical native rows/hash reverified.

The100-VU hold had feed91status200/detail108status200/like20status201/createone201, zero request/schema errors. Both canonical prechecks passed allthree native dataset tests: first151.576s, second150.866s;50,000users /500,000posts /2,016,005likes, logical SHA **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`**. These are untimed full-canonical test durations, not request percentiles or timed SQL access. No platform/Auth/environment/settings/credentials/native storage reset occurred.

## Independent native raw/source/resource replay

A separate bounded read-only VPS audit consumed **all32,355 /4,941 raw JSON rows**, verified every original bundle checksum, reproduced every hold request/error/schema count and exact interpolated min/median/p95/p99/max, and replayed the unchanged common evaluator/resource verdict. All100 snapshotted source files per bundle matched current actual frozen VPS bytes; all full frozen inputs matched the accepted original correctness attestation. The larger1,555-file source/SDK/compiler/generated freeze is separately documented by the [full gate](FULL_FROZEN_CORRECTNESS.md); a selected per-run archive is not falsely described as that complete freeze.

Both had **eight actual kernel samples** showing runner `cpu.max=200000 100000`, `memory.max=8589934592`, `memory.swap.max=0`, correct native manifest/configuration, four common hold monitoring samples spanning15.110641241073608s /15.094961881637573s, no missing/error/incomplete-monitor invalidity and host swap-outs **0→0**.

Hold runner peak CPU **8.75% /6.19% of one core**, memory **3.83% /0.83% of8GiB**. First-run all-phase peak39.59% CPU/4.07% RAM is distinct from those hold-only peaks. Neither run had generator saturation or OOM. First-run serving component CPU samples sum near the one-core parent ceiling; pressure/throttling/raw host counters are preserved. This supports a quota-saturated serving observation, not an exact profiling/causal diagnosis of all latency.

Backend **PID2313635/start2026-10-16T00:02:20.333088398Z**, PostgreSQL **PID2313499/start2026-10-16T00:02:14.076467149Z** stayed unchanged, healthy, same containers/images/private inputs/budgets, observed native `/health`ok after each. New aggregate/child OOM counters0. Parent maximum sampled current bytes **4,112,297,984 /3,596,775,424**; first lifetime peak at immediate after profile **4,117,848,064**, subsequent retained lifetime peak **4,121,296,896** including trailing work. PostgreSQL lifetime child peak **1,073,954,816 bytes** exceeded its configured **1,073,741,824-byte** allowance; raw counter retained, not rounded away, blamed on an invented cause or added to nonsimultaneous child peaks. Configured allowance/current usage/lifetime peak remain separate.

The [original SIGINT139](NATIVE_SIGINT_SHUTDOWN_CRASH.md) is still failed; separate acknowledged crash recovery does not certify a clean lifecycle or provider power-loss durability. Compatibility JWTs use fresh per-request HS256 validation and are not native signup/login/session throughput. Supported native HTTP actions/private queries/mutations/native indexes/transactions/official PostgreSQL persistence remain the timed path; no application SQL driver, query-result/response/JWT cache, precomputed counts, replica or raised native read/write/time/resource limit.

## Next stage

After these complete reviews, the owner-authorized unchanged standard bounded search started:2,500VUs initially, doubling/narrowing250 (25 below250), maximum20,000VUs /12 full attempts and three independent confirmations. The external controller freezes its own source before the first hold, requires this exact passing raw-reviewed calibration/full frozen attestation, guards epochs and aggregate OOM across **entire reset+load** before/after each attempt, and never revives a server. Actual scored outcomes/final capacity and full audit belong in subsequent evidence. This calibration stage certifies none of them.

Original full files/samples/source archives remain on the VPS; public derivatives were screened against allseven actual private candidates across both preserved variants, JWT shapes and every HTTP query string, with original/derivative bytes/hashes/provenance. Complete installed SDK/source archives remain private pending distribution/license/privacy handling; no fresh-deployment/public-download claim is made.
