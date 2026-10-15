# Original 2-GiB load runner: paused campaign review

The [original small-tier campaign](20261014T230530Z-small-campaign.json) paused after two attempts. **No maximum-capacity score or three-hold confirmation was established.** These are historical measurements with the original 2-CPU/2-GiB/no-swap k6 budget, not the current `k6-2cpu-4g-v2` cohort.

## Observed outcomes

| Attempt | Five-minute hold | Result | Interpretation |
|---|---|---|---|
| [2,500 VUs](20261014T175809892294Z-small-2500vu/report.md) | 79,191 requests; 263.97 requests/s; p95 4.032284 ms; p99 7.338109 ms; zero request/schema errors | Pass | One passing hold only, not a confirmed capacity score |
| [5,000 VUs](20261014T181104528424Z-small-5000vu/report.md) | No completed k6 summary | Invalid | Load generator OOM, not TrailBase capacity failure |

The 5,000-VU [manifest](20261014T181104528424Z-small-5000vu/manifest.json) records `load_after.State.OOMKilled=true`, `ExitCode=137`, and a 2,147,483,648-byte memory/swap-total limit. Docker memory sampling peaked at 99.63% of that limit. TrailBase's target container remained running, healthy, not OOM-killed, with unchanged restart count. Raw metric points and resource logs remain available; the absent k6 summary means a full hold cannot be scored.

The historical report's stated reason, `missing k6 scenario-start clock`, is preserved rather than rewritten. Investigation found that argument evaluation tried to read the missing summary clock before the resource classifier could inspect the known OOM. The new classifier gives a known runner OOM diagnostic precedence while retaining the same **invalid** outcome. Regression red/reproduction/green logs are retained under [implementation-checks/](implementation-checks/).

## Timing and environment caveats

The 2,500-VU scenario start was epoch `1792000741.486`; its scored hold was `[1792000951.486, 1792001251.486)`. Its resource checks passed. A 174.23-second monitoring gap began at scenario +542.60 seconds, **after** the scored hold and nominal drain, so it was outside the hold-monitoring gate. This does not establish why the gap occurred.

The next attempt's directory timestamp was 18:11 UTC, but its manifest records load startup at 23:01 UTC: a roughly five-hour wall-clock gap occurred before the timed workload, during preparation/reset. Sleep/interruption is a concern, not a proven diagnosis from these files alone. No interrupted hold is silently accepted, and no global power setting was changed.

## Owner-approved continuation (2026-10-14)

- Increase only k6 RAM to **4 GiB**, retaining 2 CPU and no container swap. TrailBase remains **1 CPU / 2 GiB**, with identical app, dataset, workload, and serving settings.
- Identify the new cohort as **`k6-2cpu-4g-v2`** in run IDs, manifests, summaries, and campaign records. Restart scored measurements; do not pool historical v1 holds into v2 confirmations.
- Rerun the full correctness gate and a 5,000-VU unscored calibration before the new capacity campaign.
- Use **command-scoped `caffeinate -i`**, not permanent power changes, to prevent idle sleep during runs. Manual sleep/lid closure can still interrupt measurements.
- Require at least **1 GiB VM/OS memory reserve** beyond serving and runner cgroup budgets. Small fits the current 8,392,929,280-byte OrbStack VM; large does not. Larger-tier benchmarking requires a separate owner/headroom review. Do not automatically change OrbStack settings.

See [the amended benchmark contract](../../contracts/BENCHMARK.md). All prior attempt files and their checksums remain immutable. Publication is local repository evidence only; no commit, push, upload, or later-service work has occurred.
