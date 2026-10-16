# Tested software and VPS slice

Convex **precompiled-2026-10-06-a3538c6**, upstream **`a3538c6d212948f20726868e41d155d2534cd130`**, SDK/CLI **1.46.0**, native Linux AMD64 manifest **`sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`**. Bundled Node **22.22.2**, untimed tools Node **22.20.0**. Backend `/version` literally **`unknown`**. Official PostgreSQL **17.11-bookworm / Debian17.11-1.pgdg12+2**, native AMD64 manifest **`sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`**.

Entire serving **1 vCPU / 4 GiB (4,294,967,296 bytes) / zero swap**, backend/bundled executor **3 GiB (3,221,225,472 bytes)** plus PostgreSQL **1 GiB (1,073,741,824 bytes)** under one aggregate parent, **not two serving cores**. Separate runner **k6 1.3.0 / 2 vCPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, `k6-2cpu-8g-v3`, native AMD64 manifest **`sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656`**; actual build `v1.3.0+dirty`, commit`5870e99ae8-dirty`, Go1.25.1. Untimed tools/controller each separately capped2CPU/4GiB/zero swap. Execution on `claudius.azabab.com`, shared-host quota slices, **not dedicated/measured $12/month VPS offerings**; price/region unknown.

## Accepted outcome: blocked/unscored

**No confirmed capacity, lower bound or maximum is published.** The first full2,500-VU attempt ended with a **new serving-backend OOM kill** under the frozen backend3-GiB/PG1-GiB split. The campaign stopped without recovery. The owner explicitly chose **publish blocked/unscored, cleanly stop only the remaining owned PostgreSQL, preserve all volumes/inputs, then advance to Nhost feasibility**.

This is evidence about the tested release, native path, exact split and load—not proof that all lower loads, all4-GiB allocations or all Convex deployments fail. The earlier **clean SIGINT shutdown FAILED139 remains a separate unresolved failure**. The exception permitting measurement despite that known teardown failure was not permission to revive this new OOM.

## Gates completed before load

The native application implements the original feed/detail/create/like/health contract using supported HTTP actions → private native queries/mutations → native document/index/transaction APIs → official PostgreSQL persistence. No timed application-side SQL driver, external compatibility server, query-result/response/JWT cache, precomputed like counter or replica. Ordinary database/index/module/page caches remain enabled. Native read/write/transaction/time/resource defaults were not raised.

- [Native original contract/reset](../implementation-checks/ORIGINAL_CONTRACT_AND_NATIVE_APPLICATION_RESET.md), transactional concurrent writes, stored signed64/Unicode/NUL/orphan-feed/collision cases passed. These are logical native invariants, **not physical SQL FK/UNIQUE declarations**.
- [Full current source/runtime freeze and full functional/harness gate](../implementation-checks/FULL_FROZEN_CORRECTNESS.md): original unchanged42 +112 Python +Node4 executed checks passed, including fullshared6. These overlap earlier stage coverage and are not added across reports. Native reset/full canonical hash restored50,000users /500,000posts /2,016,005likes, logical SHA **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`**.
- Complete1,555-file current source/harness archive,2,412 dependency/compiler entries/five generated files, SDK/native esbuild/compiler/runtime/image/schema/function metadata and20,000 original-generator compatibility fixtures frozen. Full source, archives, installed runtime and private configuration were unchanged at read-only postmortem. Complete archives remain **private pending distribution/license/privacy handling**: no public-download/fresh-deployment claim.
- [Native runner/reserve preflight](../implementation-checks/RUNNER_RESERVE_PREFLIGHT.md) passed; [two unscored calibrations](../implementation-checks/UNSCORED_CALIBRATIONS.md) independently replayed.1,000VU failed target latency/errors;100VU passed220requests/p9534.76ms/p9997.41ms/zero errors. **Neither is a capacity bound or full independent confirmation.**
- Fresh per-request synthetic HS256 compatibility verification; this is **not native signup/login/session throughput**. Separate older acknowledged crash-recovery41 checks are not proof of clean lifecycle, this new OOM's data survival or provider power-loss durability.

The original SQLite feasibility configuration separately failed timeout/later serving OOM; its stopped container/volume/private inputs remain preserved. It is not silently merged with this PostgreSQL variant.

## First and only full attempt

**`20261016T020607016365Z-standard-2500vu-k6-2cpu-8g-v3`** used the unchanged common30s initial ramp /120s warm hold≤1,000VUs /60s target ramp /300s scored hold /30s drain, ten-second request timeout, think times and validators. Strict gates remain p95<500ms /p99<1,000ms /request errors<1% /malformed successful responses0.

| Diagnostic hold metric | Actual observation—not a capacity score |
|---|---:|
| Requests |50,812 |
| All-request RPS |169.37333333333333 |
| Expected successful responses |**0** |
| Request errors |50,812 /100% |
| Endpoint/status |**All feed /all status0** |
| Median /p95 /p99 (ms) |10,000.1612255 /10,000.948015799999 /10,001.55330185 |
| Minimum /maximum (ms) |0 /10,051.829707 |
| Malformed successful responses |0, **vacuous with no successful hold responses** |

The RPS includes timeouts and post-crash connection failures, **not successful throughput**. Failed initial feed journeys did not progress to a successful mixed endpoint workload. Status0 is a client-level result, not an invented HTTP500. No request-body/timeout/native-limit modification was made to manufacture a passing outcome.

A separate read-only VPS replay consumed **all1,116,907 original raw rows**, verified every original checksum and100 snapshotted source-file bytes against frozen VPS files, reproduced every hold request/error/status and exact interpolated min/median/p95/p99/max, and replayed the common scorer/resource verdict. Common SLO replay failed; the native adapter additionally classified and raised the real serving-runtime failure. This is diagnostic failure replay, **not acceptance of a healthy capacity measurement**. The raw helper's generic `not_capacity_bound:false` is merely its original `smoke`-mode flag; it does not override this final blocked classification or certify a bound.

The full search had an upper budget20,000VUs /12 attempts and three independent confirmations, but did not reach narrowing or confirmations. **One physical full attempt consumed one slot**: the adapter raised before the common controller appended history, leaving the preserved campaign JSON `paused` with `attempts:[]`. That empty array does not erase this run or authorize a reset/retry. No second full attempt or recovery ran.

## Actual OOM evidence

The backend retained the original container/image, PID **2313635**, start **2026-10-16T00:02:20.333088398Z**, then Docker recorded **exit137 /OOMKilledtrue /PID0**, finished **2026-10-16T02:17:16.296405591Z**. Kernel at **02:17:15.907745Z** explicitly identifies `CONSTRAINT_MEMCG` in the **backend child3-GiB cgroup**, victim `convex-local-ba` PID2313635. The child usage and limit were each **3,145,728KiB**; killed process anon-RSS **3,034,760KiB**, file-RSS **88,832KiB**. Bundled Node was in that same serving child.

The aggregate's propagated counters changed **oom0→3 /oom_kill0→1 /group_kill0→0**; three OOM events are **not three process kills**. Parent configured memory **4,294,967,296 bytes**, maximum sampled current **4,294,729,728**, retained raw lifetime peak **4,295,045,120**. Preserve the77,824-byte raw peak overshoot rather than rounding it away or inventing a cause. The kernel identifies the child constraint; do not relabel it solely as an aggregate-limit kill or assume a different split would have the same outcome.

Actual allocation mechanism/leak/causal chain was not profiled. PostgreSQL also logged **“FATAL: sorry, too many clients already”** during overload; this is retained, not fixed by raising connection limits or claimed to prove the exact cause of memory growth. The stopped native deployment was not revived for diagnostics or data cleanup.

## Runner and shared-host limitations

The runner completed without OOM, pinned native image/configured limits and actual kernel2CPU/8GiB/zeroSwap records. Hold monitoring had **59 samples spanning290.98219990730286s**, no failed/missing/incomplete-monitor invalidity, sampled peak CPU **93.53% of one core** and memory **13.81% of8GiB**, host swap-outs **0→0**. Actual kernel-limit values appear in109 monitor records; post-exit tail records can carry the last known kernel values. Hold records establish the live budget. This was **not a generator OOM/saturation failure**.

A separate postmortem **persistent-service continuity guard failed and remains failed**. The unrelated `dmarie.service` was already mainPID0/activating/auto-restart with restart counter371021 in the earlier snapshot, then absent from one selected snapshot. Manager-only journal shows repeated pre-existing status226/NAMESPACE exit/restart cycles; later manager metadata still activating/auto-restart, counter371635. It was neither stopped/restarted/configured by benchmark commands nor excluded afterward to make the guard green. Its exact impact is unmeasured; **no full unchanged-host-services or causal-isolation claim** is made. Other snapshot entries and original127.0.0.1:4000 PID811/startticks691/executable identity matched. Raw counters/pressure/logs are retained. Empty bounded Docker-event history is an unavailable history window, not proof no OOM occurred.

## Owner-approved stopping and retained state

After raw/log/kernel/source/private-input evidence capture and the explicit blocked/unscored choice, only the exact owned PostgreSQL container was stopped with its configured signal. Actual PostgreSQL **exit0 /nonOOM**, finished **2026-10-16T02:31:02.851100815Z**; log confirms fast-shutdown checkpoint and **“database system is shut down”**. That clean PG stop does **not** repair the earlier backend SIGINT139 or certify a clean full-stack lifecycle.

The OOM backend remained stopped with its137/OOM/finished identity untouched. Both containers, **`baas-convexpg-vps16_data` /`baas-convexpg-vps16_pgdata`**, old SQLite storage, private inputs, source/SDK/compiler archives, raw sample/source/log evidence and prior lifecycle records remain retained. Private native configuration hash unchanged. No reset/reseed/reimport/deployment/cache flush/image/limit change or backend recovery. **No post-OOM native full canonical hash or acknowledged-write durability is certified**; measured data remains as left by the failed attempt, followed by the clean PG process stop.

Originals stay private/unchanged; public derivatives carry original/derivative SHA-256, byte counts and redaction provenance after actual seven private candidates across both preserved variants, JWT shapes and HTTP query strings were screened before retrieval/publication. Bulk raw samples/source archives are not force-added to ignored Git paths. The complete raw evidence and diagnostic failures are preserved, not replaced by a smoke test or filtered passing narrative.

**Owner-accepted next step: publish this blocked/unscored outcome, verify publication, then Nhost feasibility. No numerical Convex capacity is accepted.**
