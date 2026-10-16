# Tested software and VPS slice

This is a **failed untimed lifecycle attempt, not a capacity result or passing persistence proof**. Convex `precompiled-2026-10-06-a3538c6`, upstream `a3538c6d212948f20726868e41d155d2534cd130`, native AMD64 image `sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`, SDK/CLI **1.46.0**, bundled Node **22.22.2**; `/version` remains literally `unknown`. Official PostgreSQL **17.11-bookworm / Debian17.11-1.pgdg12+2**, AMD64 image `sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`. Untimed tools Node **22.20.0**. The actual panic identifies Tokio **1.53.1**; that does not identify the Rust compiler version.

Serving allocation remained one aggregate **1 vCPU / 4 GiB (4,294,967,296 bytes) / zero swap**: backend/bundled executor **3 GiB (3,221,225,472 bytes)**, PostgreSQL **1 GiB (1,073,741,824 bytes)**. Child one-core ceilings do not grant two aggregate cores. Separate untimed tools/controller each: **2 vCPUs / 4 GiB (4,294,967,296 bytes) / zero swap**. Eventual separate runner: **k6 1.3.0 / 2 vCPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, `k6-2cpu-8g-v3`; **no Convex k6 run or score**. Product execution was on `claudius.azabab.com`, not the Mac/historical Contabo. These are shared-host quota slices, not dedicated/measured $12/month offerings; price/region unknown.

## Preconditions and actual acknowledged operations

The preceding unchanged original42, full shared6 and57 additional checks passed, including actual native application-only reset and full canonical hash restoration. That passing functional gate is separate from this failed lifecycle gate.

This attempt planned to acknowledge a real HTTP post/like, stop backend then PostgreSQL, start the same native containers/volumes/images, verify acknowledged data/exactly-once like/allocation, then exact-owned cleanup/full canonical verification. It did not recreate/reseed a deployment or alter budgets/native limits/images/keys.

The **before-restart test passed**: real HTTP201 created ID500001 with the owned marker body; first like201, repeat200/already_likedtrue, actual GET count1; native allocation500001/one extra post. A private manifest preserved the exact acknowledged post/timestamp/state, without JWTs/credentials. This is acknowledgement evidence, **not yet survival evidence**.

## Actual failed stop, not OOM or clean restart success

Requested the pinned stack's configured **SIGINT**, using exact-owned Docker Compose `stop --timeout30 backend`. The backend stopped rapidly but exited **139**. The guard accepted neither that exit as clean nor an automatic revival. **PostgreSQL was not stopped; after-restart assertions/cleanup/full canonical verification were not reached.**

Actual backend log sequence on2026-10-15:

- **23:47:48.108777Z:** `Received Ctrl-C signal!`
- Request draining/proxy closure, then `Database shutdown` / `Application shut down`.
- **23:47:48.116489Z:** `Server successfully shut down.`
- **23:47:48.116533Z:** `Done`.
- **23:47:48.119465Z:** isolate thread panic at `tokio-1.53.1/src/runtime/time/entry.rs:539:9`: **`A Tokio 1.x context was found, but it is being shutdown.`**
- Kernel at23:47:48: **`traps: isolate[2259704] general protection fault ... error:0`**.
- Docker finish **23:47:48.287476294Z**, **ExitCode139 / OOMKilledfalse / Runningfalse**.

The backend's success-looking shutdown message is not used to override its actual crash. Exit139 plus the matching kernel fault supports segmentation-fault classification. The logs locate the failure after application/database shutdown and show a Tokio teardown panic; they do **not** prove the exact low-level memory-safety defect or establish deterministic reproduction. No backtrace/core/native memory/argv/environment was exported. No native software patch, alternate stop signal, larger timeout/budget or silent retry was used to evade the result.

Parent `oom`, `oom_kill`, `oom_group_kill` remained0; hierarchical max582125 reflects historical pressure, not an OOM classification. The stopped backend's original container/image/start identity and data volume remain preserved. PostgreSQL remains healthy, same PID2196884/start2026-10-15T20:47:57.462350749Z; the backend is deliberately stopped. Its prior PID was2132883/start2026-10-15T19:03:26.325882195Z. Original port4000 and unrelated workloads were not stopped/restarted by this test.

## Preserved evidence and decision boundary

Complete first-attempt log/driver/before/after profiles, acknowledged-before manifest and **42 exact selected source files** were preserved before any proposed fix/recovery. A separate read-only bounded Docker/kernel/state diagnostic confirmed the failure. Originals remain unchanged/private; safe derivatives retain hashes/sizes/redaction provenance and screen **seven actual private candidates**, JWT-shaped values and HTTP query strings. Source counts are selected files, not a complete SDK/compiler/generated/runtime freeze.

GitHub's latest-release API still returned this exact October6 official release when checked after the failure. A public shutdown-related issue, [#487](https://github.com/get-convex/convex-backend/issues/487), concerns an ambiguous PostgreSQL commit/SIGABRT and is **not established as this same manual-SIGINT/139 defect or a proven fix**. No untested release/patch is presented as remediation.

An explicit owner decision is required before reviving the stopped unexpected-exit target under a newly bounded recovery plan, accepting a failed clean-shutdown gate for capacity, changing the software pin, or accepting a blocked/unscored Convex outcome and advancing. The original failed clean-lifecycle attempt must remain failed even if later crash recovery succeeds. There is no evidence here of lost acknowledged data, but equally **no completed acknowledged-write recovery/clean-stack restart proof**. Provider power-loss durability and native signup/login/session throughput remain untested. No capacity numbers or Convex completion are claimed.
