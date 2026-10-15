# TrailBase small — 2500 VUs (capacity)

Outcome: **pass** — hold gates passed.

This is one `vps-linux-amd64` / `linux/amd64` shared-host attempt, **not a maximum-capacity score**. Capacity attempt: see campaign.json for search/confirmation status.

- Runner profile: `k6-2cpu-4g-v2` (2 CPU / 4 GiB RAM / no swap); serving tier unchanged.
- Hold requests: 79424; throughput: 264.75 requests/s.
- Hold p50/p95/p99: 1.7199685 / 4.627287849999996 / 15.120293680000094 ms.
- Contract/transport/status error rate: 0.
- Full endpoint summaries: `k6-summary.json`; all raw metric points: `samples.json.gz`.
- CPU/RAM/I/O/network, host VM/swap/thermal evidence: `resources.jsonl`.
- Hardware, actual cgroup limits, image IDs, auth, source revision and caveats: `manifest.json`.
- Canonical data: `dataset.json`; prior full correctness gate: `correctness.log`.
- Uncommitted source is retained in `source.tar.gz` and `working-tree.patch`; verify `SHA256SUMS`.
- Cost basis: existing shared VPS; monthly price not supplied; cost/request not calculated.

Reproduce from the source snapshot with `bash services/trailbase/run.sh build`, `bash services/trailbase/run.sh test`, then `TIER=small caffeinate -i bash services/trailbase/run.sh bench --vus 2500`. See `services/trailbase/README.md` and `contracts/BENCHMARK.md` for the frozen protocol and limitations.

Publication is local repository artifacts only. No push, release, upload, or service progression was performed. Human review/acceptance remains required.
