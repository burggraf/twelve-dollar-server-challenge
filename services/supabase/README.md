# Supabase native API-serving profile

This is a **self-hosted API-serving subset**, not a claim that the full default Supabase stack runs on one CPU. It implements the unchanged feed HTTP contract through supported native APIs:

`k6 → Envoy → native Edge Runtime user worker → Envoy /rest/v1 → PostgREST RPC/JWT → PostgreSQL`

No external application server or timed PostgreSQL driver is used. PostgreSQL functions execute inside the serving database. There are no response/query-result caches, precomputed like counters, or JWT-verification caches. Normal database buffers, query plans and JavaScript module compilation caches remain enabled.

**Measured outcome:** [2,000-VU confirmed capacity](../../results/supabase/vps16-linux-amd64/CONFIRMED_CAPACITY.md), 210.86–211.69 requests/s across three independent five-minute holds. One 2,250-VU probe passed, but all three confirmations failed; no exact mathematical maximum is claimed. All 11 scored attempts, both calibrations, original raw samples/source overlays and correctness/resource/continuity evidence are retained under the repository's artifact-storage policy. The completed owned stack is stopped; volumes/evidence remain available for reproduction.

## Frozen components and aggregate budget

Official self-hosting reference: [`7767e1ab6ef0914ba77d5835a4255fff8de90966`](https://github.com/supabase/supabase/tree/7767e1ab6ef0914ba77d5835a4255fff8de90966/docker). Exact index and selected native AMD64 digests are in [`versions.json`](versions.json).

| Required component | Pinned version |
|---|---|
| Supabase PostgreSQL | `17.6.1.136` image, PostgreSQL `17.6` |
| Auth / GoTrue | `v2.196.0` |
| PostgREST | `v14.17` |
| Edge Runtime | `v1.76.2` |
| Envoy | `v1.39.1` |

**All five serving containers share one kernel-enforced `tdsbaassupabasevps16.slice`:** `cpu.max = 100000 100000`, `memory.max = 4294967296`, `memory.swap.max = 0`. This is **1 CPU / 4 GiB total**, not five individually budgeted containers. Container membership, actual process cgroups, selected manifests, parent children and kernel limits are verified. Raw parent CPU/throttling/memory/events/pressure/I/O and individual container statistics are retained.

The separate k6 container retains the common **2 CPU / 8 GiB**, zero-swap `k6-2cpu-8g-v3` profile and pinned k6 1.3.0. Its only mounts are the workload, pre-issued token fixture and output directory; it cannot read server signing keys or private runtime state. Trusted verification tools are untimed, separately bounded, and reuse the previously verified native Node 22.20.0 tools image. No fresh tools-image compilation claim is made.

Excluded because this feed-serving path does not require them: Studio, Storage, Realtime, analytics/logging, Vector, Supavisor and imgproxy. PostgREST retains its native connection pool. Auth **is running and included in the budget**, but native signup is disabled and native signup/login/session throughput is outside this cohort. Official full-stack minimum/recommended sizing must not be confused with this explicitly reduced profile.

## Authentication and permissions

The comparison retains the owner-approved compatibility-auth scope:

- 50,000 deterministic **application** users in `feed_data.users`, not 50,000 native Auth accounts.
- 20,000 pre-issued compatibility HS256 JWT identities; a private compatibility key distinct from the native JWT key.
- Every application write verifies the compatibility signature, algorithm, expiry, subject and username inside its Edge Function.
- Each write mints a short-lived native JWT with fixed `feed_writer` role and the verified application subject. Arbitrary caller roles and username metadata are not forwarded as native authorization claims.
- PostgREST verifies the native JWT on each RPC (`jwt-cache-max-lifetime=0`). Native gateway API-key checks are retained; internal RPC traffic also traverses Envoy.
- App tables and helper functions live in a private schema. Reader roles can execute read RPCs; only the scoped writer role can execute write RPCs. Direct native table writes are denied. No client-supplied user-ID parameter selects the write owner.

Native Auth accounts, provider signup, password hashing, login/refresh, native sessions and UUID/application identity mapping are **not** benchmarked. Their performance cannot be inferred from these results.

## Canonical data and native storage mapping

The original generator, SQLite schema/specification, golden fixtures and legacy submissions remain unchanged. Offline maintenance imports only the three application tables while API services are stopped; PostgreSQL stays up for its supported maintenance interface. Supabase Auth/platform metadata is not replaced or truncated.

Expected logical data: **50,000 users, 500,000 posts, 2,016,005 likes**; SHA-256 **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`**. Every reset re-exports ordered native rows, reconstructs original logical values and checks the entire original hash. Auth account counts before/after import are retained (zero in the initial profile).

PostgreSQL `TEXT`/`JSONB` cannot contain U+0000. Bodies therefore use UTF-8 `bytea`, base64 transport over native RPC, and strict lossless decoding in Edge Functions. This is a disclosed native type/transport mapping, **not modified application data**. A database codepoint check, original PKs/FKs/three indexes, request-time `COUNT(*)`, transactional unique likes and atomic identity allocation are retained. JSON property order is reconstructed to match the inherited exact-byte contract. Invalid UTF-8, unpaired surrogates and non-finite JSON scalars are rejected rather than silently replaced.

PostgreSQL uses `fsync=on`, `synchronous_commit=on`, `full_page_writes=on`, logged application tables and ordinary WAL. Normal actual process-restart persistence is tested; **power-loss/provider-storage durability is not established**.

## Owned native lifecycle

All campaign execution is on the designated `root@azabab.com` native AMD64 host, under `/opt/twelve-dollar-baas-supabase-16g/src`, project `baas-supabase-vps16`. The parent workspace must have `.benchmark-owned`. Use the existing project-private pinned CLI; no global Docker/plugins/packages/firewall changes are required. The occupied original port **4000 remains untouched**; only **127.0.0.1:14000** is published.

```bash
bash services/supabase/run.sh build       # public pinned image pulls / private runtime initialization
bash services/supabase/run.sh up          # owned bootstrap/schema and native readiness
bash services/supabase/run.sh seed        # deterministic TSVs and private compatibility token fixture
bash services/supabase/run.sh reset       # app-only offline import and full hash verification
bash services/supabase/run.sh test        # fresh reset, full correctness, faults, actual restart, attestation
bash services/supabase/run.sh bench --vus 1000 --smoke
bash services/supabase/run.sh search --max-vus 20000 --max-attempts 12
bash services/supabase/run.sh down         # only owned serving processes; retain volumes/evidence
```

Required official `webhooks.sql` bootstrap precedes password `roles.sql`; both are vendored from the pinned reference. An initial omitted-dependency failure is retained, including its original owned failed volume. Current data is in the explicitly named `baas-supabase-vps16_pgdata2`; the failed first volume is not deleted or silently reused. Privileged offline maintenance uses the image's `supabase_admin` operator role, never an elevated serving connection.

Keys, issued JWTs, rendered private gateway config, bootstrap logs and database volumes are excluded from publication. Opaque high-entropy runtime/token fingerprints attest immutable inputs without exporting credentials. Correctness is invalidated by changed source/tests/images/schema/runtime/host/token inputs or rewritten raw logs.

Full scored protocol: 30s warm ramp, 120s warm hold at up to 1,000 VUs, 60s target ramp, **300s scored hold**, 30s drain; common p95 <500ms, p99 <1,000ms, errors <1%, malformed successes zero. The original bounded search and three independent confirmations are reused. Generator OOM/saturation, sparse/failed monitoring or host paging invalidate a measurement, not target capacity. Shared-host continuity/resource review and evidence replay remain required before publication.

This replaces the original SQLite-only deployment path and does **not** establish a dedicated $12/month equivalence. Price/region have not been supplied.
