# Tested software and VPS slice

**Convex self-hosted:** `precompiled-2026-10-06-a3538c6`, upstream **`a3538c6d212948f20726868e41d155d2534cd130`**, SDK/CLI **1.46.0**, native AMD64 backend manifest **`sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`**. Bundled Node **22.22.2**; native `/version` remains **`unknown`**.

**Native persistence:** official **PostgreSQL 17.11 (Debian17.11-1.pgdg12+2)**, native AMD64 **`sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`**, using the official Convex PostgreSQL adapter, not application-side SQL. This owner-approved fresh variant is separate from the retained [failed SQLite attempt](SQLITE_FEASIBILITY_BLOCKER.md).

**Entire serving allocation:** one shared **1-vCPU quota / 4 GiB (4,294,967,296 bytes) / zero-swap** parent, `tdsbaasconvexpgvps16.slice`, containing the official backend and its bundled executors plus PostgreSQL and all its workers/buffers. Backend child **3 GiB (3,221,225,472 bytes)**; PostgreSQL child **1 GiB (1,073,741,824 bytes)**. Both have one-core child ceilings, but the **combined parent ceiling remains one core**. Native database/index/module caches remain enabled; query-result caches are disabled. Dashboard/frontend are unnecessary and excluded.

**Separate future load runner:** **k6 1.3.0 / 2 vCPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, `k6-2cpu-8g-v3`. **No Convex load test has run.** Untimed native tools and their bounded controller each have a disclosed **2-vCPU/4-GiB/zero-swap** ceiling, not the k6 allocation. All execution occurred on **azabab.com**, actual hostname `claudius.azabab.com`: quota-limited **shared-host slices**, not dedicated VPSes or measured $12/month offerings. Price and region are unknown.

## Result: full canonical native import/read verification passed

The supported per-table CLI imports completed once into the fresh PostgreSQL-backed application. More importantly, a separate verifier read **every application row through the real native paginated query API**, independently reconstructed the logical hash, and checked exact native metadata fields, fixed-width positive signed64 ID representation, order/uniqueness, relationships and unique likes.

| Application table | Actual native rows |
| --- | ---: |
| users | 50,000 |
| posts | 500,000 |
| likes | 2,016,005 |

**Actual stored logical SHA256:** `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`.

See the [independent stored-data manifest](native-postgres-canonical-dataset-public.json), [complete import/test log](native-postgres-full-canonical-public.log) and [unit driver](native-postgres-full-canonical-driver-public.log). The extra imported `feed_sequences` row is ID-allocation metadata only; it is not a precomputed like counter and is not silently added to the three-table canonical hash.

The run then passed normalized native feed/detail assertions, including post **405018** with **583 likes**, private native function checks and five identical full-data probe queries reexecuting with no result-cache hits/shared-result waits and zero retained query-cache bytes. Counts are calculated at request time from native indexed likes, not cached aggregates.

Fresh passing suites were **canonical native data/query/private3**, **nonempty native private/cache2**, **aggregate budget5**, **actual Compose config4**: **14 tests**. The canonical suite took **161.867 seconds as a whole**; this is not a single-query latency or a benchmark percentile. The empty-table probe assertion was correctly not run or claimed passing on populated tables.

The remote bounded unit completed in **18min14.570s**. The controller's reported **31.4-MiB peak** is only the controller, **not the serving stack**. Native CLI import continued-server-side semantics remain disclosed: client interruption is not import cancellation. No native transaction/read/write/execution limit or client deadline was increased.

## Resource and continuity evidence

[Before](native-postgres-canonical-before-public.json) and [after](native-postgres-canonical-after-public.json) snapshots verify the exact native image/process/cgroup ownership and parent/child kernel budgets. The original 17 selected executable/config/test source hashes, private input hashes, platform credential hashes, container IDs, PIDs/start identities and restart counts remained unchanged. Both targets were healthy and running with no observed serving OOM. Host swap-outs stayed **0→0** and host OOM-kill counter **3→3**; that earlier count includes the separately retained SQLite failure, not a PostgreSQL kill. Existing persistent service identities and original port4000 listener/PID/start/executable were unchanged.

The observed parent peak was **2,613,133,312 bytes**, after-state current **2,396,848,128 bytes**, under the unchanged **4,294,967,296-byte** parent. **This does not mean there was no resource pressure.** The hierarchical `memory.events.max` counter reached **454,247**, with `oom=0`, `oom_kill=0`.

A subsequent [read-only child-pressure observation](native-postgres-post-canonical-pressure-public.json), taken at **2026-10-15T19:49:07.447839+00:00**, attributes the then-current **455,516 max events** to the PostgreSQL child's local counter; the parent local max counter and backend child max counter were **0**. PostgreSQL recorded substantial reclaim/refault activity and nonzero cumulative memory/I/O pressure. Its raw peak **1,074,327,552 bytes** is **585,728 bytes above** its configured **1,073,741,824-byte** limit; both the configured kernel limit and zero-swap limit remained unchanged, with no OOM. These are preserved raw kernel observations, not grounds to claim that a larger budget was assigned or that pressure was absent. Child lifetime peaks must not be summed as simultaneous memory use; post-run counters are not a continuous benchmark hold monitor.

No unrelated workloads were removed to improve fit. Actual pre-import host availability/reserve was checked; this untimed read result does not certify later k6 headroom or a capacity SLO.

## Persistence/source context and limits of proof

Fresh post-run maintenance-connection settings remained **`fsync=on`**, **`synchronous_commit=on`**, **`full_page_writes=on`**, **`data_checksums=off`**. The initial settings inherited into the before/after profiles are not falsely represented as independently resampled writer-session settings; the separate post-run observation records its own maintenance query. No provider power-loss durability test has run.

The [pinned PostgreSQL source manifest](postgres-persistence-source-manifest-public.json) records exact URLs/hashes at the deployed upstream commit. The adapter uses the requested index size hint, clamped to **1…5000**, to choose a batch size and bounded channel (`crates/postgres/src/lib.rs:1108–1122`), passes the batch limit to the SQL index query, and yields rows as a stream. This differs from the tested SQLite adapter's ignored hint/eager whole-range vector; it does not establish that every native allocation is bounded under every possible key/collision pattern. The actual canonical native read result, not source inspection alone, establishes this checkpoint.

The same pinned PostgreSQL crate declares ordinary `CREATE TABLE` storage with document JSON bytes in `BYTEA`, and its write path awaits native transaction commit (`lib.rs:1890`, `connection.rs:447–450`). No `synchronous_commit` override or `UNLOGGED` statement was found in the four retained PostgreSQL crate sources. This is bounded source evidence, not proof of every runtime writer-session option or acknowledged-write restart/power-loss behavior.

## Remaining acceptance work

This checkpoint proves **canonical native import/read feasibility for this exact configuration**, not a completed application or a performance score. Native round trips for wide signed64 IDs/Unicode/NUL, strict compatibility HTTP/auth/write behavior, transactional allocation/unique likes/concurrency, deletion/orphan paging, reset/platform preservation and actual restart recovery still require their own tests. Converter-only wide-ID/NUL tests are not substituted for native round trips. Logical relation checks are not claimed as physical SQL FK/UNIQUE declarations.

Compatibility scope remains synthetic users/preissued HS256 JWTs, not native signup/login/session throughput. No result pooling with the failed SQLite attempt, changed workload, hidden query/JWT cache, underlying-storage application driver, raised limit, Nhost progression or resolved maximum is authorized by this result. A full frozen reproduction checkout and complete current correctness gate remain prerequisites for any k6 measurement.

## Originals and privacy

[Retention provenance](native-postgres-full-canonical-retention.json) records exact original/derivative SHA256 and sizes. Actual private credential values were screened before retrieval. The backend public derivative removes **66 HTTP access-log query strings**, including native upload capabilities; private originals remain unchanged. Other retained full-run artifacts required no replacements. Pressure/source metadata has its own [retention provenance](native-postgres-pressure-retention.json). No private env/rendered config, native database or raw fixture files are published.
