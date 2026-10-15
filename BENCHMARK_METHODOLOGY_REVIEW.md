# BaaS benchmark methodology review

## Scope and status

This document records an assessment of the repository's benchmark methodology after reviewing the contract, load generator, seed, correctness tests, serving implementations, and published TrailBase and Supabase confirmation reports. It is a source/evidence review; the benchmarks were not rerun for this assessment.

The recommendations are advisory. They do not amend the frozen workload, authorize implementation changes, or change existing results. Complete the remaining services under the current baseline before introducing separately versioned experiments.

## Overall assessment

**These are credible benchmarks of one specific application architecture—not yet a broad comparison of BaaS capacity.** The methodology is substantially more careful than a typical “requests per second” comparison, but the workload is narrower than the headline “how many users can this backend handle?” suggests.

The results are trustworthy for this question:

> Under a shared 1-vCPU/4-GiB serving budget, how well does this implementation serve a warm, mostly public-read feed application through supported product APIs?

They do **not** yet answer:

> Which BaaS will make my application fastest, support the most real users, or be easiest and safest to operate on a small VPS?

The current results do show a substantial advantage for the tested TrailBase implementation over the tested Supabase implementation. That is meaningful evidence. But it is evidence about these implementations, access paths, persistence settings, and workload—not a universal product multiplier.

## What the methodology does well

Several things make this a strong foundation:

- **Whole-stack resource accounting.** Supabase's database, API, functions, gateway, and Auth share one enforced budget. Each container is not accidentally receiving its own VPS allocation.
- **Actual correctness gates**, including concurrent likes, unique post IDs, immediate reads, identity validation, and restart persistence—not just successful HTTP statuses.
- **Canonical data and independent resets**, with full logical-data verification.
- **Scoring the steady-state hold separately** from warm-up and ramp-down.
- **Three confirmation holds**, with failed attempts retained.
- **Distinguishing generator failure from backend failure.** Correctly calling TrailBase's result a lower bound is particularly important.
- **Explicit architectural and feature exclusions.** The reports do not pretend compatibility JWTs measure native authentication or that the Supabase subset represents every default component.

Those controls, documented in [the benchmark contract](contracts/BENCHMARK.md), make the results more defensible than many published benchmarks.

## Biggest limitations and fairness concerns

### 1. A large database is not the same as a large active working set

This is probably the biggest workload limitation.

In [the load generator](bench/baas.mjs), every user:

1. Reads the same global `/feed`.
2. Selects a detail page from those newest 20 posts.
3. Sometimes likes that selected post.

New posts rotate through the feed, but **the active read set remains very small**. Most of the 500,000 seeded posts and 2 million likes are not meaningfully exercised by the timed reads.

That tests an important pattern—a hot public feed—but not broad application data access. It strongly exercises hot indexes, database buffers, serialization, and API overhead, while telling us less about storage performance and cache misses.

**“No application caching” does not mean “cold data.”** This is still a very cache-friendly workload at the database/OS level.

### 2. It is even more read-heavy than the probabilities initially suggest

The 15% like and 2% create probabilities are **per journey**, not per request.

A normal successful journey averages:

- 2 reads
- 0.15 like requests
- 0.02 create requests

So approximately **92% of requests are reads**, and **less than 1% are post creations**. Some likes can also be repeats rather than new committed rows.

That is reasonable for a browsing-heavy feed. It does not establish capacity for chat, collaborative editing, order processing, activity ingestion, or other write-intensive applications.

### 3. The persistence guarantees are not equivalent

The reports explicitly disclose:

- TrailBase: SQLite WAL with `synchronous=NORMAL`.
- Supabase: PostgreSQL with `fsync=on`, `synchronous_commit=on`, and logged tables.

Those are not equivalent power-loss durability settings. WAL/NORMAL can lose recently acknowledged transactions after power loss; PostgreSQL's synchronous commit is intended to wait for WAL flush, subject to the underlying storage honoring it.

This does **not** invalidate the current results, and the read-heavy workload means we cannot infer how much of the performance difference it explains. But it matters greatly when comparing write capacity.

For a future write benchmark, publish both:

1. **The product's documented/default operating profile.**
2. **A separately labelled profile targeting comparable acknowledged-write durability.**

Do not silently change the existing baseline or imply a normal restart test proves power-loss durability.

### 4. Equal application behavior does not imply equal implementation overhead

The measured paths differ substantially:

```text
TrailBase: HTTP → native WASM handler → platform DB API

Supabase: Envoy → Edge Runtime → Envoy → PostgREST RPC → PostgreSQL
```

Supabase also bridges the compatibility identity into a native JWT, while TrailBase verifies it directly in the handler.

That overhead is real and legitimately matters on one CPU. **It should not be subtracted away.** However, these results compare particular supported architectures—not isolated storage engines or necessarily the fastest normal way developers would build the application on each product.

Similarly, enforcing integer IDs, exact JSON property order, U+0000 support, normalized counts, and synthetic JWTs introduces different adaptation costs. Supabase's bytea/base64 body transport is one concrete example.

The fairness conclusion is:

> The baseline is reasonably fair as an equal-contract, equal-resource experiment. It is not neutral about application design.

Keep it, but eventually add a **native/idiomatic implementation track**, where each product can use appropriate IDs, native authorization, and transactionally maintained counters while preserving user-visible behavior.

### 5. Aggregate thresholds can hide a broken feature

The primary gates in [the scoring harness](scripts/benchmark.py) use aggregate latency and errors. Per-endpoint results are published, but their load-script thresholds are deliberately nonrestrictive.

Because post creation is under 1% of requests, **an implementation could theoretically fail every create request and still pass the aggregate error threshold**. Slow writes can also be diluted by fast reads.

That is a methodological gap—not evidence that either published result did this. Their endpoint reports are reassuring.

For future versions, require:

- Latency/error SLOs **per important endpoint**.
- A minimum sample count.
- Successful completion of critical user journeys.
- Separate reporting of successful new writes versus idempotent no-ops.

### 6. Closed-loop VUs are useful, but not a complete capacity measure

The think times make the journey more realistic than a tight request loop. However, when the backend slows, each VU sends requests less frequently. The workload partially throttles itself.

That measures:

> How many simulated browsing sessions can this system support under this behavior?

It does not fully measure:

> What happens when requests continue arriving at a fixed rate despite slowdown?

Keep the VU test, but add an **open-loop arrival-rate test** to expose queueing, overload, and recovery. Also compare latency at the **same offered load**, not only each service's highest passing load.

### 7. The environment is controlled, but not a literal small VPS

A CPU quota on a shared four-CPU host is not identical to a dedicated one-vCPU machine. Multi-process stacks can also interact with quota scheduling differently from a single-process server.

The existing disclosures are good. For stronger conclusions, eventually add:

- A separate load-generator host.
- Repeated reference-backend runs between product campaigns to detect host drift.
- At least one actual target-VPS deployment.

The generator OOM is also a practical reason to revisit the runner before attempting higher ceilings.

## Recommended next tests

After completing the remaining services under the frozen baseline, prioritize these additions.

| Test | Concrete workload | Why it matters |
|---|---|---|
| **Common-load latency and saturation curves** | Run every backend at identical arrival rates, increasing through overload | Shows responsiveness at ordinary traffic, sustainable throughput, and the point where latency rises sharply |
| **Broad and personalized reads** | User-specific feeds, author histories, cursor pagination, and details sampled across the dataset; test both skewed and broadly distributed access | Reveals whether performance depends on everyone reading the same hot records |
| **Write-heavy and contention workloads** | Multiple read/write mixes; inserts, updates, deletes; many users modifying one hot object versus independent objects | Exposes transaction, locking, retry, and durable-write limits |
| **Native authentication and authorization** | Real accounts, login/refresh, authenticated reads, ownership and tenant rules, permission-denied requests | Measures the normal protected application rather than mostly anonymous reads plus custom JWT writes |
| **Long-running steady load** | Several hours below saturation, with realistic data growth | Reveals WAL/checkpoint behavior, vacuum/compaction, memory growth, worker recycling, and latency drift |
| **Burst and recovery** | Sudden traffic increases followed by normal traffic | Shows whether the service sheds load cleanly or stays stuck after the burst |
| **Resource scaling and minimum fit** | Several RAM caps and CPU allocations; record idle and loaded consumption | Answers which backend fits a genuinely constrained VPS and how much extra resources help |
| **Operational load and failure recovery** | Backup during traffic, restore, process crash, controlled storage/network failures | Measures reliability, recovery time, and operational headroom—not just healthy-state speed |

### Native auth and permissions before a general application comparison

Public reads avoid one of the most important—and potentially expensive—parts of a BaaS: deciding which records a user may access.

A realistic tenant-scoped application should include:

- “Show me only my organization's records.”
- “Allow this update only to the owner.”
- Paginated queries with permission filtering.
- Attempts to cross tenant boundaries.

Verify both performance **and isolation under load**. A fast query that leaks another tenant's data is not a successful query.

### Realtime and file storage where relevant

Realtime is currently excluded, but it is a major reason developers choose some of these products.

Measure:

- Concurrent subscriptions.
- Write-to-client delivery p50/p95/p99.
- Fan-out to many subscribers.
- Missed or duplicate events.
- Reconnection storms.
- CPU/RAM per connection.

Report unsupported capabilities separately rather than inventing an equivalent score.

For media-heavy applications, apply the same idea to file storage: upload/download performance, concurrent transfers, access checks, and their effect on API traffic.

### Backup and restore—not just restart

For someone hosting on a constrained VPS, these are fundamental questions:

- Can a usable backup be made while serving traffic?
- How much latency and disk I/O does that add?
- How long does restoration take?
- How much free disk space is needed?
- Does the restored application include identities, permissions, and files?

A backup is not proven until a restore is verified.

## Additional comparison metrics

The repository already collects useful resource evidence. Make the following first-class comparison outputs:

- **Successful requests and committed mutations per second**, not just attempted requests.
- **Per-endpoint and complete-action latency**, including connection establishment where applicable—not only the current `http_req_duration` score.
- **Fraction of requests meeting a deadline**, with errors counted as unsuccessful.
- **Idle RAM, aggregate peak RAM including cache, CPU time per successful operation, and disk growth.**
- **Overload recovery time** and the amount of work rejected or queued.
- **State reconciliation after load:** do acknowledged creates exist, and do sampled like counts match stored relationships?

The last point matters because [the load-response validator](bench/baas-contract.mjs) validates response structure and some semantics, but a plausible-looking response is not proof that all state remained correct throughout sustained load.

Also, five-minute holds produce relatively few create samples for the lower-capacity systems. Endpoint tail estimates need longer tests or dedicated scenarios before they support strong conclusions.

## Presenting the final comparison

Avoid one overall “best BaaS” ranking. Publish a small scorecard:

1. **Warm public-feed capacity** — the existing baseline.
2. **Protected/personalized application performance.**
3. **Durable write and contention capacity.**
4. **Minimum footprint and resource efficiency.**
5. **Sustained stability and recovery.**
6. **Realtime/storage capability and performance**, where supported.

Include a reproducible configuration and clearly distinguish the constrained API subset from the feature set a developer actually plans to run.

Finally, the raw metric streams and source overlays currently lack a public download location, as [the artifact policy](results/README.md) explains. That does not invalidate the measurements, but publishing checksum-verifiable bundles would materially improve independent auditability.

## Bottom line

**Finish the current campaign unchanged.** It is a useful, defensible baseline. The most valuable next additions are **same-load latency curves, broad/personalized reads, native authorization, write-heavy durability tests, and long-running resource/recovery tests**. Those would move this from “a carefully measured feed benchmark” toward answering “which backend should I trust for my application on a small VPS?”

## Reviewed result references

- [TrailBase confirmed lower bound](results/trailbase/vps16-linux-amd64/CONFIRMED_LOWER_BOUND.md)
- [TrailBase confirmation endpoint metrics](results/trailbase/vps16-linux-amd64/endpoint-confirmations.md)
- [Supabase confirmed capacity](results/supabase/vps16-linux-amd64/CONFIRMED_CAPACITY.md)
- [Supabase confirmation endpoint metrics](results/supabase/vps16-linux-amd64/endpoint-confirmations.md)
