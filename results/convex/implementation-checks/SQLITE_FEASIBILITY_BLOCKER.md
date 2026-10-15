# Tested software and VPS slice

**Convex self-hosted:** official release `precompiled-2026-10-06-a3538c6`, upstream **`a3538c6d212948f20726868e41d155d2534cd130`**, SDK/CLI **1.46.0**, native Linux AMD64 image `ghcr.io/get-convex/convex-backend:a3538c6d212948f20726868e41d155d2534cd130@sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`. Actual bundled Node **22.22.2**; native `/version` returns literal **`unknown`**. Default local SQLite persistence was used; its runtime SQLite engine version/pragmas have **not** been independently established.

**Entire serving stack:** official backend and bundled executors in one **1-vCPU quota / 4-GiB (4,294,967,296-byte) / zero-swap** parent slice and container on designated **azabab.com**, actual hostname `claudius.azabab.com`. Native query-result cache disabled with `UDF_CACHE_MAX_SIZE=0`; ordinary native database/index/module caches enabled. `RUNTIME_WORKER_THREADS=1`; transaction/read/execution limits were not raised. Dashboard/frontend excluded because they are not needed for the headless API.

**Separate future load runner:** **k6 1.3.0 / 2 vCPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, `k6-2cpu-8g-v3`. **No Convex k6 measurement ran.** Untimed import/query tools instead used an isolated 2-vCPU/4-GiB/zero-swap container; that is not the load-runner profile. These are quota-limited slices on a shared host, not dedicated VPSes or measured $12/month offerings. Price and region are unknown.

## Outcome: this SQLite prototype did not pass native feasibility

This is a retained implementation-stage failure, **not a capacity score, an accepted full-correctness result, or proof that every supported Convex storage configuration fails**. Compatibility HTTP actions, JWT authentication and write mutations have not been completed. The full independent stored-row canonical hash has not passed, and no successful native dataset manifest exists.

### 1. Imports completed; subsequent stored-row verification failed

The original [import/test log](native-canonical-import-and-queries.log) records successful supported CLI imports of **50,000 users / 500,000 posts / 2,016,005 likes / 1 allocation-sequence document**. The source JSONLines preparation reproduced canonical logical SHA-256 `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`; input preparation/import messages are not independent proof of every actual stored row.

The full dataset suite ran **3 tests in 64.935 seconds: 1 error, 2 passing**:

- Independent paginated stored-row/hash/relations/metadata verification errored with **`TimeoutError: timed out`** at the unchanged **30-second HTTP client deadline**.
- Native normalized feed/detail assertions passed, including request-time native indexed counting of **583** likes on seeded post **405018**. This is functional evidence, not an SLO pass.
- Unauthenticated invocation of the internal native read functions was denied.

The [backend-log derivative](native-backend-first-import-public-v2.log) records the failed request as HTTP **499**, **37,869.175 ms**, and `SystemTimeout` with final pause `database_syscall(1.0/queryPage)` of **37.867910445 s**. It also records a subsequent successful query taking **10,258.786 ms**; these are diagnostic request durations, not benchmark percentiles.

At the original job's after-profile, target PID/start/image/restart count and selected source/private credential hashes were unchanged; the target was still running and not OOM-killed. The [parent profile](native-import-after.json) recorded memory peak **4,294,967,296 bytes**, `max=12838`, but **`oom=0`, `oom_kill=0`**. Therefore the first job's timeout must not be mislabeled an OOM kill.

### 2. Bounded read-only follow-up; later actual serving OOM kill

The follow-up made at most three unchanged 1,000-row page requests per table, with no import, mutation, deployment, restart or limit change. See [page trace](native-page-diagnosis-public.log) and [driver](native-page-diagnosis-driver-public.log).

| Table | Pages observed | Outcome |
| --- | --- | --- |
| users | 3 | Each returned 1,000 rows; 0.948207 / 0.478682 / 3.192471 s |
| posts | 3 | Each returned 1,000 rows; 6.260489 / 6.543558 / 6.009347 s |
| likes | first page only | Client `TimeoutError` after 30.030058 s |

The diagnostic script catches query errors to record the remaining observations; its unit's exit **0** means the trace completed, **not that native queries passed**. A client deadline or script exit is not proof that native backend work has stopped.

Later evidence establishes an actual serving-process memory-cgroup OOM kill:

- Docker target exit **137**, **`OOMKilled=true`**, stopped at **2026-10-15T18:30:39.96804828Z**, restart count **0**.
- Parent `memory.events`: **`max=36300`, `oom=1`, `oom_kill=1`**. Configured limit remained **4,294,967,296 bytes** and zero swap. Raw recorded peak is **4,294,971,392 bytes** (one 4-KiB accounting increment above the configured ceiling), not evidence of a larger allocation.
- Kernel logs identify **`CONSTRAINT_MEMCG`**, owned **`/tdsbaasconvexvps16.slice`**, and killed original target PID **2112234**, `convex-local-ba`, with **4,169,124 KiB anonymous RSS**. See [exit/kernel/continuity evidence](native-post-diagnosis-state.json) and [raw parent/host retention profile](native-page-diagnosis-retention.json).
- Host swap-outs remained **0**. This is a **target-side feasibility failure**, not a k6/load-generator OOM; no k6 process was involved.

No query was retried after this observation. The stopped container, native SQLite volume, private credentials and original evidence are retained. No automatic restart, reimport, reseed, storage edit or resource enlargement was performed.

## Pinned implementation explains the scaling problem

In the pinned upstream [`crates/sqlite/src/lib.rs`](https://github.com/get-convex/convex-backend/blob/a3538c6d212948f20726868e41d155d2534cd130/crates/sqlite/src/lib.rs):

1. `PersistenceReader::index_scan` accepts **`_size_hint: usize`** but does not use it (lines 576–596).
2. `_index_scan_inner` executes an ordered SQL index-range query without a page-size `LIMIT` (lines 128–187).
3. It iterates the matching rows, parses each document, and collects them into a **`Vec` before returning** (lines 188–224). Only then does `index_scan` wrap that vector as a stream.

Consequently an application's 1,000-row `paginate` request is not a 1,000-row bound on this persistence adapter's intermediate work. The first unbounded-range page can materialize a much larger native index range. That concrete behavior explains why reducing the requested page count alone is not a sound fix; it is consistent with the observed multi-second pages, native query timeout, memory pressure and subsequent OOM. The exact allocation responsible for the kill was not profiled, and the evidence does not isolate every contributor to process memory.

Source URLs, full commit and original SHA-256 values are recorded in [diagnosis-source-manifest.json](diagnosis-source-manifest.json). No third-party backend patch, raised native timeout/read limit, count cache, application replica or direct underlying-storage application driver was introduced.

## Continuity, privacy and next decision

The final read-only snapshot confirms the original **port4000 listener, PID/start identity and executable unchanged**. Of the pre-Convex running service identities, only `fwupd.service` was absent at the later snapshot; normal root `user@0.service` sessions are excluded from persistent identity comparisons. No attribution is made for `fwupd` appearing/disappearing, and no unrelated service was stopped or restarted by this work.

Published backend logs are **explicit derivatives**, not originals: actual native admin/instance-secret values and conservative components were checked/redacted; every HTTP access-log query string was removed because native import URLs can carry upload tokens. Some conservative component matches are the public instance-name prefix, not leaked secret values. Original private VPS bytes are retained unchanged. [Retention provenance](native-page-diagnosis-retention.json) identifies original/derivative sizes, hashes and replacement counts. The earlier private credential-only copy named `native-backend-first-import-sanitized.log` is **not approved for publication** and is superseded by the explicit v2 derivative. Selected original kernel entries are published; the complete original kernel snapshot remains private.

The same pinned release [officially supports local PostgreSQL persistence](https://github.com/get-convex/convex-backend/blob/a3538c6d212948f20726868e41d155d2534cd130/self-hosted/advanced/postgres_or_mysql.md), explicitly tested upstream with PostgreSQL 17. A separate PostgreSQL-backed feasibility attempt is recommended **only with both servers inside the unchanged aggregate serving budget**, preserving this SQLite failure and starting with fresh owned storage. No external managed database, pooling of storage variants, successful fit claim, or progression to Nhost is authorized by this report. Owner selection is pending; no PostgreSQL deployment has been created.
