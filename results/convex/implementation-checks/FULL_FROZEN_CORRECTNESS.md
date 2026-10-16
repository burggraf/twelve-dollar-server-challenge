# Tested software and VPS slice

Convex **precompiled-2026-10-06-a3538c6**, upstream **`a3538c6d212948f20726868e41d155d2534cd130`**, SDK/CLI **1.46.0**, native AMD64 image **`sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`**, bundled Node **22.22.2**, tools Node **22.20.0**. Backend `/version` literally `unknown`. PostgreSQL **17.11-bookworm /Debian17.11-1.pgdg12+2**, native AMD64 image **`sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`**.

Entire serving **1 vCPU /4 GiB (4,294,967,296 bytes) /zero swap**, backend/bundled executor **3 GiB (3,221,225,472 bytes)** plus PostgreSQL **1 GiB (1,073,741,824 bytes)** under one aggregate parent. Separate planned runner **k6 1.3.0 /2 vCPUs /8 GiB (8,589,934,592 bytes) /zero swap**, `k6-2cpu-8g-v3`. Untimed tools/controller each separately capped2CPU/4GiB/zero swap. Native execution only on `claudius.azabab.com`; shared-host slices, not dedicated/measured $12/month machines. Price/region unknown.

**Observed result: full frozen functional/harness gate PASSED. Clean SIGINT shutdown remains FAILED139 under the explicit separate owner capacity exception. No k6 workload or capacity score is certified by this stage.**

## Required full suites, not a smoke-test replacement

The corrected wrapper explicitly supplied `RUNNER_MEMORY=8g`, matching the selected common versioned runner; the [first failed attempt and exact environment cause](COMPLETE_RUNTIME_AND_BENCHMARK_PREPARATION.md) remain preserved. No required test or assertion was changed, and the entire gate reran with distinct outputs. No source/runtime/native limits, target image, process, workload or budgets changed between attempts.

Actual fresh outcome:

- **Original unchanged `test/test.sh`: passed42/failed0** against original goldens, actual authentication/writes/counts/errors/order/time/content types.
- **Allsix shared FeedContract methods passed**, including concurrent creates/duplicate likes, signed identity, strict payload/expiry, native storage health, Unicode and ECMAScript trim.
- Native reset traversed2,017 pages, deleted exactly **37 posts/five likes**, restored allocation500000. The separate native maintenance3 tests also passed private positive/anonymous rejection/unknown-edge refusal controls.
- Native transactional writes7/fixture guards3/stored edges5/auth6/error literal1/actual backend clock2/HTTP reads6/private query-cache2/canonical3/import4/seed-safety1 all passed. Stored9007199254740993/UnicodeNUL, signed64max/exhaustion, real post-patch collision rollback,32-way create/like concurrency and24-orphan feed remained actual native tests, not in-memory mocks.
- Workload/hold/response-validation **Node4** passed.
- Host-side Convex harness3/frozen evidence5/full runtime freeze3/load config1/budget5/native Compose4/reset controller6/common scorer24/isolation3/unchanged PocketBase harness3/Supabase harness3/artifact policy3 all passed.

The primary complete log records **112 Python checks +original42 +Node4 =158 executed checks**. This is an execution count within this stage, not158 independent feature requirements, and must not be added to overlapping earlier stage counts. An extra same-suite isolation3 precheck in the driver is separate, not silently counted again.

Independent actual native API pages restored **50,000 users /500,000 posts /2,016,005 likes**, native metadata/logical relation/order/uniqueness checks,583 largest seeded likes and logical SHA-256 **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`**. Canonical suite **155.571s**, not request-latency percentiles. All fixture cleanup was exact-owned; no platform/native environment/Auth/settings/credential reset, SQL driver or blanket reseed.

## Frozen inputs, epoch and continuity checks

[Complete current source/runtime preparation](COMPLETE_RUNTIME_AND_BENCHMARK_PREPARATION.md) archived all1,555 current source/harness files,2,412 dependency/compiler entries and five generated files privately, with immutable backend/PG/tools image references. Archive checksums and every complete source entry were verified **before and after** this gate, alongside installed runtime digest **`1f7bb3f120584759bf1343bed93f8cc20d8e69bf17773b1418b9f729a8be00e3`**. Current app/verification/runtime/schema/catalog/images/host/token inputs matched exactly. The corrected external gate source was separately archived/hashed; it did not replace the original first wrapper.

Actual backend **PID2313635/start2026-10-16T00:02:20.333088398Z**, PostgreSQL **PID2313499/start2026-10-16T00:02:14.076467149Z** stayed unchanged with identical container/image/storage/private runtime configuration. Both remained healthy. Prior original139/acknowledged-recovery evidence hashes stayed unchanged; seven current application modules still matched that actual recovery checkpoint. Original port4000 listener/process identities and persistent service identities were preserved; no host swap-out increase or serving OOM event. This stage never stopped/restarted/redeployed a server.

Parent lifetime peak **3,479,109,632 bytes** unchanged; current **3,387,654,144→3,434,369,024 bytes**. `memory.events.max` **605,427→621,435**, OOM/OOM-kill/group-kill all0. Raw child/parent counters retain pressure, reclaim/refault and earlier PostgreSQL child overshoot; configured allowance is not current usage/lifetime peak, and child peaks are not simultaneous totals.

Full attestation completed **2026-10-16T01:35:49.202380+00:00**; measured gate body **255.95433378219604s**, outer job263s. Raw correctness log SHA-256 **`19a550f6de3529966732336a059730499e2c728b957de637de381264bb6ce9b9`**. Original logs/driver, before/after/final profiles/services, canonical manifest, corrected/first external controllers and complete attestation are retained with original/derivative bytes/hashes/redaction provenance; actual seven private candidates/JWT shapes/all HTTP query strings screened before retrieval/publication.

## Scope boundary

This certifies the frozen **functional/harness** stage on the current native pair, not a fresh provider deployment, native signup/login/session throughput, measured serving capacity, clean shutdown or provider power-loss durability. Logical relations/transaction uniqueness are not physical SQL FK/UNIQUE declarations. Native transaction/read/time limits remain original; ordinary DB/index/module/page caches remain enabled, response/query-result/count/JWT caches prohibited.

The original clean-backend-shutdown139 remains a real unresolved native defect with separate successful acknowledged crash-recovery evidence. The owner explicitly permitted measuring the serving path despite that failed gate. Actual runner native version/kernel allocation/reserve, calibration validity, full timed holds/independent confirmations and original source/raw/resource/privacy audit remain separate required stages before any capacity claim.
