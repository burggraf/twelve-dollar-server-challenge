# PocketBase native benchmark profile — implementation in progress

## Tested software and VPS slice

| Item | Pinned version / planned allocation |
|---|---|
| BaaS software | **PocketBase v0.40.5**, upstream commit `6f370ea741f33adf889eef02e3c1b884a47aa522` |
| Native extension build | **Go 1.27.2**, native Linux AMD64, **SQLite 3.53.4** via upstream default `modernc.org/sqlite v1.60.1`;  locked Go modules, no standalone serving SQLite driver |
| Entire serving slice | **1 vCPU quota / 4 GiB RAM (4,294,967,296 bytes) / no swap**, total for PocketBase, embedded database, native routes and ingress—not an allocation per component |
| Separate load generator | **k6 1.3.0; 2 vCPU quota / 8 GiB RAM (8,589,934,592 bytes) / no swap**, `k6-2cpu-8g-v3` |
| Host context | Quota-limited slice on shared native AMD64 `azabab.com`: 4 CPUs, 16,770,072,576 bytes total RAM; not a dedicated 1-vCPU VPS or a measured $12/month offering |

Exact image index/native-child references: [versions.json](versions.json). The native application is now running in the actual verified whole-serving 1-vCPU/4-GiB/no-swap parent slice. Untimed native Go build/tests use a separately bounded build container; neither these correctness checks nor initial runtime readiness establish serving capacity.

## Native API and logical storage mapping

The implementation uses PocketBase's supported **Go extension**, native routing, Collection/Record APIs, database query builder and `RunInTransaction`; no external application server or separately opened timed SQLite connection.

- `feed_users` and `feed_posts` are native base collections with PocketBase's supported customizable **Text primary keys**, storing original positive signed-64-bit IDs as exact decimal strings, never lossy float64 Number fields.
- Native relation fields retain logical user/post relationships. The equivalent feed-order index uses `(created_at DESC, CAST(id AS INTEGER) DESC)`; author and liked-post access paths remain indexed.
- `feed_likes` retains PocketBase's additional native record ID (deterministic 15-character hexadecimal IDs for offline imported likes; native generated IDs for new likes) plus a unique `(user_id,post_id)` index representing the original logical compound primary key.
- Native relation validation and transactional Record saves enforce write integrity. Native relation validation is not misrepresented as a physical SQLite foreign-key declaration; offline import must additionally verify every reconstructed logical relationship.
- `feed_sequences` is private persistent atomic post-ID allocation metadata only. Its scalar and the new post must commit in one native transaction. It is not an application response, query-result or like-count cache.
- Application users remain ordinary base records, not native Auth accounts. The same synthetic compatibility HS256 identities/JWT scope applies; native signup/login/session throughput is outside this benchmark. The actual native bootstrap has **0 regular Auth users and 1 platform installer superuser**; these private platform records are preserved by app-only import, not replaced by synthetic benchmark accounts.
- Native direct Create/Update/Delete rules remain locked. Custom writes must verify caller signatures/claims and bind ownership before using internal Record APIs. Per-request like counts are required; no response/query-result/JWT-verification caches.

The initial native red/green schema tests prove real collection bootstrap, locked public write rules, full `9223372036854775807` identities, Unicode/U+0000 lossless Record storage, missing-owner rejection and unique likes. [Original red/green output](../../results/pocketbase/implementation-checks/) is retained. These are feasibility checks, **not the complete HTTP correctness gate or a performance score**.

## Current status

- Published baseline `f2224373c27265037d6201208055206f6f872c63` checked out under the new owned workspace `/opt/twelve-dollar-baas-pocketbase-16g/src`.
- Namespace `baas-pocketbase-vps16`; loopback benchmark ingress 14000 verified free. Original listener 4000 and existing services are untouched; prior completed owned targets remain stopped with evidence/volumes retained.
- Current release/API/source and native build/runtime image manifests resolved; first actual Go schema red/green cycle passed on the designated VPS.
- Native HTTP application, actual serving-slice membership and full canonical import are verified. The original hash `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d` matches 50,000 users / 500,000 posts / 2,016,005 likes; native platform-row fingerprints before/after import match exactly.
- Ten native Go tests (including measured SQLite engine/source ID and native read/write connection pragmas), three real native-schema import tests, inherited42/shared6/native5/seed-privacy1 pass. Actual owned process stop/recovery/restart preserves an acknowledged NUL/Unicode post, exactly-once like and post-ID sequence. Startup testing caught that native `Bootstrap()` applies system migrations only; an explicit supported post-bootstrap application-migration hook fixed it, with the failed and passing logs retained.
- Native default DB connections use WAL / synchronous NORMAL, busy timeout 10,000 ms, foreign_keys ON, temp_store MEMORY and cache_size -32,000 KiB (pinned upstream `core/db_connect.go`). Relation fields provide native validation, not physical FK declarations. Ordinary database buffers/plans and platform metadata/module caches remain enabled; application result/like-count/JWT-verification caches do not.
- Formal owned build/up/seed/offline reset/readiness/stop automation and repeat canonical reset are verified. The [full combined frozen-input gate](../../results/pocketbase/vps16-linux-amd64/setup-evidence/full-correctness.log) passed on the current native image: Go10, inherited42/shared6/native5/import3/privacy1/workload4, common scoring/host/isolation and all PocketBase deployment/budget/ownership/frozen-evidence/artifact-policy regressions, plus actual transport stop/recovery/process restart persistence. Complete raw log, current fingerprints/log SHA and actual-value privacy scan were independently verified. The first shared runner-environment failure remains retained; assertions and resource/SLO policy were not weakened.
- **Three additional independent 10,000-VU holds passed**: 949,739 requests / 900 scored seconds, zero request/schema errors. [Final lower-bound report](../../results/pocketbase/vps16-linux-amd64/CONFIRMED_LOWER_BOUND.md), [structured result](../../results/pocketbase/vps16-linux-amd64/confirmed-lower-bound.json), [endpoint metrics](../../results/pocketbase/vps16-linux-amd64/endpoint-confirmations.md). Eleven full slots plus smoke retained, including pause/resume history, valid 11,250/12,500 target failures and invalid 15,000-RAM/20,000-OOM runner cases. Unresolved 250-VU steps: **not an exact maximum**. Original raw/source/data/image/cgroup/resource/privacy and service continuity audits passed for all 12 bundles; bulk archives retained locally/VPS under existing policy. Owned target stopped, all volumes/private inputs/evidence retained. Publication awaits commit/push verification; owner authorized Convex only after that. Normal restart is not provider power-loss durability.

All final published reports must repeat the exact software/component versions and aggregate VPS slice prominently, with separate runner allocation. No performance result is claimed before complete native correctness, frozen-input/resource checks and independent confirmations.
