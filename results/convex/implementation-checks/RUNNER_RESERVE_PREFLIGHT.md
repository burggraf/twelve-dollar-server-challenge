# Tested software and VPS slice

Convex **precompiled-2026-10-06-a3538c6 /SDK1.46.0**, upstream **`a3538c6d212948f20726868e41d155d2534cd130`**, native AMD64 image **`sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`**; bundled Node22.22.2/tools Node22.20.0; backend `/version` literally`unknown`. Official PostgreSQL **17.11-bookworm /Debian17.11-1.pgdg12+2**, native AMD64 image **`sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`**.

Entire serving **1 vCPU /4 GiB (4,294,967,296 bytes) /zero swap**, backend/executor **3 GiB (3,221,225,472 bytes)** plus PostgreSQL **1 GiB (1,073,741,824 bytes)** under one aggregate parent. Separate runner **k6 1.3.0 /2 vCPUs /8 GiB (8,589,934,592 bytes) /zero swap**, `k6-2cpu-8g-v3`. Untimed controller separately2CPU/4GiB/zero swap. Native `claudius.azabab.com`; quota-limited shared-host slices, not dedicated/measured $12/month offerings; price/region unknown.

**Scope: real pre-load software/resource/headroom checks, not a workload/calibration/capacity result. Clean SIGINT shutdown remains FAILED139 under explicit owner exception.**

After the [full frozen correctness gate](FULL_FROZEN_CORRECTNESS.md) passed, its full current source/runtime/schema/image/token/log attestation and original healthy target epochs were revalidated. An exclusive completed runner-version probe used the actual separate Compose load profile, without invoking any k6 script or HTTP workload.

Actual version output, preserved unmodified:

```text
k6 v1.3.0+dirty (commit/5870e99ae8-dirty, go1.25.1, linux/amd64)
```

Actual selected native manifest **`sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656`**, platformLinuxAMD64, configured NanoCPUs2,000,000,000, Memory/MemorySwap8,589,934,592 bytes (zero extra swap). The exact completed owned probe container was removed only after project/service/version/manifest/limits checks; neither serving container was touched. A fast version command cannot supply a live runner kernel-cgroup sample: **actual kernel limits must additionally be observed during calibration and every scored hold**, and missing/mismatched evidence invalidates the measurement.

Physical host **four CPUs**, total RAM **16,770,072,576 bytes**, no swap. Actual `MemAvailable` **14,691,288 KiB /15,043,878,912 bytes**, exceeding required8-GiB runner plus1-GiB reserve beyond the already-running serving stack. Static CPU budget1serving+2runner+1reserve fitsfour, whereas a four-core serving tier cannot fit and remains prohibited. Two raw `vmstat` samples, load/pressure/CPU/memory/swap/I/O counters retained: second sample96% idle,2% user/2% system/0% wait/steal, no runnable/blocked processes, loadavg0.15/0.58/0.45. These are momentary shared-host observations, not dedicated CPU reservations or guarantees of future headroom. Before each actual attempt the adapter rechecks available memory, physical CPU/total allocation, swap, exact targets and complete frozen evidence; hold monitoring detects runner saturation/swap/incomplete evidence.

Both serving processes remained healthy/same container/image/PID/start under unchanged kernel budgets; parent OOM counters stayed unchanged. No unrelated workload or original port4000 listener was stopped/changed, and no resource/cache/native-limit adjustment was made.

The first subsequent calibration launcher had an argument typo **`--vus1000`**, rejected by argparse with exit2 **before attempt creation/reset/k6**. Its complete failure/cleanup log and provenance are retained; this is **not an attempted load measurement or target/runner capacity failure**. The corrected launch used the same code/freeze/budgets and explicit **`--vus=1000`**, a separate bounded unit/distinct log, with only exact-owned runner/reset-tool watchdog cleanup and no serving revival. Calibration outcome belongs in its own run evidence; this preflight does not claim it passed.

Original logs/profile/raw counters and version-probe state retain SHA-256/size/redaction provenance, screened against allseven actual private values, JWT shapes and HTTP query strings before retrieval/publication. No token/key/DSN/native database files were retrieved. Actual serving-path capacity still requires valid calibration, full common holds/three independent confirmations, complete raw/source/resource/privacy audit and truthful publication. Prior acknowledged crash recovery is not clean-shutdown or provider power-loss proof.
