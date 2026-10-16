# Tested software and VPS slice

Convex **precompiled-2026-10-06-a3538c6**, upstream `a3538c6d212948f20726868e41d155d2534cd130`, SDK/CLI1.46.0; native AMD64 image `sha256:818a924cf137594517cb7b7ee9246d7af02248c990162d2531857cf51dfeb7f4`, bundled Node22.22.2/tools22.20.0, `/version` literally`unknown`. PostgreSQL17.11-bookworm /Debian17.11-1.pgdg12+2, native image `sha256:66aafa11cf15800a3c94763f7e11d1e7b2e37e5e84bc4ce027cb6e1e4bfaf4df`.

Entire serving **1 vCPU /4 GiB (4,294,967,296 bytes) /zero swap**, backend/executor3GiB (3,221,225,472 bytes) +PG1GiB (1,073,741,824 bytes), one shared parent. Separate k61.3.0 **2 vCPUs /8 GiB (8,589,934,592 bytes) /zero swap**, `k6-2cpu-8g-v3`, native manifest `sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656`. Actual `claudius.azabab.com` shared-host slices; price/region unknown, not dedicated/measured $12/month equivalence.

**Owner-accepted BLOCKED /UNSCORED.** First full2,500-VU attempt caused backend child3-GiB OOM/exit137; no candidate or independent confirmations. Original clean-SIGINT139 remains separatelyfailed. All50,812hold requests failed; any diagnostic RPS is not successful/confirmed throughput. Neither the earlier1000VUfailed nor100VUpassing unscored calibration is a capacity bound.

- [Final blocked report](BLOCKED_UNSCORED.md)
- [Structured outcome](blocked-unscored.json)
- [Stage evidence, raw/derivative provenance and checksum sets](../implementation-checks/)
- [Full frozen functional/harness gate](../implementation-checks/FULL_FROZEN_CORRECTNESS.md)
- [Unscored calibration replay](../implementation-checks/UNSCORED_CALIBRATIONS.md)

Backend stayed stopped after OOM; only ownedPG was subsequently cleanly stopped under explicit owner authority. All volumes/private inputs/original raw samples/source/SDK archives retained; no recovery/reset/post-OOM durability proof. Unrelated pre-existing flapping-service continuity guard failed and is not hidden. The owner authorized Nhost feasibility after verified Convex publication. Complete source/SDK archives remain private pending distribution/license/privacy handling; no fresh-deployment/download claim.
