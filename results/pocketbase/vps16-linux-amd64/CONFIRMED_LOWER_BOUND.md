# PocketBase — confirmed 10,000-VU lower bound

## Tested software and VPS slice

- **PocketBase v0.40.5**, upstream **`6f370ea741f33adf889eef02e3c1b884a47aa522`**; **Go 1.27.2**, **SQLite 3.53.4 / modernc.org/sqlite v1.60.1**, native Linux AMD64.
- Immutable serving image **`sha256:489cba19771795f5378e440c7f6d83d81f8460bf31e673aff8a392b080a9b131`**; executable SHA256 **`0e31cb09904df2e7cfb8a8e8d2fe18a577a1a2e4e55b92e7b937f1ee157123f8`**. Builder **`golang:1.27.2-bookworm@sha256:55395706e9703db746cc507abfc4eb2aea75918f8a8024e4848e2cb81004f5ad`**; runtime **`debian:bookworm-slim@sha256:a4672c0cb26fbdde88e38fa2dfb6c681942306680e41e4378b28770b6e79ee91`**. Complete module lock, source fingerprints, upstream/builder/runtime index and selected-child references: [versions](../../../services/pocketbase/versions.json), [native build](setup-evidence/full-native-build-manifest.json), [final attestation](setup-evidence/final-deployment-attestation.json).
- **Entire serving stack: 1 vCPU quota / 4 GiB RAM (4,294,967,296 bytes) / no swap** under `tdsbaaspocketbasevps16.slice`: native routes, REST/Auth/admin/realtime implementation and embedded main/auxiliary databases. No unbudgeted serving proxy or database.
- **Separate runner: k6 1.3.0 / 2 vCPU quota / 8 GiB RAM (8,589,934,592 bytes) / no swap**, `k6-2cpu-8g-v3`, selected native image `sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656`.
- Serving runs on an existing **quota-limited shared-host slice**, **not a dedicated one-vCPU VPS or measured $12/month offering**. Physical host: native AMD64 Ubuntu 24.04.5, Docker 29.8.1; 4 CPUs / 16,770,072,576 bytes RAM / no swap; this is **not** the serving allocation. At least 1 CPU / 1 GiB reserve is required beyond serving and runner. Price/region unknown; no cost/request claim.

## Result and limits of the claim

**Three additional independent full 10,000-VU holds passed** after the passing discovery probe, each following a fresh canonical application-only reset. The confirmations served **949,739 requests over 900 scored seconds**, with **0 request errors (0.000000%)** and zero malformed-success/schema errors. No latency quantiles are pooled. This measures the frozen **warm public-feed application**, not general BaaS capacity or 10,000 real authenticated users.

**This is a confirmed lower bound, not a maximum or a 250-VU-resolved capacity.** Valid 11,250- and 12,500-VU probes failed target SLOs; 20,000 was invalid due to runner OOM, and 15,000 was invalid because runner RAM hit 90.14% (unchanged cutoff: 90%). Those invalid runs cannot establish target failures. The search reserved independent confirmation slots and used 11 of 12 full attempt slots (including original paused probe and invalid runs); one unused slot cannot complete intervening bisection and three new confirmations. The observed 10,000-pass / 11,250-fail probe range remains unresolved and is not a mathematical stochastic upper bound. No hidden promotion of a single probe or invalid measurement.

## Independent confirmations

| Hold | Requests | RPS | p50 ms | p95 ms | p99 ms | Maximum ms | Errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| [20261015T164056211098Z-standard-10000vu-k6-2cpu-8g-v3](20261015T164056211098Z-standard-10000vu-k6-2cpu-8g-v3/report.md) | 316,575 | 1,055.25 | 18.581 | 74.4469 | 293.3995 | 4,668.7871 | 0 |
| [20261015T165058113497Z-standard-10000vu-k6-2cpu-8g-v3](20261015T165058113497Z-standard-10000vu-k6-2cpu-8g-v3/report.md) | 316,546 | 1,055.1533 | 16.2719 | 67.5886 | 239.8627 | 3,162.3347 | 0 |
| [20261015T170059086766Z-standard-10000vu-k6-2cpu-8g-v3](20261015T170059086766Z-standard-10000vu-k6-2cpu-8g-v3/report.md) | 316,618 | 1,055.3933 | 16.585 | 66.4716 | 278.3945 | 2,791.669 | 0 |

[Per-endpoint metrics](endpoint-confirmations.md) retain each hold's counts/errors/maxima. [Structured result](confirmed-lower-bound.json) carries exact software, allocation, source, resource and individual-hold fields.

## Frozen workload and correctness

Same protocol as TrailBase/Supabase: 30-second initial ramp, 120-second warm hold (up to 1,000 VUs), 60-second target ramp, 300-second scored hold, 30-second drain; 10-second request timeout. Per journey: feed/detail reads, 15% like, 2% create, original think times; approximately 92% of requests are reads with a very small hot public-feed working set. Gates: p95 < 500 ms, p99 < 1,000 ms, request errors < 1%, malformed successful responses = 0. Runner validity requires complete monitoring; any hold RAM >= 90%, three consecutive hold CPU samples >= 180% of one core, runner OOM, monitor failure or increased host swap-outs invalidates measurement. Isolated CPU spikes above 180% were retained, not silently filtered or mistaken for the consecutive-sample rule.

[Full correctness log](setup-evidence/full-correctness.log) passed on the exact frozen executable/test/image/runtime/schema/token/host/tool inputs, revalidated before resume and after all holds. 10 native Go tests; 42 inherited exact-byte checks; 6 shared, 5 native, 3 import, 1 seed-privacy and 4 workload tests; 24 original scoring/host and 3 isolation tests; shared Supabase harness and PocketBase snapshot/config/budget/controller/frozen-evidence/artifact-policy regressions. Real native closed DB connections prove sanitized 503 health / 500 write responses and transaction rollback in Go tests. Actual owned embedded-server stop proves transport unavailability; real process restart preserves acknowledged post/body/owner, exactly-once like and ID allocation. **Neither is a provider power-loss durability test.** The first integrated gate failed on a missing shared runner-memory environment setting, then the unchanged isolation suite and entire fresh gate passed; original failure retained. No SLO/resource/security assertion weakened.

## Supported native architecture and storage mapping

`k6 → PocketBase native Go routes → supported DB query builder / native Record APIs / RunInTransaction → embedded SQLite`. This is a pinned native extension of the product, **not an external standalone SQLite replacement**. All timed operations stay in supported product APIs. Offline app-only maintenance/import and read-only catalog/resource audits are untimed.

- Canonical 50,000 users / 500,000 posts / 2,016,005 likes, logical hash `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`. Original specification, fixture algorithm and legacy submissions preserved.
- Native base collections use exact decimal signed-64-bit Text user/post IDs, explicit numeric sort/index, native required relation fields, and extra native like-record IDs plus unique logical (user_id, post_id). Imported like IDs are deterministic 15-character hex; new ones native-generated. A transactional persistent post sequence is allocation metadata, **not a like-count/query cache**. Unicode/U+0000 roundtrips remain lossless.
- Native relation validation and explicit offline logical-integrity checks **are not physical SQLite foreign-key declarations**. Native platform/Auth/migration/settings rows and auxiliary DB remain intact; before/after platform fingerprints match. Direct native app CRUD writes are locked; allocation metadata is not publicly readable.
- Synthetic application users and preissued compatibility HS256 JWTs are verified on each write with signed-subject binding. Native Auth remains budgeted, but has 0 regular users and 1 private installer superuser: **native signup/login/session throughput is not measured**.
- Request-time normalized like counts; no response/query-result/precomputed-like-count/JWT-verification caches. Ordinary DB buffers/plans/native platform metadata caches remain enabled. Actual native concurrent/nonconcurrent builders verified SQLite 3.53.4 / source ID, WAL, synchronous=NORMAL, foreign_keys=ON, busy_timeout=10,000 ms, temp_store=MEMORY, cache_size=-32,000 KiB. WAL/NORMAL is not durability-equivalent to Supabase's synchronous PostgreSQL commits.

## Resource, host and lifecycle evidence

Original kernel budgets/native selected image/process membership, exact one-child serving scope, runner limits, no target OOM/restart, source/runtime/schema/image/token fingerprints, dataset/import preservation and scenario-clock scoring were independently replayed. Every confirmation has complete original raw samples and resource records; hold spans/peaks and raw Linux CPU/memory/I/O/pressure counters are retained in [resource replay](setup-evidence/retained-attempt-review.json) and [host review](setup-evidence/host-parent-review.json). No host swap-out increase. Host CPU pressure/quota throttling are observations, not proof of unrelated-service interference or dedicated-machine equivalence. Parent memory is charged memory including accounted cache, **not all shared host page cache**; no global cache flush or host tuning was performed.

The confirmations had 59/60/60 hold monitor samples spanning 290.82/296.86/295.87 seconds. Runner peak RAM was 54.83%/55.11%/54.79% of 8 GiB; isolated CPU peaks were 192.41%/205.69%/201.78% of one core, without the invalidating three consecutive saturated samples. Aggregate serving mean CPU was 0.8940/0.8627/0.8681 cores; peak charged RAM was 1,748,107,264 / 1,898,233,856 / 2,048,163,840 bytes. Host mean steal was 0.0135–0.0153%, I/O wait 0.2969–0.3042%, minimum available RAM 10,006,577,152 bytes; memory/I/O pressure averages peaked at zero. These describe these holds, not guaranteed future headroom.

The owner paused after the first 2,500-VU probe; the complete original history was preserved byte-for-byte. On explicit continuation, source/raw/resource/current-input checks passed and the separate resumed search repeated the initial probe within the original total 12-attempt budget. All outcomes remain retained. Original 26 persistent service identities and original port-4000 listener PID/start/executable were unchanged after correctness, pause/resume, confirmations and owned shutdown. An additional `fwupd.service` appeared at the pause snapshot; no causal attribution is made. Normal root SSH-session manager differences are separate from persistent services. Only owned PocketBase/runner components were stopped; all owned volumes, failed setup evidence and private inputs retained. No unrelated stop/restart/deletion or global Docker/package/firewall/power changes.

## All retained attempts

| Run | VUs | Outcome | Hold RPS | p95 ms | p99 ms | Reason |
|---|---:|---|---:|---:|---:|---|
| [20261015T141534167176Z-standard-1000vu-k6-2cpu-8g-v3-smoke](20261015T141534167176Z-standard-1000vu-k6-2cpu-8g-v3-smoke/report.md) | 1,000 | unscored smoke | 109.9 | 3.0813 | 43.8543 | hold gates passed |
| [20261015T142603330350Z-standard-2500vu-k6-2cpu-8g-v3](20261015T142603330350Z-standard-2500vu-k6-2cpu-8g-v3/report.md) | 2,500 | pass | 264.3467 | 13.1192 | 45.2826 | hold gates passed |
| [20261015T152505251855Z-standard-2500vu-k6-2cpu-8g-v3](20261015T152505251855Z-standard-2500vu-k6-2cpu-8g-v3/report.md) | 2,500 | pass | 264.59 | 12.8518 | 44.9393 | hold gates passed |
| [20261015T153502288012Z-standard-5000vu-k6-2cpu-8g-v3](20261015T153502288012Z-standard-5000vu-k6-2cpu-8g-v3/report.md) | 5,000 | pass | 528.6567 | 21.648 | 49.6988 | hold gates passed |
| [20261015T154500193682Z-standard-10000vu-k6-2cpu-8g-v3](20261015T154500193682Z-standard-10000vu-k6-2cpu-8g-v3/report.md) | 10,000 | pass | 1,055.8633 | 72.9871 | 300.1658 | hold gates passed |
| [20261015T155504060165Z-standard-20000vu-k6-2cpu-8g-v3](20261015T155504060165Z-standard-20000vu-k6-2cpu-8g-v3/report.md) | 20,000 | invalid | — invalid | — invalid | — invalid | load generator OOM (not target capacity) |
| [20261015T160505445050Z-standard-15000vu-k6-2cpu-8g-v3](20261015T160505445050Z-standard-15000vu-k6-2cpu-8g-v3/report.md) | 15,000 | invalid | — invalid | — invalid | — invalid | load generator used >=90% of its memory budget |
| [20261015T161651511282Z-standard-12500vu-k6-2cpu-8g-v3](20261015T161651511282Z-standard-12500vu-k6-2cpu-8g-v3/report.md) | 12,500 | fail | 1,245.3733 | 6,891.7894 | 10,000.8172 | hold latency/error/schema gate failed |
| [20261015T162851328457Z-standard-11250vu-k6-2cpu-8g-v3](20261015T162851328457Z-standard-11250vu-k6-2cpu-8g-v3/report.md) | 11,250 | fail | 1,159.8067 | 876.6719 | 9,276.4711 | hold latency/error/schema gate failed |
| [20261015T164056211098Z-standard-10000vu-k6-2cpu-8g-v3](20261015T164056211098Z-standard-10000vu-k6-2cpu-8g-v3/report.md) | 10,000 | pass | 1,055.25 | 74.4469 | 293.3995 | hold gates passed |
| [20261015T165058113497Z-standard-10000vu-k6-2cpu-8g-v3](20261015T165058113497Z-standard-10000vu-k6-2cpu-8g-v3/report.md) | 10,000 | pass | 1,055.1533 | 67.5886 | 239.8627 | hold gates passed |
| [20261015T170059086766Z-standard-10000vu-k6-2cpu-8g-v3](20261015T170059086766Z-standard-10000vu-k6-2cpu-8g-v3/report.md) | 10,000 | pass | 1,055.3933 | 66.4716 | 278.3945 | hold gates passed |

Invalid-run diagnostic metrics—including 15k request timeouts—remain in the original per-run summaries/raw streams; the invalid entries above deliberately have no scored throughput/latency claim. No immutable per-run report/log/checksum was rewritten to make this table.

## Reproduction, privacy and availability

See [native profile](../../../services/pocketbase/README.md), [benchmark contract](../../../contracts/BENCHMARK.md), per-run `manifest.json`, `correctness.log`, `correctness-manifest.json`, `dataset.json`, `working-tree.patch` and original `SHA256SUMS`. The remote sparse base is `f222437`; archives/source overlays freeze actual working-tree files, not a falsely clean Git checkout. Local publication executable/test hashes match measured VPS bytes. Native build references and full Go module lock are retained; resumed runs reused the same verified image, not a newly claimed build.

Full original raw `samples.json.gz` and `source.tar.gz` are retained locally/on the VPS, **excluded from new Git commits** under [existing artifact policy](../../README.md). A Git checkout alone cannot verify absent bulky files against original checksums. No external public raw download locator, release publication or external CI execution is claimed. Small originals/reports/provenance/audit helpers are included; actual keys, issued tokens, private rendered config/installer URLs, database files/volumes and broad environments/process arguments are excluded. Actual runtime-key / issued-signature / native-password+tokenKey scans passed. Verify `REPORT_SHA256SUMS` for mutable final summaries; original per-run checksum files remain unchanged.

## Interpretation

This supported native implementation passes the common hot public-feed contract at 10,000 simulated VUs under the disclosed serving budget. It does not establish the highest sustainable VU count, protected/personalized reads, cold/broad datasets, write-heavy/native Auth/realtime/storage capacity, power-loss durability, a universal product ranking or measured $12 price equivalence. Future methodology experiments remain separate from this frozen cohort.
