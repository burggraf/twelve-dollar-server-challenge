# Tested software and VPS slice

This is **untimed partial correctness evidence, not a capacity result**. Convex release `precompiled-2026-10-06-a3538c6`, upstream `a3538c6d212948f20726868e41d155d2534cd130`, native AMD64 image `sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`, SDK/CLI **1.46.0**, bundled Node **22.22.2**; `/version` remains literally `unknown`. Official PostgreSQL persistence: **17.11-bookworm / Debian 17.11-1.pgdg12+2**, AMD64 image `sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`. Untimed tools use Node **22.20.0**.

Serving is one shared-host aggregate **1 vCPU / 4 GiB (4,294,967,296 bytes) / zero swap**, split backend including bundled Node executor **3 GiB (3,221,225,472 bytes)** and PostgreSQL **1 GiB (1,073,741,824 bytes)**. The two child one-core ceilings do not grant two aggregate cores. Separate untimed tools/controller each have **2 vCPUs / 4 GiB (4,294,967,296 bytes) / zero swap** ceilings. Eventual separate runner: **k6 1.3.0 / 2 vCPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, `k6-2cpu-8g-v3`; no Convex k6 run yet. Host is designated `claudius.azabab.com`, not historical Contabo or the Mac. These are quota slices, not dedicated VPSes or measured $12/month offerings; price/region unknown.

## Meaningful missing-native-mutation reds, then real writes

Seven actual native-site write test methods first produced **six assertion failures** before implementation: genuine authenticated creates returned sanitized500 instead of201, private allocation/reset primitives were absent, while anonymous-denial probes passed. Full native canonical verification afterward confirmed unchanged canonical application rows. Complete failures/source are preserved in the preceding auth/input checkpoint.

Added supported private `internalMutationGeneric` functions:

- **Create:** indexed author existence, persistent native allocation row, lossless signed64 increment/bound, same-transaction sequence patch and public-ID collision check, native insert with exact UTC millisecond timestamp. A collision throws after the patch so the native transaction must roll back the allocation; actual collision proof is a later gate, not inferred here.
- **Like:** indexed post/user existence, indexed `(user_id, post_id)` absence/read and native insert in one native serializable/OCC transaction. Competing mutations use native conflict handling; no application counter, lock service, cache or underlying SQL driver.
- **HTTP:** compact ordered original-contract JSON. Creation uses the signed username in its response; later reads join stored `users.username`. Like fields are ordered `liked,already_liked,post_id`, first201/repeat200. IDs are validated decimal strings internally and exact decimal integer interpolation on the wire, never unsafe JavaScript Number conversion.

Native limits, budgets, schema/index declarations, images and dependencies were not increased or replaced. Logical application uniqueness/relations are **not physical SQL FK/UNIQUE declarations**. Native query-result cache remains zero; ordinary native database/index/module caches stay enabled.

## Fresh actual native positive gate

The seven-method write suite passed, including:

1. Private empty probe/reset and canonical allocation precondition.
2. Actual create/store/read roundtrip of **Unicode, an embedded NUL and emoji**, exact timestamp and ordered post keys. Deliberately different signed creation username versus subsequent stored-user read author.
3. **32 concurrent same-user likes:** exactly one201 and31repeat200, exact boolean/body semantics, actual subsequent like_count1; another signed subject then produced201 and actual count2.
4. **32 concurrent creates:** unique contiguous allocated IDs and actual feed ordering by stored timestamp then numeric identity.
5. Valid signed but nonexistent user → sanitized500, allocation unchanged, subsequent valid creation consumed exactly the next ID. This proves this error does not consume an ID, not yet rollback after an issued sequence patch.
6. ECMAScript whitespace trimming with an accepted500-codepoint emoji body, valid-auth invalid-ID400 and absent signed64 post404.
7. Anonymous calls to create/like/private cleanup rejected.

The write suite took **1.579 seconds total**; this is not a latency percentile or capacity measurement. It was followed by **35 current auth/input/read/health/clock/cache/canonical/converter/budget/config regression checks**, all passing. The resulting42selected checks are **not the inherited42-test compatibility suite**, which is still a separate pending gate; counts overlap earlier checkpoints.

A private admin-only test utility removed only this attempt's marked contiguous posts above500000 and their likes, after verifying namespace/range/sequence and a bounded document count; unexpected rows/ranges cause refusal rather than blanket reseeding. It restored the allocation metadata. Then an independent full native read reproduced **50,000 users / 500,000 posts / 2,016,005 likes**, full logical SHA-256 **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`**, logical relations/keys/order, metadata and native largest seeded count583. Canonical suite duration **154.877 seconds**, not an HTTP percentile. This cleanup is application-probe-only; no platform/auth/native environment/credentials were deleted or reseeded.

The next actual stored-edge installation test was then run before its fixture implementation and failed meaningfully because its private native primitive was missing. That failure is preserved separately; no edge rows were installed during this checkpoint.

## Continuity, pressure and selected-source provenance

Both native servers remained healthy, same container/image identities and actual PIDs/start times/restart counters. Existing private/platform fingerprints, persistent services and original port4000 listener were preserved. No host swap-out increase, target OOM or serving restart occurred. There was no increase to native timeout/read/write limits.

Parent configured allowance remained **4,294,967,296 bytes**. Observed parent lifetime peak **3,444,871,168 bytes**, final current usage **3,426,258,944 bytes**. Hierarchical `memory.events.max` **524,865 → 535,258**; `oom`, `oom_kill`, `oom_group_kill` remained0. Complete profiles retain raw reclaim/refault/pressure histories and previous child peaks/overshoot evidence; this is not pressure-free operation or future load fit. Controller memory is not serving memory; child peaks are not simultaneous totals.

The complete logs/driver/profiles/native canonical manifest/setup red have original and safe-derivative SHA-256/size provenance. Retention screened **seven actual private candidates across both SQLite/PostgreSQL attempts**, including the new compatibility secret, plus JWT-shaped values and HTTP query strings. Originals stay unchanged/private on the VPS. **29 exact selected source files** were preserved before subsequent fixture/feed changes; this is not a complete SDK/compiler/generated/runtime reproduction freeze.

## Remaining gates

Actual stored wide IDs and maximum allocation/collision rollback, newer orphan/deletion-hole feed continuation, cleanup ownership negative controls, acknowledged-write clean-process restart persistence, full inherited/shared/native/security/harness correctness, complete frozen reproduction, actual runner reserve/headroom and bounded capacity search remain later proof. Successful ordinary writes here do not prove provider power-loss durability, native signup/login/session throughput, a measured $12 server, a maximum capacity, or Convex completion. The original SQLite failed configuration remains separate and unchanged.
