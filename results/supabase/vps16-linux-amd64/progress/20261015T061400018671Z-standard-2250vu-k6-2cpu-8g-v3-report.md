# Supabase standard — 2250 VUs (capacity)

Outcome: **fail** — hold latency/error/schema gate failed.

One shared-host attempt, **not a maximum-capacity score**. Full 300-second scored hold; see campaign search and independent confirmations.

- Entire five-component serving stack: **1 CPU / 4 GiB / no swap**, one kernel-enforced parent cgroup.
- Separate runner: **2 CPU / 8 GiB / no swap**, `k6-2cpu-8g-v3`.
- Hold requests: 70504; throughput: 235.01 requests/s.
- p50/p95/p99: 31.591025 / 744.5644386999995 / 1503.4388443100013 ms; maximum: 6264.69384 ms.
- Request/schema errors: 0.00019857029388403494 / 0.
- Compatibility identities/JWTs, **not native signup/login/session throughput**; native Auth included in serving budget.
- Native path: Envoy → Edge Functions → Envoy → PostgREST RPC → PostgreSQL. No direct driver, result/like-count/JWT-verification caches.
- API-serving subset: unused dashboard/storage/realtime/analytics/pooler services excluded, not a full default-stack claim.
- Canonical logical data/hash: `dataset.json`; original complete correctness: `correctness.log`, `correctness-manifest.json`.
- Raw samples and endpoint metrics: `samples.json.gz`, `k6-summary.json`; all six containers, aggregate cgroup and raw host counters: `resources.jsonl`.
- Images, actual budgets, lifecycle identities, source/runtime/schema fingerprints and caveats: `manifest.json`.
- Reproduction overlay: `source.tar.gz`, `working-tree.patch`, base commit in manifest. Verify **SHA256SUMS**. Private keys/tokens/runtime data are intentionally excluded.
- Shared VPS price/region unknown; no cost/request or dedicated-$12 equivalence claim.
