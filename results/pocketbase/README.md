# PocketBase results

## Tested software and VPS slice

**PocketBase v0.40.5 / Go 1.27.2 / SQLite 3.53.4 / modernc.org/sqlite v1.60.1**, native Linux AMD64. [Immutable upstream/builder/runtime/build references](vps16-linux-amd64/CONFIRMED_LOWER_BOUND.md#tested-software-and-vps-slice).

**Entire serving stack: 1 vCPU quota / 4 GiB (4,294,967,296 bytes) / no swap. Separate k6 1.3.0 runner: 2 vCPU / 8 GiB (8,589,934,592 bytes) / no swap**, `k6-2cpu-8g-v3`. Quota-limited shared-host slice on `azabab.com`, not a dedicated VPS or measured $12/month offering.

## Verified result

**Final owner acceptance (2026-10-16):** retain the existing10,000-VU confirmed lower bound and close further boundary search. [Supplemental closure report](vps16-linux-amd64/SUPPLEMENTAL_STUDIES_CLOSED.md) and [structured observations](vps16-linux-amd64/supplemental-studies-closed.json) preserve all14 further holds/25 physical full attempts overall, mixed11,250 results and the incomplete seven-of-twelve post-update study stopped on fwupd continuity. No higher score or resolved250-VU boundary; the owner explicitly relaxed that completion requirement. Convex-plan work follows only audited publication and remote verification. The paragraph/bundles below describe the original completed cohort, not newly certified post-update confirmations.

**10,000-VU confirmed lower bound**: three additional independent full holds, **949,739 requests / 900 scored seconds**, zero request/schema errors. Not an exact maximum or 250-VU-resolved boundary. Valid 11,250/12,500-VU probe failures and invalid 15,000-RAM/20,000-OOM generator attempts remain separate.

- [Final report](vps16-linux-amd64/CONFIRMED_LOWER_BOUND.md)
- [Structured result](vps16-linux-amd64/confirmed-lower-bound.json)
- [Per-endpoint confirmation metrics](vps16-linux-amd64/endpoint-confirmations.md)
- [Original raw/source/resource replay](vps16-linux-amd64/setup-evidence/retained-attempt-review.json)
- [Native implementation/profile](../../services/pocketbase/README.md)

All 12 original bundles (11 full attempts and one unscored smoke) retained and checksum-verified locally/VPS. Bulk raw gzip/source archives are excluded from new Git commits under [the existing artifact policy](../README.md); no public external raw download URL is established. Owned target stopped, all volumes/private inputs/evidence retained. Compatibility JWTs do not measure native Auth throughput; normal restart is not power-loss durability. Full caveats and exact evidence are in the report.
