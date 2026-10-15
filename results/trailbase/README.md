# TrailBase results and evidence

**Current status: all future product tests use the 16-GiB native AMD64 host; fresh 1-CPU/4-GiB correctness and 5,000-VU calibration passed; full holds passed through 15,000 VUs; 20,000 paused on generator OOM; all three additional independent 15,000-VU confirmation holds passed, with full source/checksum/resource review complete. Confirmed lower bound: **15,000 VUs**, not a maximum-capacity score. [Final report](vps16-linux-amd64/CONFIRMED_LOWER_BOUND.md).** See [current primary evidence](vps16-linux-amd64/README.md) and [safe setup](../../services/trailbase/VPS16.md). The common aggregate serving tier is now **standard: 1 CPU/4 GiB**, with **2 CPU/8 GiB** k6 profile `k6-2cpu-8g-v3`, no container swap. Existing services and loopback port 4000 are preserved; benchmark HTTP uses loopback 14000. Current-source full correctness and calibration are verified; confirmation/resource/service-continuity review is complete. The owner authorized commit/push and direct progression to **Supabase before PocketBase** on the same configuration. Both the failed unscored 10,000-VU latency check and passing 5,000-VU calibration are retained, with no OOM. All 26 persistent system-service identities and the original port-4000 listener remained unchanged; the root SSH-session manager lifecycle is disclosed separately.

Historical Mac and 8-GiB VPS results stay in their own immutable tracks. The 8-GiB host passed five-minute search holds at 2,500 and 5,000 VUs, then k6 OOM-killed at 10,000 under its 4-GiB limit; TrailBase remained healthy. That is not a measured target maximum. No prior host/tier/profile hold supplies confirmation for the new baseline. No original dedicated $12-cloud-VM or cost/request equivalence is claimed.

## Historical 8-GiB native VPS track — runner-limited pause

[Complete native build/correctness/calibration/campaign evidence](vps-linux-amd64/README.md) is retained with verified checksums. One pre-workload ARM64 k6 fallback was fixed and retained invalid. Fresh native search then passed at 2,500 and 5,000 VUs (5,000: 158,750 requests, p95 7.54 ms / p99 24.09 ms, zero errors) before 10,000-VU generator OOM paused it. One unrelated pre-existing app had a clean stop/start of unknown cause during that campaign; lifecycle commands from the benchmark targeted only its own containers, and no absence-of-interference claim is made. See [original VPS setup](../../services/trailbase/VPS.md).

## Mac runner v2 — 2 CPU / 4 GiB / no swap

Full correctness passed again against the unchanged app and small serving tier. Logs/attestation are retained as `implementation-checks/runner-v2-correctness*`; profile/budget/headroom and OOM-diagnostic red/green tests are retained alongside them.

| Run | Mode | Outcome |
|---|---|---|
| [First 5,000-VU calibration](20261014T231310540419Z-small-5000vu-k6-2cpu-4g-v2-smoke/report.md) | Unscored 20-second hold | Invalid: macOS swap-outs increased; no runner OOM |
| [Single 5,000-VU retry](20261014T231534625521Z-small-5000vu-k6-2cpu-4g-v2-smoke/report.md) | Unscored 20-second hold | Invalid: macOS `top` timed out after 5 seconds; monitoring incomplete |

That calibration completed with 10,973 hold requests and zero request/schema errors, but those are **invalid diagnostic measurements**, not a score or a passed calibration. k6 peaked at 47.38% of its 4-GiB memory limit; the host swap-out counter increased by 21,392 16-KiB pages (334.25 MiB). Limits and rejection rules have not been weakened. The single same-profile retry was also invalid due to monitor failure, with severe diagnostic request latency/errors and no complete monitoring window. Available samples cannot establish whether paging recurred after the monitor stopped. See [the v2 review](runner-v2-calibration-review.md); further attempts await owner direction, not automatic advancement.

## Historical capacity campaign — original 2-GiB runner

See [the campaign review and approved continuation](runner-v1-campaign-review.md), with raw manifests and the preserved [paused campaign record](20261014T230530Z-small-campaign.json).

| Run | Hold requests / throughput | p95 / p99 | Errors | Outcome |
|---|---:|---:|---:|---|
| [2,500 VUs](20261014T175809892294Z-small-2500vu/report.md) | 79,191 / 263.97 requests/s | 4.03 / 7.34 ms | 0% | One passing five-minute hold, not a maximum score |
| [5,000 VUs](20261014T181104528424Z-small-5000vu/report.md) | No complete summary | N/A | N/A | Invalid: k6 OOM-killed, exit 137; target healthy |

The original 5,000-VU report's missing-clock reason is preserved. The known OOM prevented completion of the summary; new classification reports that cause first. Neither that invalid attempt nor its missing clock defines a TrailBase failure bracket.

## Unscored pipeline checks — historical 2-GiB runner

| Run | VUs | Hold | p95 / p99 | Hold errors | Interpretation |
|---|---:|---:|---:|---:|---|
| [Initial pipeline](20261014T174258157655Z-small-25vu-smoke/report.md) | 25 | 20 s | 3.70 / 5.43 ms | 0% | Historical smoke before least-privilege k6 mounts and scenario-clock refinement |
| [Isolated runner](20261014T174842135140Z-small-25vu-smoke/report.md) | 25 | 20 s | 11.19 / 15.57 ms | 0% | Smoke with isolated mounts and actual k6 scenario clock; before added host CPU/I/O and kernel-limit capture |
| [Completed-runner calibration](20261014T175228740434Z-small-1000vu-smoke/report.md) | 1,000 | 20 s | 5.84 / 16.89 ms | 0% | 2,215 hold requests, 110.75 requests/s; full resource/kernel-limit/disk capture |

These are **not capacity scores**, rankings, 5-minute holds, or evidence that 25 is the service's user limit. Different smoke revisions are kept with their original source snapshots; raw evidence is not rewritten to match newer code. The completed 1,000-VU calibration passed, with peak load-container CPU 32.16% (of a 200% quota) and memory 19.36% of its 2-GiB limit. Actual target cgroups read `cpu.max=100000 100000`, `memory.max=2147483648`, `memory.swap.max=0`. Host CPU/I/O/thermal/VM samples and allocated-data growth are retained. These short samples still do not establish steady-state maximum capacity.

Each run directory contains raw compressed k6 points, the complete k6 summary, resource JSONL, source snapshot, tracked patch, correctness and reset logs, dataset manifest, selected Docker state, summary/report, and SHA256 checksums. The source snapshot captures uncommitted code because this work has not been committed. Do not treat the base Git commit alone as the tested implementation.

## Correctness and implementation evidence

The suite covers 42 inherited checks, six additional black-box regressions, native Record API read/write denial, storage failure/recovery, actual restart persistence, Rust contract tests, seed privacy, workload validation, score/monitor fail-closed cases, and resolved Compose isolation. Current full logs are retained in `implementation-checks/` and the run directories. A separate brand-new-volume boot regression passed and its start/cleanup evidence is retained too. CI configuration has been added but has **not** been run on GitHub from this local session.

`implementation-checks/` also retains raw failing TDD output and the first tooling build failure (missing CA trust in the slim base image). The CA issue was resolved using certificates from another pinned official image, not by disabling TLS verification. The initial depot permissions issue was fixed in the image; no platform-generated credentials or bootstrap logs are published.

See [TrailBase's README](../../services/trailbase/README.md), [the frozen benchmark contract](../../contracts/BENCHMARK.md), and [the master plan](../../MASTER_PLAN.md) for reproduction and progression gates.

The owner authorized repository commit/push on 2026-10-15; that publication is being executed. No release or unrelated public upload is authorized. Supabase is next by explicit owner priority; PocketBase remains untouched.
