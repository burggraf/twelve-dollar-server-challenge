# Tested software and VPS slice

- **Convex:** `precompiled-2026-10-06-a3538c6`, upstream `a3538c6d212948f20726868e41d155d2534cd130`, SDK/CLI1.46.0, bundled Node22.22.2, native `/version` literal`unknown`; AMD64 backend `sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`.
- **PostgreSQL:**17.11(Debian17.11-1.pgdg12+2), AMD64 `sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`.
- **Complete serving stack:** shared aggregate parent **1vCPU/4GiB(4,294,967,296bytes)/zero swap**; backend including its bundled Node executor **3GiB(3,221,225,472bytes)**, PostgreSQL **1GiB(1,073,741,824bytes)**. Both child CPU ceilings one core; combined parent still **one**, not two. No additional application server/replica/storage driver or larger budget.
- **Separate future runner:** k6**1.3.0**, **2vCPUs/8GiB(8,589,934,592bytes)/zero swap**, profile`k6-2cpu-8g-v3`; **not run**. Untimed tools and controller each use separate2CPU/4GiB/noSwap limits.
- Native execution only on `azabab.com`, actual`claudius.azabab.com`. These are **shared-host quota slices**, not dedicated VPSes or measured$12/month offerings; price/region unknown. Ordinary native DB/index/module caches remain enabled; query-result cache disabled and actual reexecution tested. This official-PG variant is not pooled with the failed default-SQLite attempt.

## Red before implementation

The unchanged common storage-health test [failed404≠200](native-health-first-red-public.log). Separate native metrics diagnostics found **no established uptime/start/boot value**, including label-aware names/numeric-candidate extraction. No zero/module-age/worker-age clock was substituted.

A new private-action clock test [then failed meaningfully](native-health-clock-first-red-public.log): native action status`error` rather than`success`;2tests/1failure. This output was safely retained and completely reviewed before implementing `clock.js`.

## Actual native implementation

GET`/health` calls supported **ctx.runQuery(native:storageProbe)** against actual native users/posts/likes, then **ctx.runAction(clock:backendUptime)**. The private Node action uses only built-in Node APIs and stock`getconf CLK_TCK` inside the existing backend image, reading **`/proc/1/stat` and `/proc/uptime`**. Official `run_backend.sh` execs the native backend as PID1. The helper checks PID1's native-backend command name, obtains actual tick frequency rather than assuming100Hz, checks finite/safe/nonnegative clock values and returns integer elapsed seconds since the actual backend PID1 start. It reads/returns **no argv, environment, credentials or native database files**. No package, privilege, resource, read/write or native timeout setting was increased. All executor/child processes remain charged to the existing backend and aggregate serving cgroups.

The native test compares two action results to actual DockerStartedAt±3seconds, requires monotonic integer nonnegative uptime, and verifies anonymous callers cannot execute the private action. This establishes backend-process uptime, **not Node-worker/module/OS-boot uptime**. HTTP success is compact ordered `status`, `db`, `uptime_s`; query errors map to sanitized503 and clock/other errors to sanitized500. **The error branches' existence is not proof of actual backing-store-outage correctness.**

## Fresh23-check positive/regression proof

[Complete log](native-health-clock-green-public.log), [driver](native-health-clock-green-driver-public.log), [before](native-health-before-public.json), [after](native-health-after-public.json), [canonical manifest](native-health-canonical-dataset-public.json), [safe retention provenance](native-health-clock-green-retention.json).

**Passed:** native clock2; unchanged common positive health1; HTTPreads6; native private/cache2; full native canonical3; aggregate budget5; actual Compose config4. Full stored native data was independently re-read after the code change: **50,000users/500,000posts/2,016,005likes**, full logical SHA **`738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`**, exact583-like native projection, metadata/order/relationships/uniqueness intact. Full canonical suite162.740seconds; unit2min47.010s. These durations are **not request latency percentiles**. Controller31.1MiB peak is **not serving memory**.

All **22 executed selected source hashes** matched local/VPS; private inputs/platform credentials/container images/main PIDs/starts/restart counts/budgets and original persistent service/4000-listener identities stayed unchanged. Additional unrelated`dmarie.service` was observed before and absent after; no cause/ownership attribution is made and this experiment did not stop it. Parent lifetime memory peak remained**2,613,133,312bytes**, post-run current**2,434,146,304bytes**, configured limit**4,294,967,296bytes**. No serving OOM or host swap-out increase observed; substantial PostgreSQL-child memory pressure/raw overshoot caveats from the canonical checkpoint remain applicable, not erased by a passing check.

## Not complete health, compatibility or capacity

This immutable checkpoint proves the **positive storage-backed health/native backend clock path plus current read/data regression**. An actual hot-path PostgreSQL-stop/health/recovery experiment is separate; do not infer503/dependency isolation/recovery from this positive gate. Auth/strict JSON/native transactional writes/concurrency/allocation/wide signed64/Unicode/NUL/lifecycle/reset/full reproduction and correctness remain required before any k6/capacity score. No native signup/login/session-throughput, physical SQL FK/UNIQUE or provider power-loss durability claim is made. The selected source attestations are not a complete SDK/generated/runtime freeze. No Nhost progression follows.
