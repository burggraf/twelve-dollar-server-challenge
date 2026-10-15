# Supabase benchmark evidence

**Confirmed capacity: 2,000 VUs**, the highest candidate passing three independent five-minute holds at the fixed 250-VU search resolution. **Not an exact mathematical maximum:** 2,250 passed one probe but failed all three confirmations. [Final report](vps16-linux-amd64/CONFIRMED_CAPACITY.md) · [Machine-readable result](vps16-linux-amd64/confirmed-capacity.json) · [Endpoint metrics](vps16-linux-amd64/endpoint-confirmations.md).

The three final holds delivered **210.86–211.69 requests/s**, with **7 request errors in 190,165 requests** and **zero malformed successful responses**. All 11 scored attempts and both unscored calibrations are retained; original quantiles were reproduced from raw samples. Complete resource/source/data/correctness/image/checksum/continuity review passed. The completed owned stack is stopped with both original/current data volumes and all evidence retained.

- Serving: **all five** PostgreSQL, Auth, PostgREST, Edge Runtime and Envoy containers share **one actual 1-CPU / 4-GiB / zero-swap parent cgroup**, not per-container allocations.
- Runner: separate **2 CPU / 8 GiB / zero swap**, `k6-2cpu-8g-v3` and unchanged k6 workload/SLOs.
- Native path: Envoy → Edge Functions → Envoy API-key layer → PostgREST transactional RPC/JWT → PostgreSQL. No timed direct driver, response/like-count/JWT-verification caches.
- Scope: compatibility application identities/JWTs; **not native Auth signup/login/session throughput**. Native Auth runs within the serving budget; initial native Auth account count is zero.
- Canonical data: **50,000 app users / 500,000 posts / 2,016,005 likes**, full original logical SHA-256 `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`.
- Disclosed native mapping: UTF-8 `bytea` bodies and base64 RPC preserve U+0000 and exact JSON strings; original logical data, PKs/FKs/indexes, ordering, idempotency and request-time counts retained.
- Existing **26 persistent services and original loopback-4000 listener** were unchanged after the full correctness gate. Only owned benchmark ingress **127.0.0.1:14000** is published.

[Profile, pins, auth/data details and lifecycle](../../services/supabase/README.md). [Implementation red/green evidence](implementation-checks/). [Native host evidence](vps16-linux-amd64/).

## Initial unscored calibration

| Run | Scored? | Requests / throughput | p50 / p95 / p99 | Errors | Outcome |
|---|---|---|---|---|---|
| [Initial 1,000 VUs](vps16-linux-amd64/20261015T044425811639Z-standard-1000vu-k6-2cpu-8g-v3-smoke/report.md) | No; 20-second smoke hold | 2,238 / 111.90 requests/s | 4.38 / 45.34 / 144.24 ms | 0 request/schema | Pass |
| [Final-source 1,000 VUs](vps16-linux-amd64/20261015T045317043850Z-standard-1000vu-k6-2cpu-8g-v3-smoke/report.md) | No; 20-second smoke hold | 2,194 / 109.70 requests/s | 4.28 / 95.67 / 152.52 ms | 0 request/schema | Pass |

Original checksums, raw stream, source-archive privacy, aggregate kernel limits and scoring replay were verified. These are pipeline calibrations, **not sustained capacity or a maximum**. After synchronizing the repository's existing bulk-artifact ignore-policy regressions, [fresh full correctness](vps16-linux-amd64/setup-evidence/full-correctness.log) and the final-source calibration passed. [Native resource replay](vps16-linux-amd64/setup-evidence/final-calibration-resource-review.json) found no paging, runner saturation, serving restart or frozen-input drift. No serving cap, executable API code, workload or SLO was tuned by that policy synchronization. Scored-cohort inputs are frozen.

## Evidence integrity and limitations

Every scored attempt must retain original raw samples, native/aggregate/host resources, summary, endpoint metrics, full correctness, canonical reset/hash, source overlay, selected images, runtime/schema/host/token fingerprints and original `SHA256SUMS`. All failed/invalid attempts remain distinct; runner/host invalidity cannot form a target-failure bracket. No cross-host/profile/verification-input confirmations are pooled.

This is an explicitly reduced **API-serving subset**, not the complete default Supabase platform; unused Studio, Storage, Realtime, analytics/logging, Vector, Supavisor and imgproxy are excluded. No dedicated-machine or $12/month equivalence is claimed; price/region are unknown. Power-loss durability and native login throughput are unmeasured.

Private runtime keys, issued JWTs, rendered gateway config, database volumes and bootstrap logs are never published. Bulky generated streams/source archives are retained without rewriting but excluded from the current Git tree by [repository artifact policy](../README.md). Full native bundles currently require the retained local/VPS copies; no new external artifact upload location has been established.
