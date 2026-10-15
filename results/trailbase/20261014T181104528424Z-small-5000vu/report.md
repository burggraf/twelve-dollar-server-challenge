# TrailBase small — 5000 VUs (capacity)

Outcome: **invalid** — missing k6 scenario-start clock.

This is one local ARM64 OrbStack attempt, **not a maximum-capacity score**. Capacity attempt: see campaign.json for search/confirmation status.

- Hold requests: 0; throughput: 0.00 requests/s.
- Hold p50/p95/p99: N/A / N/A / N/A ms.
- Contract/transport/status error rate: N/A.
- Full endpoint summaries: `k6-summary.json`; all raw metric points: `samples.json.gz`.
- CPU/RAM/I/O/network, host VM/swap/thermal evidence: `resources.jsonl`.
- Hardware, actual cgroup limits, image IDs, auth, source revision and caveats: `manifest.json`.
- Canonical data: `dataset.json`; prior full correctness gate: `correctness.log`.
- Uncommitted source is retained in `source.tar.gz` and `working-tree.patch`; verify `SHA256SUMS`.
- Local hardware has no measured cloud monthly price; cost/request is not applicable.

Reproduce from the source snapshot with `bash services/trailbase/run.sh build`, `bash services/trailbase/run.sh test`, then `TIER=small bash services/trailbase/run.sh bench --vus 5000`. See `services/trailbase/README.md` and `contracts/BENCHMARK.md` for the frozen protocol and limitations.

Publication is local repository artifacts only. No push, release, upload, or service progression was performed. Human review/acceptance remains required.
