# Tested software and VPS slice

This is **untimed partial correctness evidence, not a capacity result**. Convex `precompiled-2026-10-06-a3538c6`, upstream `a3538c6d212948f20726868e41d155d2534cd130`, native AMD64 image `sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`, SDK/CLI **1.46.0**, bundled Node **22.22.2**; `/version` is literally `unknown`. Official PostgreSQL **17.11-bookworm / Debian17.11-1.pgdg12+2**, AMD64 image `sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`. Untimed tools Node **22.20.0**.

The serving stack shares one aggregate **1 vCPU / 4 GiB (4,294,967,296 bytes) / zero swap**: backend including its bundled Node executor **3 GiB (3,221,225,472 bytes)**, PostgreSQL **1 GiB (1,073,741,824 bytes)**. Child one-core ceilings do not grant two aggregate cores. Separate untimed tools/controller each have **2 vCPUs / 4 GiB (4,294,967,296 bytes) / zero swap** ceilings. Eventual separate runner: **k6 1.3.0 / 2 vCPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, `k6-2cpu-8g-v3`; no Convex k6 run yet. All product execution was on designated `claudius.azabab.com`, not the Mac or historical Contabo. These are shared-host quota slices, not dedicated or measured $12/month VPSes; price/region unknown.

## Actual stored-edge red and native root cause

After the previously retained missing-installer red, an admin-only fixture installed one real wide-ID user and25 real posts: one wide post and24 newer posts whose referenced author does not exist. The five-method gate produced **two passing methods and three failures**:

- Actual stored **9007199254740993** identity, exact Unicode/NUL/emoji body, native detail lookup and genuine signed wide-subject like passed.
- Feed over24 newer missing-author join holes returned **500**, not the required20 valid joined posts.
- Maximum-allocation/exhaustion and collision rollback tests failed because their private boundary preparation primitive was still absent. These are separate observed reds, not evidence that those invariants already held.

Exact-owned cleanup restored all canonical application rows and allocation. Three fixture ownership guards, health, canonical verification, budget and configuration checks then passed. The initial edge gate and30 exact selected sources are preserved, not replaced by the later green version.

Ordinary backend access logs and the private native query response did **not** explain the feed failure: the latter was the intentionally redacted `Server Error`. A guarded fresh diagnostic reproduced that same native failure and removed exactly its25 posts and one user. The first diagnostic driver failed its phase-name assertion before fixture/query operations; it is retained separately. The first native CLI history attempt rejected `--json-logs`; its complete usage showed the installed option is `--jsonl`. A second bounded history capture retained the actual matching native execution, request ID `e0b596a8d1cbdeae`:

> This query or mutation function ran multiple paginated queries. Convex only supports a single paginated query in each function.
> at async handler (../convex/native.js:53:17)

That event recorded **40 read documents /13,824 database read bytes**, uncached, no writes. This confirms the platform single-paginated-query restriction, **not a measured read-budget exhaustion or OOM**. The complete100-event history is preserved with privacy provenance, not reduced to this excerpt.

## Minimal native feed fix and fresh stored-edge positives

Replaced repeated pagination inside `native:feed` with **one supported native indexed async iterator**, descending by stored timestamp/public ID. Projections use bounded20-document batches; the function stops after20 valid joined posts. All reads/author joins/actual like counts remain within the same native query transaction. No application-side SQL, extra server, response/query-result/JWT cache, precomputed like count, schema/index addition, or native read/write/time/resource limit increase.

The five stored-edge tests then passed:

1. Exact real native fixture installation: one wide user/25 posts.
2. Actual stored ID **9007199254740993**, exact Unicode/NUL/emoji read and authenticated native like by that same wide subject.
3. Feed crosses all24 newer missing-author rows and returns the **exact wide post plus19 independently captured canonical feed posts**, including actual count1. Orphan detail is404, matching the required inner join.
4. Actual HTTP creation allocates **9223372036854775807** exactly, unrounded. The next valid create returns sanitized500 without advancing the native allocation.
5. A private, shape/ownership/sequence-guarded fixture transition positions allocation immediately below the already stored wide ID. A real create patches the sequence, detects the real public-ID collision and fails500; the native transaction rolls back that patch and leaves the original wide body intact.

The boundary utility permits only two explicit fixture transitions and refuses unexpected ownership/state. Cleanup is admin-only and verifies namespace, complete row shapes, user identity, allowed like pair, bounded25/26-post counts and known allocation states before deleting only those fixtures and restoring500000. It does not reset platform/native environment/Auth/settings/credentials or unrelated data. Logical native uniqueness/relationships are not physical SQL FK/UNIQUE declarations.

## Complete selected regression and canonical restoration

Fresh gate: **write7 + ownership guards3 + stored edges5 +35 current auth/input/read/health/clock/cache/canonical/converter/budget/config checks**, all passed. This is **50 selected checks**, not the original inherited42-check suite or a full runtime reproduction freeze. Write tests again exercised32 concurrent creates and32 same-user likes; stored-edge suite duration **0.395s** is a suite duration, not an HTTP percentile/capacity statistic.

After exact-owned cleanup, independent actual native paginated reads reproduced **50,000 users /500,000 posts /2,016,005 likes**, logical relations/keys/order, native metadata, largest seeded count583 and full logical SHA-256 **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`**. Canonical suite duration **158.405s**, not a serving latency percentile.

Both native container/image identities and actual PIDs/start times/restart counters remained unchanged; private/platform fingerprints, persistent service identities and original port4000 listener were preserved. No target OOM or host swap-out increase. Parent configured allowance remained **4,294,967,296 bytes**, observed lifetime peak **3,444,871,168 bytes**, final current **3,430,264,832 bytes**. Hierarchical `memory.events.max` **545,657→557,110**; `oom`, `oom_kill`, `oom_group_kill` stayed0. Raw profiles preserve substantial reclaim/refault/pressure and historical child overshoot evidence. These are not pressure-free operation or future load-fit claims; child peaks are not simultaneous totals.

Originals remain unchanged/private on the VPS. Public derivatives retain original/derivative SHA-256, sizes and redaction provenance; retention screened **seven actual private candidates across both SQLite/PostgreSQL variants**, JWT-shaped values and HTTP query strings. Both red and green stages preserve30 exact selected source files each; these are not complete SDK/compiler/generated/runtime freezes.

## Still incomplete at this checkpoint

No Convex VU/RPS/p95/p99 result exists. The original inherited42 checks, full shared suite, general benchmark application-only reset, acknowledged-write clean-stack restart persistence, final current frozen correctness/harness/reproduction, actual runner headroom and bounded capacity campaign remain later gates. Synthetic JWTs do not measure native signup/login/session throughput; clean-process restart would not establish power-loss durability. The failed SQLite configuration stays separate. Convex is not complete and this checkpoint does not advance the campaign to Nhost.
