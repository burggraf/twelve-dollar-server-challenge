# Tested software and VPS slice

**Partial checkpoint publication, not completed Convex compatibility or capacity.**

Convex self-hosted **`precompiled-2026-10-06-a3538c6`**, upstream **`a3538c6d212948f20726868e41d155d2534cd130`**, SDK/CLI **1.46.0**, bundled Node **22.22.2**, native `/version` literal **`unknown`**; AMD64 backend **`sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`**. Official PostgreSQL **17.11 (Debian17.11-1.pgdg12+2)**, AMD64 **`sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`**.

Entire serving stack: shared aggregate **1-vCPU quota / 4 GiB (4,294,967,296 bytes) / zero swap**, backend including native Node executor **3 GiB (3,221,225,472 bytes)**, PostgreSQL **1 GiB (1,073,741,824 bytes)**. Child one-core ceilings still share a single combined one-core parent. Separate planned runner **k6 1.3.0 / 2 vCPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, `k6-2cpu-8g-v3`, **not run**. Untimed tools/controller each separate2CPU/4GiB/zeroSwap. Native execution only on **azabab.com**, actual **claudius.azabab.com**: shared-host quota slices, not dedicated VPSes or measured$12/month offerings; price/region unknown.

## Fresh read-only publication verification

At **2026-10-15T21:36:02.972992+00:00**, a separate bounded verification completed without deploying code, importing/reseeding data, restarting any serving process, changing credentials or raising limits.

**27 checks passed:** common positive health1; private backend-clock2; native HTTPreads6; native private/cache2; complete native canonical data3; converter4; aggregate budget5; actual Compose config4. [Full safe log](publication-checkpoint-public.log), [driver](publication-checkpoint-driver-public.log), [before](publication-checkpoint-before-public.json), [after](publication-checkpoint-after-public.json), [canonical manifest](publication-checkpoint-native-dataset-public.json), [retention provenance](publication-checkpoint-retention.json).

The full native paginated API independently re-read **50,000 users / 500,000 posts / 2,016,005 likes**, reproducing logical SHA **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`** and checking metadata/order/relations/unique likes/native projections/private visibility. Largest seeded like count583 remains correct. Converter wide-ID/NUL checks remain preparation evidence, not actual stored wide-ID/NUL round trips.

**Authentication still fails:** two actual-site tests produced **six expected assertion failures**, actual404/non-JSON missing POST routes versus required401s. [Complete fresh red](publication-auth-expected-red-public.log). The wrapper verifies this expected-red state; exit0 of the publication unit **does not turn auth failures into passes**. No authentication, transactional writes, full inherited correctness or capacity completion is claimed.

Canonical suite156.232seconds; unit2min39.443s. These are correctness durations, not request latency percentiles. Controller31.4MiB peak is not serving memory. All24 selected source hashes matched current local/VPS bytes; private inputs/platform credentials/main image/container/PID/start/restart identities and original services/port4000 listener were preserved. Both required servers healthy afterward.

Parent configured allowance **4,294,967,296bytes**, lifetime observed peak **3,329,617,920bytes**, post-run current **3,317,202,944bytes**. Hierarchical`memory.events.max`**493443→504029**; OOM/kill/group-kill0 and no host swap-out increase. Raw pressure and prior PostgreSQL child overshoot remain retained; no exact allocation cause, pressure-free fit or future full-write/load fit is asserted. Ordinary native DB/index/module caches enabled; query-result cache disabled and execution verified. No custom response/like-count/JWT-verification cache or timed application-side storage driver.

## Publication safety and limits

An [initial exact proposed-index audit](publication-privacy-audit-public.json) screened189files/2,629,034bytes against **six actual private values across both preserved SQLite and PostgreSQL attempts**, with no matches, forbidden private files or unredacted HTTP log queries. New safe derivatives carry original/private versus derivative SHA/size provenance. Final index auditing and Git/remote identity verification occur before publication; this report does not preclaim a commit hash, public download or CI run.

Code/config/docs-only staged whitespace checks passed. Full staged diff checking reports existing whitespace in original raw-safe logs; those bytes are retained unchanged, not trimmed to manufacture green output. All earlier94 checksum entries were independently replayed. Selected source snapshots remain **not a full SDK/generated/runtime reproduction bundle**.

This publishes an honest work-in-progress checkpoint at owner request. Native strict authentication/JSON, transactional create/like/allocation/concurrency/rollback, actual stored wide-ID/Unicode/NUL, reset and acknowledged compatibility-write restart, full frozen reproduction/current inherited correctness and all load-search/confirmations remain pending. No numerical Convex VU/RPS/p95/p99 result or progression to Nhost is justified by these27 checks. Logical relation checks are not physical SQL FK/UNIQUE enforcement; synthetic HS256 compatibility is not native signup/login throughput; clean process recovery/global settings are not provider power-loss durability.
