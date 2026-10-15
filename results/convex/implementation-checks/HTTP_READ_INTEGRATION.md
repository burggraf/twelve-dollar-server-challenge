# Tested software and VPS slice

**Convex self-hosted** `precompiled-2026-10-06-a3538c6`, upstream **`a3538c6d212948f20726868e41d155d2534cd130`**, SDK/CLI **1.46.0**, bundled Node **22.22.2**, native version endpoint **`unknown`**, AMD64 backend **`sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`**. Official **PostgreSQL17.11 (Debian17.11-1.pgdg12+2)**, AMD64 **`sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`**.

**Aggregate serving:** **1-vCPU quota /4GiB(4,294,967,296bytes)/zero swap**, shared parent `tdsbaasconvexpgvps16.slice`; backend **3GiB(3,221,225,472bytes)** and PostgreSQL **1GiB(1,073,741,824bytes)** children. Both child ceilings are one core but the combined parent is **one core**, not two. All required native backend/executor/database processes and buffers are included; dashboard/frontend unnecessary and excluded. Ordinary database/index/module caches enabled; query-result caches disabled.

**Separate future runner:** **k6 1.3.0 /2vCPUs/8GiB(8,589,934,592bytes)/zero swap**, `k6-2cpu-8g-v3`; **not executed**. Untimed tools and bounded controller each use their disclosed separate2CPU/4GiB/noSwap ceiling, not the load-runner profile. Native execution only on **azabab.com**, actual `claudius.azabab.com`: **shared-host quota slices**, not dedicated VPSes or measured$12/month offerings. Price/region unknown. See [canonical read checkpoint](POSTGRES_CANONICAL_READ_FEASIBILITY.md) for storage/default-limit/resource-pressure details; this separate variant is not pooled with failed SQLite.

## Observed red → native read integration green

The actual native site port3211 initially returned missing-route404s/non-JSON fallback errors. [Six tests produced14 assertion failures](native-postgres-http-read-red-public.log), not import/fixture exceptions. Only then was the first `http.js` implemented through supported **HttpRouter/httpActionGeneric → ctx.runQuery → internal native feed/detail** functions. No external application-side SQL driver, response/query/count/JWT cache, resource increase or read/execution limit increase was introduced.

The [complete fresh green log](native-http-read-green-public.log) contains **20 passing tests**:

- **HTTP reads6:** canonical native projection/key order/compact JSON; detail and leading-zero normalization; exact583-like count; invalid and missing signed64 IDs; exact unknown-path JSON; five HTTP feed requests actually reexecuting native queries with no ready/wait/cache result reuse.
- **Native nonempty private/cache2**.
- **Full native canonical rows/hash/relations/metadata/order/feed/detail/private3**, again independently reproducing50,000users/500,000posts/2,016,005likes and SHA **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`** after the code deployment.
- **Aggregate budget5**, **actual Compose config4**.

The public post serializer preserves exact positive signed64 IDs without passing IDs through `Number`; it JSON-escapes all string fields and checks count integrity. The nonexistent-wide-ID tests demonstrate parsing/error classification, **not actual native wide-ID/NUL stored round trips**. Those remain required.

The native unit ran **2min45.833s**; the canonical suite alone took **162.008s**. These are setup/correctness durations, not request percentiles. The controller's31.1MiB peak is not serving memory. The compiler's cross-filesystem temporary-directory advisory and npm update notice remain untrimmed in the raw-safe log; no install/upgrade/global configuration change was made.

## Frozen selected source and runtime continuity

[Before](native-http-read-before-public.json), [after](native-http-read-after-public.json), [stored-data manifest](native-http-read-canonical-dataset-public.json), [driver](native-http-read-green-driver-public.log) and [retention provenance](native-http-read-green-retention.json) retain actual proof. All **19 selected source hashes** matched VPS/local bytes. Native image/container/PID/start/restart identities, parent/child kernel budgets, private inputs, platform credentials, existing persistent services and original port4000 listener identities remained unchanged. No serving OOM or host swap-out increase was observed. PostgreSQL child memory-pressure caveats from the canonical checkpoint remain applicable; no claim of pressure-free operation is made.

Those exact executed source bytes were subsequently checked against actual private values and preserved under [`http-read-selected-source/`](http-read-selected-source/) with [SHA/size manifest](http-read-selected-source-manifest.json), before subsequent feature edits. The manifest preserves the original read-only `http.js` as tested here. **This selected source snapshot is not yet the full SDK/generated/runtime freeze or a completed capacity reproduction bundle.**

All original/private and explicit derivative hashes/sizes are retained; actual private values and HTTP query strings were screened before retrieval. No private env, raw fixtures/native databases, tokens, DSNs or full process environment/argv are published.

## Scope still incomplete

This checkpoint proves native HTTP **read integration**, not completed compatibility or a performance score. At this checkpoint health/authentication/write mutations were absent; later health work has separate tests/evidence and does not retroactively change this report. Actual native wide-ID/Unicode/NUL round trips, transactional allocation/unique likes/concurrency, orphan-hole pagination, reset/platform preservation and acknowledged-write restart/recovery remain pending. Synthetic preissued-HS256 compatibility is not native signup/login throughput; logical checks are not physical SQL FK enforcement; normal restart/global fsync settings are not provider power-loss proof. No Nhost progression or maximum/capacity claim follows from these20 tests.
