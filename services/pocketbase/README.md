# PocketBase native benchmark profile — implementation in progress

## Tested software and VPS slice

| Item | Pinned version / planned allocation |
|---|---|
| BaaS software | **PocketBase v0.40.5**, upstream commit `6f370ea741f33adf889eef02e3c1b884a47aa522` |
| Native extension build | **Go 1.27.2**, native Linux AMD64, upstream default `modernc.org/sqlite v1.60.1`; locked Go modules, no standalone serving SQLite driver |
| Entire serving slice | **1 vCPU quota / 4 GiB RAM (4,294,967,296 bytes) / no swap**, total for PocketBase, embedded database, native routes and ingress—not an allocation per component |
| Separate load generator | **k6 1.3.0; 2 vCPU quota / 8 GiB RAM (8,589,934,592 bytes) / no swap**, `k6-2cpu-8g-v3` |
| Host context | Quota-limited slice on shared native AMD64 `azabab.com`: 4 CPUs, 16,770,072,576 bytes total RAM; not a dedicated 1-vCPU VPS or a measured $12/month offering |

Exact image index/native-child references: [versions.json](versions.json). Serving deployment and kernel-budget verification are pending; the untimed native Go schema tests use a separately bounded build container and do not establish serving capacity.

## Native API and logical storage mapping

The implementation uses PocketBase's supported **Go extension**, native routing, Collection/Record APIs, database query builder and `RunInTransaction`; no external application server or separately opened timed SQLite connection.

- `feed_users` and `feed_posts` are native base collections with PocketBase's supported customizable **Text primary keys**, storing original positive signed-64-bit IDs as exact decimal strings, never lossy float64 Number fields.
- Native relation fields retain logical user/post relationships. The equivalent feed-order index uses `(created_at DESC, CAST(id AS INTEGER) DESC)`; author and liked-post access paths remain indexed.
- `feed_likes` retains PocketBase's native generated record ID plus a unique `(user_id,post_id)` index representing the original logical compound primary key.
- Native relation validation and transactional Record saves enforce write integrity. Native relation validation is not misrepresented as a physical SQLite foreign-key declaration; offline import must additionally verify every reconstructed logical relationship.
- `feed_sequences` is private persistent atomic post-ID allocation metadata only. Its scalar and the new post must commit in one native transaction. It is not an application response, query-result or like-count cache.
- Application users remain ordinary base records, not native Auth accounts. The same synthetic compatibility HS256 identities/JWT scope applies; native signup/login/session throughput is outside this benchmark.
- Native direct Create/Update/Delete rules remain locked. Custom writes must verify caller signatures/claims and bind ownership before using internal Record APIs. Per-request like counts are required; no response/query-result/JWT-verification caches.

The initial native red/green schema tests prove real collection bootstrap, locked public write rules, full `9223372036854775807` identities, Unicode/U+0000 lossless Record storage, missing-owner rejection and unique likes. [Original red/green output](../../results/pocketbase/implementation-checks/) is retained. These are feasibility checks, **not the complete HTTP correctness gate or a performance score**.

## Current status

- Published baseline `f2224373c27265037d6201208055206f6f872c63` checked out under the new owned workspace `/opt/twelve-dollar-baas-pocketbase-16g/src`.
- Namespace `baas-pocketbase-vps16`; loopback benchmark ingress 14000 verified free. Original listener 4000 and existing services are untouched; prior completed owned targets remain stopped with evidence/volumes retained.
- Current release/API/source and native build/runtime image manifests resolved; first actual Go schema red/green cycle passed on the designated VPS.
- HTTP application, full canonical import/reset, deployment, actual serving limits, full correctness/fault/restart gate, calibration, scored search, confirmations and final report remain in progress/pending.

All final published reports must repeat the exact software/component versions and aggregate VPS slice prominently, with separate runner allocation. No performance result is claimed before complete native correctness, frozen-input/resource checks and independent confirmations.
