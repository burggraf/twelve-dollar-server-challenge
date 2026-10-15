# Runner v2 calibration: paused for host review

**Status: no valid v2 calibration or maximum-capacity score. Further load attempts are paused pending owner direction.** This is an investigation note, not an accepted final blocked outcome or permission to advance to PocketBase.

The owner approved `k6-2cpu-4g-v2` (2 CPU / 4 GiB / no container swap), unchanged TrailBase small tier (1 CPU / 2 GiB), fresh scored measurements, and command-scoped `caffeinate -i`. The full correctness gate passed again; [its raw log](implementation-checks/runner-v2-correctness.log) and [attestation](implementation-checks/runner-v2-correctness-manifest.json) are retained. The original [2-GiB runner campaign](runner-v1-campaign-review.md) remains a separate immutable cohort.

## Two retained attempts

| Attempt | Outcome | Evidence |
|---|---|---|
| [First 5,000-VU smoke](20261014T231310540419Z-small-5000vu-k6-2cpu-4g-v2-smoke/report.md) | Invalid: host swap-outs increased | [Manifest](20261014T231310540419Z-small-5000vu-k6-2cpu-4g-v2-smoke/manifest.json), [resource JSONL](20261014T231310540419Z-small-5000vu-k6-2cpu-4g-v2-smoke/resources.jsonl) |
| [Single same-profile retry](20261014T231534625521Z-small-5000vu-k6-2cpu-4g-v2-smoke/report.md) | Invalid: resource monitor failed | [Manifest](20261014T231534625521Z-small-5000vu-k6-2cpu-4g-v2-smoke/manifest.json), [resource JSONL](20261014T231534625521Z-small-5000vu-k6-2cpu-4g-v2-smoke/resources.jsonl) |

Both attempts were **unscored 20-second calibrations**, not five-minute capacity/confirmation holds. Neither is a TrailBase failing bracket. Both retain complete available raw metrics, summary, selected container state, source, correctness evidence, and SHA256 checksums.

### First calibration

k6 exited 0 and was not OOM-killed, peaking at 47.38% of its 4-GiB limit. It recorded 10,973 hold requests and zero request/schema errors. However, macOS `Swapouts` increased from 15,752,219 to 15,773,611 pages: **334.25 MiB** at the recorded 16-KiB page size. The unchanged host-swap rule rejected the attempt. Existing swap usage alone is not the gate; new swap-outs during the attempt are.

### Retry

The second of just two resource samples records:

```text
Command '['top', '-l', '2', '-s', '1', '-n', '0']' timed out after 5 seconds
```

The monitor correctly stopped and the attempt was invalidated. The available samples do **not** certify the scored window or establish whether swapping recurred later. k6 exited 99 with threshold failures; its diagnostic summary also shows severe request latency/errors and incomplete response-validation counts. Those figures are not accepted capacity measurements. They do not isolate the target from load-generator/VM/host scheduling, paging, or other interference.

The selected before/after container state shows no TrailBase OOM/restart and no k6 OOM. Remaining healthy is not proof of meeting latency SLOs, and absent OOM is not proof of an adequate generator or stable host.

## Next-step boundary

- Do not keep retrying, weaken monitoring/swap rules, mix historical cohorts, or declare a TrailBase capacity limit from these attempts.
- Await owner direction: free host resources and resume the same-profile calibration; explicitly choose lower-load exploration and a possible lower-bound report; or request a final blocked-outcome publication/review.
- Read-only process inventory collected executable basenames and resident-memory totals only, not process arguments/environments. It cannot identify the cause of past interference. No unrelated workload was stopped.
- Larger-tier benchmarking remains separately blocked by the current VM memory preflight. No automatic power/OrbStack settings change, dependency installation, commit, push, public upload, or later-service work was performed.

See [the benchmark contract](../../contracts/BENCHMARK.md) and [results index](README.md). The benchmark target remains available locally for inspection; no load generator or campaign should be running at this checkpoint.
