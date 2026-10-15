# PocketBase — owner-requested checkpoint

## Tested software and VPS slice

- **PocketBase v0.40.5**, upstream `6f370ea741f33adf889eef02e3c1b884a47aa522`; **Go 1.27.2**, **SQLite 3.53.4 / modernc.org/sqlite v1.60.1**. Immutable builder/runtime/executable/image references are retained in the [attempt manifest](20261015T142603330350Z-standard-2500vu-k6-2cpu-8g-v3/manifest.json).
- **Entire serving stack: 1 vCPU quota / 4 GiB RAM (4,294,967,296 bytes) / no swap.**
- **Separate runner: k6 1.3.0 / 2 vCPU quota / 8 GiB RAM (8,589,934,592 bytes) / no swap**, `k6-2cpu-8g-v3`.
- Native AMD64 quota-limited **shared-host slice** on `azabab.com`, not a dedicated VPS or measured $12/month offering.

## Paused, not completed

At the owner's request before local shutdown, the campaign stopped at a completed-attempt boundary at **2026-10-15T14:36:01Z**. The coordinator verified no owned PocketBase project containers remain running. Data volumes, private runtime inputs, build caches and all evidence remain retained. The campaign's exit130/KeyboardInterrupt is the intentional pause, not a failed target measurement.

- Full frozen-input native correctness/storage/restart gate passed and was reviewed.
- Unscored 1,000-VU calibration passed; original checksum/source/raw-quantile/resource replay was verified.
- One full **2,500-VU probe passed**: **79,304 requests / 300 seconds = 264.3467 requests/s**; p50/p95/p99 **0.47487 / 13.11920795 / 45.28261443 ms**, maximum **108.57681 ms**.
- The complete 2,500-VU raw/source bundle is retained locally and on the VPS. Its original checksums were verified on both copies. Full independent raw/endpoint/host/privacy review of this probe remains pending.
- **No confirmed capacity or maximum is established.** Search and three independent confirmations remain incomplete. Do not pool this probe into a fabricated final score.

The original 26 persistent service identities and original port4000 listener PID/start/executable were rechecked and remained unchanged. The post-pause snapshot additionally lists `fwupd.service`; no causal attribution is made, and no unrelated service was stopped by the pause coordinator.

## Resume requirements

Do not resume automatically. Preserve [the original paused campaign](setup-evidence/owner-paused-original-campaign.json), [pause checkpoint](setup-evidence/owner-requested-pause.json), raw per-run files and original checksums. The common search CLI starts new history; it is not an automatic resume API. Before another search, preserve the paused cohort separately, revalidate frozen source/runtime/schema/image/token/host/correctness inputs and review retained evidence. Any executable/test/profile change requires a fresh full correctness gate. Do not rotate keys or replace native volumes. Convex and later services remain unauthorized.

Implementation/report work is still uncommitted locally; no PocketBase completion publication is claimed. Private continuation details are in `.state/pocketbase/current-progress.md`.
