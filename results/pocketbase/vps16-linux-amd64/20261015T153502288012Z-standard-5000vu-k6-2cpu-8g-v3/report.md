# PocketBase standard — 5000 VUs (capacity)

## Tested software and VPS slice

- **PocketBase v0.40.5**, upstream `6f370ea741f33adf889eef02e3c1b884a47aa522`; **Go 1.27.2**; upstream default **SQLite 3.53.4 / modernc.org/sqlite v1.60.1**. Immutable builder/runtime pins, native executable/image IDs and source hashes are in `manifest.json`.
- **Entire serving stack: 1 vCPU quota / 4 GiB RAM (4,294,967,296 bytes) / no swap**, including native HTTP/routes/Auth/REST/admin APIs and embedded main/auxiliary databases, under one kernel-enforced parent budget.
- **Separate runner: k6 1.3.0 / 2 vCPU quota / 8 GiB RAM (8,589,934,592 bytes) / no swap**, `k6-2cpu-8g-v3`.
- This is a quota-limited **shared-host slice** on native AMD64 `azabab.com`, not a dedicated 1-vCPU VPS or a measured $12/month offering.


Outcome: **pass** — hold gates passed.

One attempt, **not a maximum-capacity score**. Full 300-second hold; see search and independent confirmations.

- Hold requests: 158597; throughput: 528.66 requests/s.
- p50/p95/p99: 0.626335 / 21.647994999999998 / 49.69875964000002 ms; maximum: 205.873223 ms.
- Request/schema errors: 0 / 0.
- Supported native Go extension/DB/Record transaction path; compatibility JWTs checked per write, not native Auth throughput.
- Original canonical logical data/hash: `dataset.json`; complete native correctness: `correctness.log`, `correctness-manifest.json`.
- Native Text IDs/numeric ordering, extra like IDs, platform metadata and native relation validation mapping are disclosed in source/profile and manifest.
- Original samples, quantiles/statuses/endpoint metrics and raw target/runner/parent/host counters: `samples.json.gz`, `k6-summary.json`, `resources.jsonl`.
- Immutable image/build IDs, actual kernel budgets, lifecycle identities, source/runtime/schema fingerprints and caveats: `manifest.json`.
- Source reproduction overlay: `source.tar.gz`, `working-tree.patch`, base commit in manifest. Verify **SHA256SUMS**; private keys/tokens/runtime database files excluded.
- Ordinary restart persistence is not a provider power-loss test. Shared-host price/region unknown; no dedicated-$12 or cost/request claim.
