# Tested software and VPS slice

- **Convex precompiled-2026-10-06-a3538c6**, upstream `a3538c6d212948f20726868e41d155d2534cd130`, SDK/CLI **1.46.0**, bundled Node **22.22.2**, tools Node **22.20.0**; PostgreSQL **17.11-bookworm / Debian17.11-1.pgdg12+2**. Immutable native image IDs/digests in manifest; backend `/version` literally `unknown`.
- Entire serving allocation **1 vCPU / 4 GiB (4,294,967,296 bytes) / no swap**, one aggregate parent: backend/executor **3 GiB (3,221,225,472 bytes)** plus PostgreSQL **1 GiB (1,073,741,824 bytes)**. Child CPU ceilings do not grant two cores.
- Separate runner **k6 1.3.0 / 2 vCPU / 8 GiB (8,589,934,592 bytes) / no swap**, `k6-2cpu-8g-v3`.
- Quota-limited **shared-host** slice, not dedicated or a measured $12/month VPS; price/region unknown.
- **Clean SIGINT shutdown FAILED139** after native teardown panic/fault. Explicit owner exception permits capacity; acknowledged crash recovery passed separately. Not clean lifecycle or provider power-loss proof.

## Convex standard — 100 VUs (smoke)

Outcome: **pass** — hold gates passed. One attempt, not a maximum-capacity score. Short calibration only, not scored.

- Hold requests220; throughput11.000000 requests/s.
- p50/p95/p99/max ms: 13.1452135 / 34.76025679999987 / 97.40511321000004 / 111.549268.
- Request/schema errors: 0 / 0.
- Source overlay/patch and raw complete dependency/generated inventory retained; immutable runtime/compiler/image pins inmanifest. Original full source/dependency archive staysprivate pending distribution/license/privacy handling, not falsely represented as a public download.
- Original raw samples, endpoint metrics/statuses/outliers, parent/child/host/runner counters retained; SHA256SUMS. No pooled quantiles or cost/request claim.
- Canonical full native hash restoration beforemeasurement, full frozen correctness evidence copied; no serving restart/reseed/cache flush. Compatibility JWTs are NOT nativeAuththroughput.
- Native clean-shutdown gate remains FAILED139 regardless of measured serving outcome.
