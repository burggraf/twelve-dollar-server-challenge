# TrailBase feed benchmark

Native **TrailBase v0.34.6** (`8359b240cc4ae1d229738385bf42f8f40d5d59af`), native Linux ARM64 image, with a Rust WASM component compiled using Rust 1.91.1 and the published `trailbase-wasm` SDK **0.6.1**. The release source's 0.7.0 SDK is not published on crates.io; 0.6.1's guest/transaction interfaces were verified against the pinned server by the full integration suite. All Rust transitive dependencies are locked.

Timed path:

```text
k6 container -> TrailBase HTTP -> Rust WASM custom handler
             -> trailbase_wasm::db::{query, Transaction} -> TrailBase-owned SQLite
```

There is **no separate application server, SQLite driver inside the app, response cache, counter table, or external proxy**. Reads use the documented guest query API; writes use the native transaction resource and explicitly commit before constructing a success response. Likes rely on a composite primary key and a single transaction for existence/insert/duplicate detection. Post IDs are allocated by SQLite's integer primary key, not a racy application-side max+1.

A separately labelled **native Linux AMD64 VPS track** is now owner-approved. The pinned multi-arch TrailBase index retains the original ARM64 child and adds the AMD64 child of the same release. See [VPS setup, isolation, build limits, and Linux monitoring](VPS.md); the full VPS correctness gate must pass before load. No Mac/VPS measurements are pooled.

## Current primary host and budget

The owner now directs **all future product tests** to the 16-GiB native AMD64 host. Use **`TIER=standard` (1 CPU/4 GiB aggregate serving)** and **`BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3` (2 CPU/8 GiB k6)**, with no container swap. Preserve existing services and the port-4000 listener; publish benchmark HTTP only on loopback 14000. Follow [the current isolated host guide](VPS16.md) and [current evidence](../../results/trailbase/vps16-linux-amd64/README.md). Correctness and all scored holds restart; the previous 2-GiB serving and other-host results are not pooled.

The historical default `small`/runner-v2 settings remain available for reproducing earlier artifacts; **they are not the new primary baseline**. Explicitly export the documented host environment. The four-CPU `large` tier is distinct from standard and cannot fit the CPU reserve on this four-CPU host alongside the separate two-CPU runner.

## Historical OrbStack reproduction

Prerequisites: Docker/Compose via OrbStack on ARM64 macOS, Python 3, and internet access for pinned image/crate/package downloads. Host Node/Rust/SQLite/k6 are not required; Docker builds run the compiler/tests and the reusable tool container supplies seed/correctness dependencies. Build and test commands may take a few minutes on a cold cache.

```bash
bash services/trailbase/run.sh build
bash services/trailbase/run.sh test
# Tests automatically reset to canonical data, verify correctness and restart persistence.
curl -fsS http://127.0.0.1:4000/health

# Unscored, short pipeline smoke; performs a fresh reset first.
caffeinate -i bash services/trailbase/run.sh bench --smoke --vus 25

# One capacity attempt, not a maximum score (about 9 minutes plus reset).
caffeinate -i bash services/trailbase/run.sh bench --vus 2500

# Bounded search and three confirmation holds; can take roughly 1–2 hours.
caffeinate -i bash services/trailbase/run.sh bench --campaign --max-vus 20000 --max-attempts 12

# Larger common tier: only after an owner-approved VM headroom review.
# Current ~8-GiB VM is too small for 4-GiB service + 4-GiB k6 + 1-GiB OS reserve.
# Correctness alone does not establish benchmark headroom.
TIER=large bash services/trailbase/run.sh test
TIER=large caffeinate -i bash services/trailbase/run.sh bench --campaign

bash services/trailbase/run.sh down
```

Full correctness output: `.state/trailbase/correctness.log`. The success attestation records the serving source hash, image, tested tier, harness hash, and log checksum. The benchmark refuses stale/missing attestations or mismatched image/resource limits. New generated results appear under `results/trailbase/<deployment-track>/` (historical runs remain at their original paths); `.state` is private and ignored. See [the benchmark contract](../../contracts/BENCHMARK.md) for timing, rejection rules, retention, and hardware caveats. Campaign progress is also written to `.state/trailbase/campaign.json`; an invalid run pauses the campaign rather than being treated as a platform capacity limit.

Do not build, edit benchmark code, reset/test the same service, run another benchmark, or change power/OrbStack settings during a capacity campaign. The owner approved command-scoped `caffeinate -i` for idle-sleep prevention; it does not change the permanent power profile or prevent manual sleep/lid closure. Inspect the host if results show swap, thermal warnings, contention, or load-generator saturation. The runner does not change macOS settings or stop unrelated workloads. The benchmark orchestrator's campaign lock prevents concurrent invocations of itself; lifecycle operations must still be kept sequential.

## Dataset, migration, reset

TrailBase applies `migrations/U1791970000__feed.sql` through its normal migration mechanism. Application columns, foreign keys, constraints, and indexes match `schema.sql`; the tables additionally use `STRICT`, which the native Record API requires. Platform system tables/keys remain separate and untouched.

`run.sh seed` produces canonical TSVs and load tokens inside `.state/seed`. `run.sh reset` stops **only this service**, imports the TSVs into application tables in its named volume, verifies the complete logical hash/counts/foreign keys, analyzes indexes, checkpoints WAL, restarts, and waits for storage health. It never replaces `main.db` with an unrelated SQLite file. No direct bulk-import work is timed as serving traffic.

The canonical data contains **50,000 users, 500,000 posts, 2,016,005 likes**, with content hash `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`. Repeat resets must reproduce it exactly. Test writes and benchmark writes are disposable. `down` stops the named Compose stack/network but preserves its benchmark-only volume for reproducibility; no global Docker cleanup/prune is performed.

## Auth, privacy, API scope

The default signing key is the upstream **public fixture**, suitable only for synthetic benchmark data. To use another local key, supply `JWT_SECRET` through your shell's environment before the first build/initialization; do not put its value in a command argument, report, or commit. Once initialized, the wrapper refuses a changed key rather than silently mismatching the token pool. The secret lives under a host directory with mode 0700; its single-file Docker secret mount is readable by service UID 1000. The WASM sandbox has read-only access only to a runtime directory containing that key and the process start time, not the whole host filesystem. Neither key nor tokens enter build context or result archives.

JWTs are HS256-verified on every authenticated request inside the WASM handler; required expiry/payload/algorithm rules and auth-before-ID ordering follow the compatibility contract. Subject/username come from the validated token. This is a **custom compatibility auth route**, not a measurement of native TrailBase login, password hashing, session refresh, or RLS throughput. No admin credential or native server key is passed to k6.

A native read-only Record API at `/api/records/v1/benchmark_posts/<id>` is included for integration proof and permission tests, but not used by the scored journey. Native admin APIs/UI are isolated on a nonpublished loopback listener. Password authentication is disabled. Default platform logging/storage remains enabled and counts against the serving cgroup; bootstrap logs can contain generated credentials, so do not upload `docker compose logs` or private volumes.

## Correctness and durability evidence

`run.sh test` runs the inherited **42 exact-contract checks**, six extra black-box tests (32-way likes/posts, immediate reads, identity forgery, strict JWT payload/expiry, Unicode boundaries), native Record API read/write-denial checks, a real storage failure/recovery test, and an actual container restart with an acknowledged post/like read back afterward. It also runs the seed privacy regression, pure workload-validation tests, and fail-closed score/resource-gate tests. Rust contract tests run in the Docker build. CI uses native ARM64 correctness only, never scored capacity runs.

Health probes execute `SELECT 1 FROM users LIMIT 1` via TrailBase, which is stronger than a process-only/static health signal and detects missing application storage. Health failure exposes a sanitized error. The stronger app-table probe is an explicit adaptation from the upstream `SELECT 1` example.

Pinned TrailBase initializes SQLite with WAL, `synchronous=NORMAL`, and foreign keys enabled ([release source](https://github.com/trailbaseio/trailbase/blob/8359b240cc4ae1d229738385bf42f8f40d5d59af/crates/extension/src/lib.rs)). The tests demonstrate normal restart persistence, **not sudden power-loss durability**. The original WAL/NORMAL power-loss caveat remains; do not describe it as equivalent to every managed backend's fsync/replication guarantee.

## Result interpretation

Current primary standard = **1 CPU/4 GiB** serving with **2 CPU/8 GiB** runner v3 on the new native AMD64 host. Full correctness/calibration/search and independent confirmations must be repeated; see the current host guide.

For historical OrbStack/8-GiB VPS artifacts only: small = 1 CPU/2 GiB for the entire service; large = 4 CPU/4 GiB. k6 used the owner-approved `k6-2cpu-4g-v2` profile: separate 2 CPU/4 GiB/no-swap limits, sharing OrbStack and the physical Mac. The original 2-GiB runner passed one 2,500-VU hold but OOM-killed at 5,000 VUs; those immutable historical attempts are not pooled with v2 measurements. The preflight requires at least 1 GiB VM/OS headroom in addition to both container budgets, so the current VM permits small but rejects large before reset. Actual enforced limits, images, source, host/VM versions, and raw samples are retained per run. Local scores are not directly comparable with the upstream x86 cloud-VM challenge, managed services, or emulation. A successful smoke or a single 5-minute hold is not a maximum-capacity result. A candidate requires search, three independent passing holds, resource/evidence review, and explicit acceptance before moving on.
