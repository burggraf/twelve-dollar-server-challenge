# TrailBase standard — 5000 VUs (capacity)

Outcome: **pass** — hold gates passed.

This is one `vps16-linux-amd64` / `linux/amd64` shared-host attempt, **not a maximum-capacity score**. Capacity attempt: see campaign.json for search/confirmation status.

- Serving tier: `standard` (1 CPU / 4 GiB RAM / no swap).
- Runner profile: `k6-2cpu-8g-v3` (2 CPU / 8 GiB RAM / no swap).
- Hold requests: 158849; throughput: 529.50 requests/s.
- Hold p50/p95/p99: 0.621706 / 1.2344452000000008 / 8.062135599999992 ms.
- Contract/transport/status error rate: 0.
- Full endpoint summaries: `k6-summary.json`; all raw metric points: `samples.json.gz`.
- CPU/RAM/I/O/network, host VM/swap/thermal evidence: `resources.jsonl`.
- Hardware, actual cgroup limits, image IDs, auth, source revision and caveats: `manifest.json`.
- Canonical data: `dataset.json`; prior full correctness gate: `correctness.log`.
- Uncommitted source is retained in `source.tar.gz` and `working-tree.patch`; verify `SHA256SUMS`.
- Cost basis: existing shared VPS; monthly price not supplied; cost/request not calculated.

Reproduction environment: `export BENCHMARK_PROJECT=baas-trailbase-vps16 BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3 TIER=standard TRAILBASE_PORT=14000`. From the source snapshot, build with the documented bounded builder, run `bash services/trailbase/run.sh test`, then `bash services/trailbase/run.sh bench --vus 5000`. See `services/trailbase/README.md`, `services/trailbase/VPS16.md`, and `contracts/BENCHMARK.md` for setup, the frozen protocol, and limitations.

Publication is local repository artifacts only. No push, release, upload, or service progression was performed. Human review/acceptance remains required.
