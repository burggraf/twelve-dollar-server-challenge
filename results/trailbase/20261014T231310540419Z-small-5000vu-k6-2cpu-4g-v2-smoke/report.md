# TrailBase small — 5000 VUs (smoke)

Outcome: **invalid** — host swap-outs increased during this attempt.

This is one local ARM64 OrbStack attempt, **not a maximum-capacity score**. Smoke only: shortened timing, not scored.

- Runner profile: `k6-2cpu-4g-v2` (2 CPU / 4 GiB RAM / no swap); serving tier unchanged.
- Hold requests: 10973; throughput: 548.65 requests/s.
- Hold p50/p95/p99: 2.311199 / 106.47046559999998 / 191.96949783999997 ms.
- Contract/transport/status error rate: 0.
- Full endpoint summaries: `k6-summary.json`; all raw metric points: `samples.json.gz`.
- CPU/RAM/I/O/network, host VM/swap/thermal evidence: `resources.jsonl`.
- Hardware, actual cgroup limits, image IDs, auth, source revision and caveats: `manifest.json`.
- Canonical data: `dataset.json`; prior full correctness gate: `correctness.log`.
- Uncommitted source is retained in `source.tar.gz` and `working-tree.patch`; verify `SHA256SUMS`.
- Local hardware has no measured cloud monthly price; cost/request is not applicable.

Reproduce from the source snapshot with `bash services/trailbase/run.sh build`, `bash services/trailbase/run.sh test`, then `TIER=small caffeinate -i bash services/trailbase/run.sh bench --vus 5000 --smoke`. See `services/trailbase/README.md` and `contracts/BENCHMARK.md` for the frozen protocol and limitations.

Publication is local repository artifacts only. No push, release, upload, or service progression was performed. Human review/acceptance remains required.
