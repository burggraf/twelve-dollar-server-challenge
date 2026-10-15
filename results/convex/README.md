# Tested software and VPS slice

**Status: incomplete feasibility/correctness checkpoint. No Convex capacity score.**

- **Convex:** official self-hosted `precompiled-2026-10-06-a3538c6`, upstream `a3538c6d212948f20726868e41d155d2534cd130`, SDK/CLI **1.46.0**, bundled Node **22.22.2**. Native `/version` reports `unknown`. AMD64 image: `sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`.
- **Approved persistence variant:** PostgreSQL **17.11 (Debian17.11-1.pgdg12+2)**; AMD64 image `sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`.
- **Entire serving stack:** one shared **1-vCPU quota / 4 GiB (4,294,967,296 bytes) / zero swap** parent. Backend, including its native Node executor, has a **3-GiB (3,221,225,472-byte)** child limit; PostgreSQL **1 GiB (1,073,741,824 bytes)**. The child CPU ceilings do not increase the combined one-core allowance.
- **Separate planned runner:** k6 **1.3.0 / 2 vCPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, profile `k6-2cpu-8g-v3`. **No Convex k6 load test has run.** Untimed tools/controller each use separate 2-CPU / 4-GiB / zero-swap limits.
- Native execution on **azabab.com**, actual **claudius.azabab.com**. These are quota-limited **shared-host slices**, not dedicated VPSes or measured $12/month offerings. Price and region are unknown.

## Results so far

| Stage | Observed result | Evidence |
|---|---|---|
| Original SQLite persistence | Failed feasibility: full native row verification timed out; later read-only paging was followed by a serving-backend OOM kill. Not a k6/runner failure. | [SQLite diagnosis](implementation-checks/SQLITE_FEASIBILITY_BLOCKER.md) |
| Fresh official PostgreSQL setup | 16 empty-setup checks passed, after preserved setup failures. | [Setup](implementation-checks/POSTGRES_EMPTY_SETUP.md) |
| Full canonical native import/read verification | 50,000 users, 500,000 posts and 2,016,005 likes independently re-read through native APIs; exact canonical logical hash reproduced. Initial full-data gate: 14 checks. | [Canonical data proof](implementation-checks/POSTGRES_CANONICAL_READ_FEASIBILITY.md) |
| Native HTTP reads | Feed/detail/error integration and full data regression passed 20 checks after observed missing-route failures. | [HTTP reads](implementation-checks/HTTP_READ_INTEGRATION.md) |
| Positive storage health and backend uptime | 23 checks passed; actual backend-process uptime, not guessed module/worker age. | [Health and clock](implementation-checks/POSITIVE_STORAGE_HEALTH_AND_BACKEND_CLOCK.md) |
| Actual PostgreSQL outage/recovery | Warmed health path, stopped only owned PostgreSQL, observed sanitized HTTP503, recovered the same container and reverified the full canonical hash. 1 outage check + 23 recovery checks passed. | [24-check recovery result](implementation-checks/ACTUAL_POSTGRES_OUTAGE_AND_RECOVERY.md) |
| Fresh read-only publication verification | 27 checks passed, including another full stored-data hash, unchanged runtime/source/private/service identities. Auth reds separately reconfirmed. | [Publication verification](implementation-checks/PARTIAL_CHECKPOINT_PUBLICATION.md) |
| Authentication | Initial missing/malformed-bearer tests produced six meaningful failures across two tests. These are expected reds before implementation, **not passing auth tests**. | [Auth red](implementation-checks/native-http-auth-gate-first-red-public.log) |

The passing stage counts overlap: **do not add them as distinct coverage totals**. The canonical logical SHA-256 is `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`.

### Performance results

| Metric | Convex result |
|---|---|
| Confirmed VUs | **Not measured** |
| Requests/second | **Not measured** |
| Scored p95 / p99 | **Not measured** |
| Capacity comparison/ranking | **Not available** |

Correctness/import durations and individual health observations are not scored request-latency measurements. The fresh publication-verification parent memory peak was **3,329,617,920 bytes**, with post-run current **3,317,202,944 bytes**, under the unchanged 4-GiB configured parent. Substantial raw memory-pressure counters and earlier PostgreSQL child peak overshoot are retained. No serving OOM or host swap-out increase was observed in the accepted PostgreSQL stages. This does not guarantee full write/load fit.

## Why Convex is not finished

Still required: strict authentication/JSON validation; native transactional post allocation and exactly-once likes; concurrency/rollback; actual stored wide signed64/Unicode/NUL round trips; reset and acknowledged compatibility-write restart persistence; full frozen SDK/generated/runtime reproduction and inherited/current correctness; then runner headroom, load search, independent confirmations and final audit.

Native HTTP actions/private functions access storage through supported Convex APIs; no timed application-side PostgreSQL driver or precomputed like counters. Ordinary database/index/module caches stay enabled; query-result caching is disabled and reexecution checked. Synthetic HS256 compatibility is not native signup/login/session throughput. Logical relation checks are not physical SQL FK enforcement; a clean restart is not provider power-loss proof.

Original SQLite failure, PostgreSQL stages, source snapshots and raw-safe evidence remain separate and immutable. Selected source snapshots are not a completed reproducibility bundle. See [implementation/status](../../services/convex/README.md), [master plan](../../MASTER_PLAN.md), and the stage-specific checksum/provenance files. Later BaaS work waits until Convex is completed or an explicitly accepted stopping outcome is agreed.
