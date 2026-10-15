# Tested software and VPS slice

**Convex:** official`precompiled-2026-10-06-a3538c6`, upstream`a3538c6d212948f20726868e41d155d2534cd130`, SDK/CLI**1.46.0**, bundled Node**22.22.2**, native version endpoint literal`unknown`, AMD64 backend`sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`. **PostgreSQL17.11(Debian17.11-1.pgdg12+2)**, AMD64`sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`.

**Complete serving stack:** aggregate **1-vCPU quota/4GiB(4,294,967,296bytes)/zero swap**, parent`tdsbaasconvexpgvps16.slice`; backend including bundled Node executor **3GiB(3,221,225,472bytes)**, PostgreSQL **1GiB(1,073,741,824bytes)**. Both child CPU ceilings one core but parent combined **one**, not two. No extra server, SQL application driver, cache, limit increase or unsafe database manipulation. Ordinary native buffers/index/module caches enabled; query-result cache disabled and actual execution verified.

**Separate future runner:** **k6 1.3.0/2vCPUs/8GiB(8,589,934,592bytes)/zero swap**, `k6-2cpu-8g-v3`; **not run**. Untimed tools/controller each have separate2CPU/4GiB/noSwap limits. Only designated **azabab.com**, actual**claudius.azabab.com**: shared-host quota slices, not dedicated VPSes or measured$12/month offerings; price/region unknown. Original workloads/listener and previous product/SQLite volumes remain preserved.

## Actual fault injection, not mocked health

The accepted [positive health/clock stage](POSITIVE_STORAGE_HEALTH_AND_BACKEND_CLOCK.md) was followed by a distinct bounded actual dependency test:

1. Record actual full image/container/main-process identity, source/private/platform fingerprints, parent/child kernel limits and original persistent service/listener snapshot.
2. **Warm the exact native health query/module/clock path** while PostgreSQL is healthy. This prevents a cold-cache failure from being mistaken for proof of correct behavior with ordinary native buffers hot.
3. Gracefully stop **only the exact owned PostgreSQL** container; independently inspect its actual`State.Running=false` before requesting health. No global Docker/systemd/firewall/power/cache changes.
4. Native HTTP returned **503**, exact ordered JSON **`{"status":"degraded","db":"unreachable","error":"storage unavailable"}`**. [Probe evidence](native-dependency-down-probe-public.json) records0.013467333046719432seconds for this single observation; **not a percentile, capacity measurement or universal failure-detection bound**.
5. Preplanned ownership/image/CID-checked recovery starts the **same** PostgreSQL container without recreation/reseed/credential rotation; it refuses automatic restart of OOM targets and would start backend only if it had exited non-OOM. **Backend never exited/restarted in this attempt.**
6. Run all23 current positive/read/native-data/cache/private/budget/config regressions again. The unit would return nonzero for a failed dependency-health probe even if recovery passed; recovery cannot hide a failure.

## Fresh24-check outcome

**Passed1 actual-dependency-down check +23 recovery/current regressions**, complete [log](native-dependency-fault-recovery-public.log), [driver](native-dependency-fault-recovery-driver-public.log), [retention provenance](native-dependency-fault-recovery-retention.json). Recovery23 comprise common positive health1, native backend-clock/private2, HTTPreads6, native private/cache2, full native canonical3, budget5 and Compose config4.

Independent native pages again reproduced **50,000users/500,000posts/2,016,005likes** and exact logical SHA **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`**; row order/relationships/unique likes/native metadata/583-like projection verified. Canonical suite159.794seconds; full native unit2min48.958s. These are correctness durations, **not request latency percentiles**. Controller31.2MiB peak is not serving memory.

- Backend PID**2132883**, started**2026-10-15T19:03:26.325882195Z**, unchanged throughout.
- PostgreSQL PID**2132744→2196884**, started**2026-10-15T19:03:20.716573172Z→2026-10-15T20:47:57.462350749Z**, same native image/container/data/private inputs.
- Docker restart counts**0→0** for both: a manual clean stop/start changed the actual PostgreSQL process; Docker's automatic-restart counter did not increment. This counter alone is not persistence/restart proof.
- All **23 selected executed source hashes** matched local/VPS, before/after source/private/platform fingerprints unchanged, both actual required servers healthy after recovery, full aggregate enforcement unchanged.
- Original persistent service identities and port4000 listener unchanged; no additional unrelated persistent service in before/after snapshots. No serving OOM/host swap-out increase.

See [before](native-dependency-before-public.json), [actual stopped states](native-dependency-down-states-public.json), [warm request](native-dependency-warm-health-public.json), [after](native-dependency-after-public.json), [native stored recovery manifest](native-dependency-recovery-dataset-public.json). All public derivatives were screened against actual private values and stripped of HTTP query strings before retrieval; original/private hashes/bytes/provenance remain retained.

## Memory pressure and proof boundaries

Configured parent limit remains**4,294,967,296bytes**. Parent lifetime observed peak increased to**3,323,609,088bytes**, post-run current**3,315,154,944bytes**; neither is substituted for the configured allowance or a guarantee of future fit. Parent hierarchical`memory.events.max`**483284→493423**, `oom/oom_kill/oom_group_kill` remained**0**. This is real pressure/counter history, not erased by the child process restart. Earlier PostgreSQL child reclaim/refault/observed-peak-overshoot evidence remains separate; child lifetime counters can reset on restart and are not simultaneous totals. Exact allocation responsible for the increased parent memory was not profiled; no unsupported cause is asserted.

This proves **the tested hot-path503 behavior, clean PostgreSQL process recovery and current canonical-data/read continuity**, not full compatibility, acknowledged compatibility-write persistence, power-loss durability or a performance score. Strict auth/JSON, supported transactional writes/allocation/concurrency/unique likes, actual wide signed64/Unicode/NUL round trips, reset/full frozen SDK/generated/runtime reproduction and full inherited/current correctness are still required. No native signup/login/session throughput, physical SQL FK/UNIQUE enforcement or Nhost progression claim is made.
