# Supabase — 2,000-VU confirmed capacity

**Outcome: scored, 2,000 virtual users**, the highest candidate confirmed by three independent passing five-minute holds under the fixed **250-VU search resolution**. This is **not an exact mathematical maximum**: 2,250 VUs passed one probe but failed all three subsequent confirmations; no finer search was performed. 2,500 VUs also failed. No failed hold is discarded, no generator-invalid run forms the bracket, and no single-run pass substitutes for confirmation.

## Three independent confirmations

| Hold | Requests | Requests/s | p50 ms | p95 ms | p99 ms | Maximum ms | Request errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| [1](20261015T062456087846Z-standard-2000vu-k6-2cpu-8g-v3/report.md) | 63,258 | 210.86 | 4.70 | 125.39 | 415.28 | 1,910.44 | 2 (0.00316%) |
| [2](20261015T063552558051Z-standard-2000vu-k6-2cpu-8g-v3/report.md) | 63,401 | 211.34 | 4.85 | 163.53 | 473.41 | 1,396.74 | 2 (0.00315%) |
| [3](20261015T064648677622Z-standard-2000vu-k6-2cpu-8g-v3/report.md) | 63,506 | 211.69 | 4.76 | 128.93 | 411.23 | 1,407.40 | 3 (0.00472%) |

Across **900 scored seconds**, **190,165 requests**, **7 request errors** (0.00368% combined count ratio), and **zero malformed successful responses**. Each hold independently met p95<500ms, p99<1,000ms, request errors<1%, malformed successes=0. Maximum latencies exceed one second and remain disclosed; maximum is not the percentile SLO. **Quantiles are not averaged or pooled.** [Per-endpoint results](endpoint-confirmations.md) include all 12 endpoint/hold rows. The original raw status audit identifies the seven errors as **five HTTP 500s and two HTTP 503s**; they are not hidden as successful work. The underlying individual error causes are not established by status-only metric evidence.

## Complete search and backoff

| Attempt | VUs | Phase | Outcome | Requests/s | p95 / p99 ms | Errors |
|---|---:|---|---|---:|---:|---:|
| [1](20261015T045724392273Z-standard-2500vu-k6-2cpu-8g-v3/report.md) | 2,500 | Search probe | **fail** | 231.32 | 3,560.66 / 5,462.97 | 4560 (6.57089%) |
| [2](20261015T050821481749Z-standard-1250vu-k6-2cpu-8g-v3/report.md) | 1,250 | Search probe | **pass** | 132.26 | 6.07 / 31.69 | 0 (0.00000%) |
| [3](20261015T051917744240Z-standard-1750vu-k6-2cpu-8g-v3/report.md) | 1,750 | Search probe | **pass** | 185.19 | 30.20 / 217.06 | 24 (0.04320%) |
| [4](20261015T053014119004Z-standard-2000vu-k6-2cpu-8g-v3/report.md) | 2,000 | Search probe | **pass** | 211.43 | 70.09 / 323.74 | 6 (0.00946%) |
| [5](20261015T054110358168Z-standard-2250vu-k6-2cpu-8g-v3/report.md) | 2,250 | Search probe | **pass** | 236.15 | 473.41 / 863.79 | 15 (0.02117%) |
| [6](20261015T055206724973Z-standard-2250vu-k6-2cpu-8g-v3/report.md) | 2,250 | 2,250 confirmation | **fail** | 235.16 | 684.06 / 1,205.16 | 23 (0.03260%) |
| [7](20261015T060303490334Z-standard-2250vu-k6-2cpu-8g-v3/report.md) | 2,250 | 2,250 confirmation | **fail** | 234.84 | 721.70 / 1,469.62 | 54 (0.07665%) |
| [8](20261015T061400018671Z-standard-2250vu-k6-2cpu-8g-v3/report.md) | 2,250 | 2,250 confirmation | **fail** | 235.01 | 744.56 / 1,503.44 | 14 (0.01986%) |
| [9](20261015T062456087846Z-standard-2000vu-k6-2cpu-8g-v3/report.md) | 2,000 | 2,000 confirmation | **pass** | 210.86 | 125.39 / 415.28 | 2 (0.00316%) |
| [10](20261015T063552558051Z-standard-2000vu-k6-2cpu-8g-v3/report.md) | 2,000 | 2,000 confirmation | **pass** | 211.34 | 163.53 / 473.41 | 2 (0.00315%) |
| [11](20261015T064648677622Z-standard-2000vu-k6-2cpu-8g-v3/report.md) | 2,000 | 2,000 confirmation | **pass** | 211.69 | 128.93 / 411.23 | 3 (0.00472%) |

All 11 scored attempts are retained and resource-valid. The attempt budget was 12 and the upper VU budget 20,000; neither was expanded. The three failed 2,250-VU confirmations forced the prescribed 250-VU backoff. Their p95/p99 failures prevent a 2,250-VU score despite the passing probe. Both initial and final-source 1,000-VU **unscored 20-second calibrations** remain separate; the earlier calibration predates the final verification-input synchronization and supplies no scored confirmation.

## Native profile, resource envelope and measurement validity

- Host: **azabab.com**, Ubuntu 24.04.5 LTS, native AMD64, 4 CPUs, 16,770,072,576 bytes RAM, no swap, Docker 29.8.1. Existing shared VPS; price/region/provider thermals and storage guarantees unknown. No original dedicated-$12 equivalence or cost/request claim.
- Entire serving stack: official pinned **PostgreSQL 17.6 / Auth 2.196.0 / PostgREST 14.17 / Edge Runtime 1.76.2 / Envoy 1.39.1**, **one actual 1-CPU/4-GiB/zero-swap** parent `tdsbaassupabasevps16.slice`. Exact index/native-child digests are in [versions.json](../../../services/supabase/versions.json); actual selected images and process memberships are in every manifest.
- Separate k6 **2 CPU/8 GiB/zero swap**, `k6-2cpu-8g-v3`, k6 1.3.0; selected native child `sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656`. No signing keys/private runtime mounts. Untimed verification reuses the verified native Node 22.20.0 tools image; no fresh tools-image compilation is claimed.
- All five serving processes, exact parent children/CPU/memory/swap limits and runner kernel limits/native child are verified. There are no five separate 1-CPU/4-GiB allowances. Parent memory includes page cache; child Docker memory percentages are not substituted for the aggregate budget.
- Required OS reserve of 1 CPU/1 GiB fits beyond serving+runner. Every attempt has 60 hold samples spanning approximately 297.7 seconds; no monitor failure/sparse coverage, runner OOM, sustained>=180%-of-one-core runner CPU, >=90% runner RAM, or rising host swap-outs invalidated this cohort.

| Hold | Monitor samples / span s | Runner peak CPU % of one core | Runner peak RAM % of 8 GiB | Serving peak GiB incl. cache | Mean serving CPU cores |
|---|---:|---:|---:|---:|---:|
| 1 | 60 / 297.66 | 98.28 | 11.38 | 2.408 | 0.929 |
| 2 | 60 / 297.69 | 42.90 | 11.34 | 2.410 | 0.939 |
| 3 | 60 / 297.67 | 95.45 | 11.44 | 2.403 | 0.930 |

[Native scoring/resource/source/checksum replay](setup-evidence/capacity-resource-replay-review.json), [raw counter review](setup-evidence/host-parent-review.json), and [original raw quantile/status audit](setup-evidence/raw-sample-audit.json) support the result. Host swap-outs remained 0→0. Confirmation mean host steal was 0.0051–0.0077%, mean I/O wait 0.0599–0.0616%, and minimum available host RAM ≥13,363,150,848 bytes. Host CPU pressure `some avg10` peaked at 29.74–32.47; memory/I/O pressure peaks were 0. The serving quota was busy (~0.929–0.939 CPU) and throttled 59.66–63.15% of periods. These raw observations describe a quota-limited shared-host experiment, **not proof of no possible external interference**; provider/storage/thermal attribution remains limited.

All 26 preexisting persistent services and original loopback-4000 listener/start identities matched [before/after campaign](setup-evidence/capacity-continuity.json). Ordinary root SSH-session `user@0.service` changes are separately identified, not a blanket application exception. Only benchmark ingress 127.0.0.1:14000 was published. No global packages/plugins/firewall/power changes, unrelated stop/restart or pruning was performed. After final live-input review the five completed **owned** serving containers were stopped; [ownership/stop/continuity proof](setup-evidence/completed-owned-stop-proof.json) confirms that data volumes and all evidence remain retained.

## Timed path, auth and data semantics

`k6 → Envoy → native Edge Runtime user worker → Envoy /rest/v1 API-key layer → PostgREST RPC/JWT → PostgreSQL`

No external application server or timed SQL driver. There are no response/query-result caches, precomputed like counters or JWT-verification caches. Ordinary database buffers/plans and JS module compilation caches remain enabled. PostgREST verifies each native JWT (`jwt-cache-max-lifetime=0`); Edge verifies compatibility HS256 signature/algorithm/expiry/strict subject on every write and binds only the verified app identity into a scoped 60-second native writer JWT. Native gateway API-key checks remain active. No application retries were added. Native worker/isolate recycling is not attested as absent by container/process-restart proofs.

The scope is **synthetic application identities and pre-issued compatibility JWTs**, not native Auth signup/login/password/session/refresh throughput. Native Auth is running within the same budget, signup disabled; native accounts remain 0 versus 50,000 logical application users. Do not infer native login performance.

The exact canonical logical data is 50,000 users / 500,000 posts / 2,016,005 likes; SHA-256 **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`**. Every attempt resets app-only tables offline and reconstructs the original full logical hash from native ordered rows, retaining Auth/platform metadata. UTF-8 `bytea` bodies/base64 RPC preserve U+0000 and Unicode losslessly; original logical PK/FK/three indexes, atomic IDs, unique transactional likes and request-time counts remain. This is an explicit PostgreSQL-native deviation from the historical SQLite-only type/deployment rule, not changed application data. Writes use logged tables, `fsync`, `synchronous_commit`, `full_page_writes` on. Normal actual restart persistence passed; **power-loss/provider-storage durability is not established**.

This is an explicit **API-serving subset**, excluding unused Studio, Storage, Realtime, analytics/logging, Vector, Supavisor and imgproxy. It is not the default full-stack sizing/minimum or feature-completeness claim.

## Correctness, frozen source and reproduction

[Fresh complete raw correctness log](setup-evidence/full-correctness.log) and [attestation](setup-evidence/full-correctness-manifest.json):

- 42 inherited exact-byte checks; 6 shared API/concurrency/auth tests; 5 native RPC/API-key/permission/encoding tests.
- 1 seed-log privacy test; 5 strict JSON/body/ID/JWT/native-bridge contract tests; 4 workload/schema tests.
- 24 original scoring/host tests; 3 isolation; 3 native harness; 2 Compose/config; 3 native import/storage/operator; 5 aggregate-budget; 3 frozen-evidence; 3 repository artifact-policy regressions.
- Actual stopped-database failure/degraded health/sanitized writes, recovery, and acknowledged post/exactly-once like across actual five-process restart.

Expected red/reproduction/green attempts remain in [implementation checks](../implementation-checks/), including exact-byte like response order, strict body/claims, native authorization, official bootstrap dependency/operator role, Compose memory-string representation and existing artifact-ignore policy synchronization. The initial incomplete owned database volume is retained, not deleted; current volume is `baas-supabase-vps16_pgdata2`. Private bootstrap logs remain private. No numerical limit/SLO was tuned to repair setup.

Scored source base: **`3b1fa99a4ecf241b40d322aef029879061f8b25e`**, with an explicitly dirty native Supabase overlay. Each immutable run retains `git_status`, `working-tree.patch`, original `source.tar.gz`, exact app/verification/runtime/schema/image/host/token/tool fingerprints, reset/correctness logs and raw evidence. Source archives and base-commit files independently reproduce app and verification hashes. [Final live attestation](setup-evidence/final-deployment-attestation.json) matched unchanged inputs after all holds. A later non-destructive repository merge preserved both the already-published TrailBase commit and its preexisting local artifact-storage amendment; it did not alter measured VPS code. No GitHub CI execution is claimed.

On the designated native host, after the owned profile/private CLI prerequisites in [the lifecycle guide](../../../services/supabase/README.md):

```bash
bash services/supabase/run.sh build
bash services/supabase/run.sh up
bash services/supabase/run.sh test
bash services/supabase/run.sh bench --vus 1000 --smoke
bash services/supabase/run.sh search --max-vus 20000 --max-attempts 12
```

Full protocol: 30s warm ramp, 120s warm hold at up to 1,000 VUs, 60s target ramp, 300s scored hold, 30s drain, 10s HTTP timeout; no TLS on the isolated Docker/loopback benchmark path. Timing uses explicit scenario-start/phase tags, not runner initialization. Reset/import/verification/maintenance are untimed. Exact gateway/native runtime/pool/timeouts are pinned source inputs; no hidden external autoscaling, scale-to-zero or app placement.

## Publication and artifact availability

[Machine-readable result](confirmed-capacity.json), [campaign state](campaign.json), all 13 calibration/scored run directories and original per-run `SHA256SUMS` are retained. Reports, logs, metrics summaries, resources, manifests, code, helpers and checksums are checked in. **The latest Git tree excludes bulky `samples.json.gz` and `source.tar.gz` under the preexisting [artifact policy](../../README.md); they remain intact locally and on the designated VPS, not publicly downloaded from this checkout. No external artifact location/upload has been established.** A partial clone cannot satisfy all original per-run checksums until those original files are restored. New runs cannot regenerate historical timing samples. Do not rewrite checksums or raw evidence to disguise partial availability.

Owner authorization covers repository commit/push, not release creation or unrelated uploads. No runtime keys, issued JWTs, private gateway config, database volumes, bootstrap logs, SSH material or complete container environments are published. PocketBase and all later implementations remain deferred; this report does not authorize starting them.
