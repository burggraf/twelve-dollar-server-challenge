# BaaS workload v1: local OrbStack and separate native VPS track

This fork retains the five endpoints and exact JSON/errors in [SPEC.md](../SPEC.md), including its full golden suite. It replaces the SQLite-only runtime/submission rules with per-product native implementations. Physical schemas may adapt types/IDs and platform metadata; equivalent baseline indexes are allowed. No response/query-result caches, precomputed counters, or JWT-verification caches in application code. Platform caches/retries are disclosed, not represented as identical across products.

## Current primary profile — 16-GiB native AMD64 host

**Owner amendment, 2026-10-15:** all future BaaS product tests run on the designated 16-GiB host. The common primary serving tier is now **`standard`: 1 CPU / 4 GiB aggregate RAM**, with a separate **2 CPU / 8 GiB / no-swap** runner, **`k6-2cpu-8g-v3`**. The entire serving stack shares the budget, not each container independently. This is not the older four-CPU `large` tier. Supabase and later products must demonstrate fit; no fit or performance outcome is assumed.

The prior 8-GiB VPS passed 2,500/5,000-VU search holds, then k6 was OOM-killed at 10,000 VUs under the four-GiB runner. That invalid attempt does not establish TrailBase's maximum. All host/tier/runner changes require fresh correctness and independent scored holds; old results remain immutable and are not pooled. New output is `results/trailbase/vps16-linux-amd64/`, isolated by `baas-trailbase-vps16`. See [the current host guide](../services/trailbase/VPS16.md).

The host has four CPUs. Preflight requires serving + runner quotas **plus one CPU**, and serving + runner RAM **plus one GiB**, leaving additional headroom for existing workloads. Standard fits (3 CPU/12 GiB combined container ceilings); the legacy four-CPU serving tier does not fit with a separate two-CPU runner on this host and is rejected. Check available headroom and monitor host activity; do not modify existing services to make room. The existing loopback port-4000 listener is untouched; benchmark ingress uses loopback **14000**. No global package/plugin/power/firewall changes or unrelated-service lifecycle actions.

## Historical local profiles — runner v2

| Profile | Entire serving stack | Runtime threads (TrailBase) | k6 container |
|---|---|---|---|
| small | 1 CPU quota, 2 GiB RAM, no container swap | 1 | 2 CPU quota, 4 GiB RAM, no container swap |
| large | 4 CPU quota, 4 GiB RAM, no container swap | 4 | same |

**Owner-approved amendment, 2026-10-14:** runner profile `k6-2cpu-4g-v2` replaces the original 2-CPU/2-GiB runner after k6 was OOM-killed at 5,000 VUs. Workload v1 and serving tiers are unchanged. Historical v1 attempts remain immutable and are not pooled with v2 scored measurements; capacity search restarts with fresh correctness evidence. Every new run/summary/campaign identifies the runner profile and verifies its actual Docker limits.

Before any benchmark reset, the runner requires VM memory to cover the serving tier, 4-GiB load generator, and at least 1 GiB of VM/OS reserve. Small fits the current 8,392,929,280-byte VM; large does **not**, so larger-tier benchmarks stop for owner/headroom review rather than silently overcommitting or changing global settings. This reserve is a preflight floor, not proof against contention; runtime invalidation still applies.

Serving-stack limits include database, BaaS, adapter/functions, and ingress where applicable. TrailBase needs one container, so its cgroup enforces the whole budget. Other stacks must allocate limits whose totals fit the same tier, or use verified aggregate enforcement. The shared OrbStack VM and macOS overhead are outside these container budgets. Host paging is monitored; these are **not dedicated $12 cloud-VM equivalents**. Do not change global OrbStack settings or stop unrelated workloads without approval.

Current host inventory is recorded per run, not assumed from the planning document. Only native ARM64 results belong in the primary local track; emulation and managed-cloud results belong in separate tracks. Cold starts, image downloads, migrations, seeding, and correctness runs are outside scored HTTP latency. Ingress for TrailBase is direct HTTP/1.1 on the Compose network; no Nginx, TLS, or compression. Port 4000 is bound to host loopback only; admin port 4001 is loopback-only inside the service container and is not published.

## Separately labelled VPS track

After host paging/monitor instability paused the Mac work, the owner approved bounded TrailBase tests on an existing shared x86-64 VPS, private pinned CLI plugins, and a dedicated resource namespace. This is **not** a replacement ARM64 result or a dedicated-machine comparison. Record the actual architecture, host versions, serving/runner caps, background-service caveats, and unknown monthly cost; do not pool cross-host holds. Follow [the VPS guide](../services/trailbase/VPS.md). That initial VPS track retained the small serving tier and runner-v2 budget, workload, dataset, auth, SLOs, and three-hold confirmation protocol. It is now paused after generator OOM; the owner designated the 16-GiB host and amended the primary serving/runner budgets as above. Workload/data/auth/SLOs/confirmation remain unchanged.

Linux collection preserves raw `/proc/vmstat`, CPU/memory/disk/load/uptime, and pressure counters without Mac commands or process arguments. Increasing `pswpout` invalidates an attempt just like increasing macOS `Swapouts`. Hardware thermals are not exposed inside the VPS; raw CPU steal/pressure must be reviewed for virtualization/shared-host interference. Platform and project selection rejects emulated images and non-benchmark namespaces. New outputs are separated under `results/trailbase/<deployment-track>/`; historical paths and artifacts remain immutable.

## Data and identities

Canonical export: `node seed/generate.mjs <directory>`, with no changes to its application-data algorithm. TSV fields use tab/newline delimiters without CSV quoting. Import 50,000 users, 500,000 posts, and **2,016,005** unique likes; preserve all seed IDs, timestamps, text, and relationships. Canonical logical row hash is `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`, computed from `users ORDER BY id`, `posts ORDER BY id`, `likes ORDER BY post_id,user_id`, each row joined by `|` and followed by LF. Tokens are time/key-dependent and excluded from this hash and all published artifacts.

The compatibility identity contract uses HS256 tokens for users 1–20,000, with required numeric expiry, positive decimal-string subject, and string username. Validation happens on every write request; auth precedes body/ID validation. Native login/refresh throughput is not measured. TrailBase verifies these tokens inside its WASM handlers and uses the signed subject for all writes; it is not measuring TrailBase's native login/session flow. Native Record API access is read-only, with direct writes denied. No BaaS admin credential is used by k6.

Each attempt stops the service, replaces **only application table contents**, verifies counts/FKs/full logical hash, then restarts and waits for storage health. Platform metadata remains intact. Test writes and previous attempts never carry into another attempt. Warm-up writes within the same attempt do carry into its hold; that rule is the same for every product. Import tooling may use offline native bulk import; the **timed application** must use the product's supported APIs.

## User journey and scoring

`bench/baas.mjs` uses the inherited closed-loop journey: feed, think 3–7 s, detail for a random feed item, think 3–8 s, 15% like probability, 2% create probability, idle 5–15 s. Initial VUs are staggered by 0–5 s. No deterministic random seed is claimed; report actual endpoint mix and repeat runs. The default timeout is 10 s, no client retry or redirects; disclosed platform-internal retries remain included in timings.

Each capacity attempt has a 30 s ramp to `min(1000, target)` VUs, 2 min warm hold, 60 s ramp to target, **5 min scored hold**, and 30 s drain. Graceful ramp-down/stop allowances are 10 s. The lower warm-up load when target <1,000 is the predefined fallback; a warm-up at a higher load than the candidate must not disqualify a low-capacity service. Report that fallback explicitly.

Requests are tagged by their **start time**. Only requests started in the hold are scored; their completed latency/error samples are retained even if they complete during drain. This differs from the inherited script's all-phase aggregate. Raw JSON metric points and whole-run summaries are retained too. Thresholds:

- Hold p95 < 500 ms and p99 < 1,000 ms, with no rounding before evaluation.
- Hold request-error rate < 1%. Unexpected status, transport failure, JSON parse failure, or invalid response counts as a request error, including 2xx responses k6 might otherwise accept.
- Successful-status responses with invalid schemas/content/order have a separate **zero-tolerance schema-error gate**.
- Nonempty hold samples; a missing metric, incomplete validation sample count, runner crash, or contradictory exit status is invalid—not a target-capacity failure.

All four endpoint latencies, counts, and error rates are reported. Feed responses must contain 20 unique posts in timestamp/ID descending order. Create and like checks validate actual body/identity/ID and first/repeat status semantics, not just a 2xx code. Fine-grained concurrency/persistence requirements are covered by the correctness suite, not inferred from load checks.

Search starts at 2,500 VUs, doubles until failure, then narrows to 250-VU steps (25 below 250). A candidate needs **three independent passing 5-minute holds**; confirmation failure steps down. This is stricter than the upstream single hold. Default local safety budgets are 20,000 VUs (unique-token pool) and 12 attempts. Passing an upper budget is only a lower bound; exhausting an attempt budget is a paused campaign, **not a maximum score**. Invalid attempts pause for investigation, never define the failing side of a capacity bracket. A campaign status of `confirmed_pending_human_review` still needs artifact/resource review and acceptance before advancing to PocketBase.

`--smoke` is explicitly unscored: 5 s ramp, 20 s hold, 5 s drain. It validates the real container/load/artifact pipeline, not maximum capacity or statistical stability.

## Resource evidence and invalidation

`resources.jsonl` retains periodic Docker CPU/RAM/I/O/network/PID samples plus raw macOS CPU/I/O headers (no process arguments), VM, swap, and thermal output. Actual Docker limits are inspected, and target CPU/RAM/swap limits are read from the kernel cgroup files—not just requested in YAML. Allocated data-directory KiB before/after the attempt records storage growth. A k6 gauge records the actual scenario start and anchors hold-window resource checks, excluding image-pull delay and VU initialization (container start alone is insufficient). The runner rejects load OOM, missing/broken/sparse hold monitoring, three consecutive hold samples at >=180% Docker CPU (90% of its 2-CPU quota), >=90% runner memory, or increasing host swap-out counters. These rules are fixed before capacity runs within each documented runner-profile cohort. A known runner OOM takes diagnostic precedence when the crash also prevents writing the k6 summary/clock; the attempt remains invalid. Target OOM/restarts/outages are disclosed target outcomes, not discarded as outliers.

Monitoring cannot prove absence of unrelated CPU contention or thermal throttling. Review the raw thermal/VM data and host activity before accepting scores; a shared laptop is a limitation even when automatic checks pass. Do not run builds or other benchmarks during a capacity campaign. With owner approval, run the campaign via `caffeinate -i` to prevent idle sleep only for that command's lifetime; no persistent power setting changes. It does not prevent manual sleep or lid closure, and interrupted hold monitoring still invalidates a run. The orchestrator itself and metrics export add consistent overhead outside the serving cgroup. No power-loss durability equivalence is claimed: acknowledged writes must survive normal service restart; platform persistence settings and guarantees must be disclosed.

## Provenance and publication

Each `results/trailbase/<run-id>/` includes full k6 summary, raw compressed metric stream, resource samples, reset/correctness output, counts/hash, machine-readable summary, selected Docker state/limits, source snapshot, tracked patch, and SHA256 checksums. Source/image labels and correctness attestations must match before running, and the attestation rejects verification inputs changed during testing. Source archives are overlays on the recorded base Git commit, not standalone Git repositories: extract over that checkout to retain upstream files, licenses, and Git provenance before following reproduction commands. Docker environment dumps, platform bootstrap logs (which can contain generated credentials), JWTs, secret files, and database volumes are never published. Runtime/build inputs are pinned in Compose/Dockerfiles/Cargo.lock, including an apt snapshot for the shared runner.

Reports and small supporting evidence are local versioned repository artifacts first. Raw metric streams (`samples.json` / `samples.json.gz`) and generated source overlays (`source.tar.gz`) are retained locally but ignored by Git; new runs generate their own copies, not replacements for historical evidence. A clone is not a complete historical evidence bundle. Preserve original checksums and use separate artifact storage when distributing the bulk files; see [artifact storage](../results/README.md). Do not equate writing local files with an external push/release/public upload. Local hardware has no measured cloud monthly price; cloud cost/request is not applicable. The original upstream challenge results are not comparable entries. No later BaaS starts before the TrailBase outcome is published, reviewed, and accepted.
