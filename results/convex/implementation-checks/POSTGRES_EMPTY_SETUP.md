# Tested software and VPS slice

**Convex self-hosted:** `precompiled-2026-10-06-a3538c6`, upstream **`a3538c6d212948f20726868e41d155d2534cd130`**, SDK/CLI **1.46.0**, native AMD64 backend manifest **`sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`**. Bundled Node **22.22.2**; native `/version` remains literal **`unknown`**.

**Official native persistence:** **PostgreSQL 17.11 (Debian 17.11-1.pgdg12+2)**, `postgres:17.11-bookworm@sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`, native Linux AMD64. This is the upstream-supported `POSTGRES_URL`/`postgres-v5` configuration, not an application-side SQL adapter or external managed database. The owner explicitly approved this separate variant after the retained [SQLite feasibility failure](SQLITE_FEASIBILITY_BLOCKER.md).

**Entire serving allocation:** **1 vCPU quota / 4 GiB (4,294,967,296 bytes) / zero swap**, enforced by the shared `tdsbaasconvexpgvps16.slice` parent. Backend child: **3 GiB (3,221,225,472 bytes)**; PostgreSQL child: **1 GiB (1,073,741,824 bytes)**, both zero swap. Each child has a one-core ceiling, but the **shared parent caps their combined CPU at one core**, not two. The official backend includes its bundled executors; PostgreSQL includes all its worker processes and buffers. The dashboard/frontend are excluded because they are unnecessary for the headless serving API.

**Separate future runner:** **k6 1.3.0 / 2 vCPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, `k6-2cpu-8g-v3`. **No Convex load measurement has run.** Untimed tools and the bounded setup controller use a separate **2-vCPU/4-GiB/zero-swap** allowance, not the future load-runner profile. All product execution occurred on approved **azabab.com**, actual hostname `claudius.azabab.com`. These are quota-limited slices on a shared host, not dedicated VPSes or measured $12/month offerings; price and region are unknown.

## Verified empty setup, not full native feasibility

The fresh owned workspace is `/opt/twelve-dollar-baas-convexpg-16g/src`, project **`baas-convexpg-vps16`**, with fresh **`baas-convexpg-vps16_data`** and **`baas-convexpg-vps16_pgdata`** volumes. The failed SQLite container/volume/private inputs remain stopped and retained in their separate original workspace. Results from the two storage configurations will not be pooled.

The fresh host preflight recorded native AMD64, **4 host CPUs**, **15,484,362,752 available memory bytes**, no host swap, free owned namespace/loopback endpoints, and **363,894,431,744 free disk bytes**. No unrelated workload was removed or stopped to make room.

The [actual runtime profile](native-postgres-empty-setup-verification-public.json) verifies:

- Both native image identities/architectures, actual Docker limits, process cgroup membership, exact parent/child kernel CPU/RAM/swap limits, and exactly the two required serving cgroup children.
- Both servers healthy, same container IDs, PIDs/start identities and restart count **0** throughout the empty setup verification. PostgreSQL runs as native UID **999**; both containers have read-only roots, dropped capabilities and no-new-privileges. PostgreSQL exposes no host port; backend endpoints bind only to loopback.
- PostgreSQL `server_version_num=170011`, **`fsync=on`**, **`synchronous_commit=on`**, **`full_page_writes=on`**; native default **`data_checksums=off`** is retained and disclosed. These settings are not provider power-loss durability proof.
- `UDF_CACHE_MAX_SIZE=0`, `RUNTIME_WORKER_THREADS=1`, unchanged native read/write/execution limits. Repeated identical native queries executed again with no result-cache hits/shared-result waits and zero retained query-cache bytes. Ordinary native database/index/module caches remain enabled.
- All **17 selected executable/config/test source hashes** matched the local source; private input hashes, existing persistent service identities and original port4000 listener/PID/start/executable remained unchanged. No serving OOM or host swap-out increase was observed during these empty checks.

The recorded empty-state parent peak was **140,464,128 bytes**. **This is not a full-dataset footprint, proof of fit, or a performance measurement.**

## Fresh verification evidence

The complete [retained test log](native-postgres-empty-verification2-public.log) contains **16 passing tests**, without treating earlier failures as passes:

| Checks | Tests | Scope |
| --- | ---: | --- |
| Actual Compose normalization | 4 | Exact image pins, separate tools profile, fresh volumes, precise byte allocations, parent, privilege and host-port settings |
| Native API/private visibility/cache | 3 | Actual empty storage reads, unauthenticated internal-function denial, repeated-query re-execution |
| JSONLines converter | 4 | File preparation: signed64 wide IDs, Unicode/NUL, canonical hashes/relations/uniqueness and refusal to replace existing output |
| Aggregate budget validator | 5 | Reject missing required servers, unaccounted children, parent/child resource drift, wrong native images/ownership/membership and failed health |

The converter tests do **not** establish actual native wide-ID/Unicode/NUL round trips. The budget unit fixtures do **not** replace the separately captured actual kernel/runtime profile. Config/profile tests run on the designated VPS with deployment metadata available; actual native API/converter checks run in bounded untimed tools.

### Retained setup failures and minimal corrections

1. The first configuration test compared native Compose's canonical memory-byte **string** with an integer. It stopped before credentials, images or containers were created. The test now compares exact string representations of the same byte quantities; the limits/assertions were not enlarged or relaxed. Original executed test source, [failure log](native-postgres-bootstrap-first-public.log), driver and retention provenance are preserved.
2. Both servers then started and actual runtime/version/durability settings plus three native tests passed, but converter tests failed because the partial upload omitted shared **`scripts/import_sqlite.py`**. Only its canonical constants are imported; its database-writing `main` is not invoked by this converter. The unchanged shared source was supplied; no native SQLite storage access or fallback was introduced. See [original second setup outcome](native-postgres-bootstrap-attempt2-public.log).
3. Converter tests then passed, but budget tests were incorrectly called inside the narrowly mounted tools container, where deployment `versions.json` was unavailable. The **unchanged five tests** were moved to the bounded VPS controller, alongside host-side Compose checks, where their metadata exists. No test assertion was removed. [Failure evidence](native-postgres-empty-verification-first-public.log) and a separate fresh passing run are retained.

No correction required a server restart, function redeployment, native reimport, volume deletion, credential rotation, resource increase, relaxed read/timeout limit or unrelated service change after the successful initial server start.

## Remaining work

Full canonical inputs have been reused byte-for-byte from the original verified preparation: only **three TSVs and four JSONLines files**, not prior credentials/env/native databases. New PostgreSQL-native full-data tests were then run against empty tables and failed meaningfully on **0 versus 50,000 users** and an empty feed, while unauthenticated access remained denied. Input preparation and expected reds are not stored-data proof.

The next step is supported per-table native CLI import followed by independent actual stored-row/hash/relationships/metadata/order checks, native normalized feed/detail/count queries and full-data cache/private-function checks, with before/after source/private-input/process/resource continuity. **No full stored canonical hash, completed compatibility application, accepted full correctness/fit gate, benchmark score or Nhost progression is claimed by this checkpoint.** The workspace is still an initial partial source upload, not the final frozen reproduction checkout.

## Privacy and originals

[Retention provenance](native-postgres-empty-verification2-retention.json) records original/private and public-derivative hashes and sizes. Actual PostgreSQL password/DSN and native admin/instance secrets were checked before retrieval; HTTP access-log query strings are removed from derivatives if present. The passing log and selected profiles required no replacements and have the same hashes as their retained originals. Earlier failures/private originals remain unchanged. No keys, fixture/native database files or rendered private configuration are published.
