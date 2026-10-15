# BaaS Benchmark Campaign

This fork is being retooled to benchmark the same feed application using each product's supported APIs, one service at a time:

**TrailBase → Supabase → PocketBase → Convex → Nhost → Directus → Appwrite → Neon (if feasible).**

Owner priority amendment (2026-10-15): Supabase is next, before PocketBase.

See **[the master plan and progress checklists](MASTER_PLAN.md)** for the application contract, Docker/runner design, resource tiers, correctness gates, benchmark protocol, and per-service publication requirements.

All future BaaS product tests use the owner-designated **16-GiB native AMD64 VPS**, preserving its existing services. The common **standard** budget is **1 CPU / 4 GiB for the entire serving stack**, with a separate **2 CPU / 8 GiB / no-swap** k6 runner (`k6-2cpu-8g-v3`). Required database/API/functions/adapters/caches/ingress share the aggregate serving budget. Headroom is checked before reset; no global settings or unrelated-service changes are permitted. See [current host setup](services/trailbase/VPS16.md) and [the frozen contract](contracts/BENCHMARK.md).

Earlier OrbStack and 8-GiB VPS attempts, including 1-CPU/2-GiB serving results, remain immutable historical tracks. The latter passed 5,000 VUs then hit a **runner** OOM at 10,000; this was not a TrailBase maximum. All correctness/scored holds restart on the new host/tier/profile. No cross-host/tier confirmations are pooled, and none of these results is an original dedicated $12-cloud-VM score. See [current evidence/status](results/trailbase/README.md).

**TrailBase completed three independent 15,000-VU confirmation holds**, at 1,585.29–1,586.82 requests/s with zero request/schema errors. This is a **confirmed lower bound, not a maximum**: the 20,000-VU attempt hit the generator's 8-GiB limit. Read the [verified report](results/trailbase/vps16-linux-amd64/CONFIRMED_LOWER_BOUND.md), including tail outliers, resource review, compatibility-auth scope and all raw evidence. The owner authorized committing/pushing this outcome and moving directly to Supabase. Each subsequent service needs a reproducible report before progression.

After isolated setup and verified native images per the host guide:

```bash
export BENCHMARK_PROJECT=baas-trailbase-vps16 BENCHMARK_RUNNER_PROFILE=k6-2cpu-8g-v3
export TIER=standard TRAILBASE_PORT=14000
bash services/trailbase/run.sh test
bash services/trailbase/run.sh bench --smoke --vus 5000 # unscored pipeline calibration
# Only after calibration review:
bash services/trailbase/run.sh bench --campaign --max-vus 20000 --max-attempts 12
```

See [TrailBase setup and architecture](services/trailbase/README.md) for requirements, resource limits, auth scope, safe lifecycle operations, result locations, and caveats. Supabase is the next active implementation; PocketBase remains queued. The same compatibility-auth scope, host and aggregate resource budgets apply unless explicitly amended.

---

## Upstream reference: The $12 Server Challenge

The original challenge documentation below, along with `SPEC.md`, the seed, tests, and existing submission, is retained as the workload reference. Its SQLite-only rules, submission workflow, and original scoring procedure are historical upstream rules, not the cross-product benchmark policy; see the master plan for planned changes.

How many users can one **$12/month server** (1 vCPU, 2 GB RAM) handle? 

I benchmarked 8 languages with basic unoptimized code using language defaults. https://www.youtube.com/watch?v=sQXFhh_PiG4

**Now it's your turn: implement the same API in any language and framework, make it as fast as you can on
SQLite, and I'll benchmark it on the same VM.**

## What's here

| | |
|---|---|
| [`SPEC.md`](SPEC.md) | The API you implement: 5 endpoints, exact JSON and errors |
| [`schema.sql`](schema.sql) | The SQLite schema (fixed) |
| [`seed/make-seed.sh`](seed/make-seed.sh) | Builds the seed database `seed/feed.db` (50k users, 500k posts, 2M likes) and `seed/tokens.json` |
| [`test/test.sh`](test/test.sh) | The test suite (42 checks). Your server must pass all of them |
| [`test/run.sh`](test/run.sh) | Builds your submission, starts it on a fresh database copy and runs the tests (what CI runs) |
| [`bench/load.js`](bench/load.js) | The k6 load test we score with (you can test this yourself before submission) |
| [`bench/nginx.conf`](bench/nginx.conf) | The Nginx config in front of your server, if you want Nginx (rule 9) |

## Quick start

```bash
bash seed/make-seed.sh                          # needs node >= 18 and sqlite3; about a minute
mkdir submissions/rust-axum-yourname            # your code + install.sh, build.sh, start.sh, README.md
bash test/run.sh submissions/rust-axum-yourname # needs curl, jq, openssl
k6 run -e VUS=1000 bench/load.js                # optional: load test your server yourself
```

## Rules

**The stack**
1. Any language, framework, runtime and SQLite driver/binding. Any number of processes or threads.
2. **The database is SQLite**: the file at `$SQLITE_PATH`, used in-process. No other database, cache
   server, or external service (no Postgres, Redis, Memcached).
3. The schema and data are fixed. Don't add or change tables, columns, indexes or triggers. Any SQL
   you like against the schema as given.

**Correctness**
4. Pass `test/test.sh` 100%, with the exact bytes it expects.
5. **No caching across requests.** Every request reads its data from SQLite while it is being served:
   no response caches, query-result caches, in-memory copies of tables, or remembered JWT verifications
   (verify every token's signature). SQLite's own page cache and `mmap` are fine. That's the database.
   Reusing prepared statements is fine too: they cache the query plan, not the data.
6. **Writes are durable before you respond.** A 201 means the row is committed. Use WAL with
   `synchronous=NORMAL` or stronger: no `synchronous=OFF`, no `journal_mode=OFF/MEMORY`, no in-memory database.
   Batching several requests' writes into one transaction (group commit) is allowed if each response waits for
   its commit.
7. No hard-coded responses, no detecting the load test, nothing that only works because it's a benchmark.

**VM Specs and Info**
8. It runs on Ubuntu 24.04 x86_64 on a DigitalOcean Basic droplet: 1 vCPU, 2 GB RAM, no swap. You share
   the CPU and RAM with the OS (and Nginx, if you use it). If you run out of memory, you lose.
9. **Nginx is optional.** Either run behind our Nginx ([`bench/nginx.conf`](bench/nginx.conf), as in the video)
   on `127.0.0.1:3000`, or serve the internet directly on `0.0.0.0:80`. Going direct saves the CPU Nginx uses
   (14–20% in the video), but then your server has to handle up to ~15,000 open keep-alive connections by
   itself. Say which one you chose in your README.
10. It is built from source on the box with your `install.sh` and `build.sh`. Pin your dependency versions,
   and don't ship prebuilt binaries. It must come up healthy within 60 seconds of `start.sh`.
11. Nothing on the box gets tuned for you: no kernel parameters, and no pinning of CPU or other processes.
    Settings inside your own process (GC, thread counts, allocator, pragmas allowed by rule 6) are fair game.

## Submitting

Open a pull request that adds one folder, `submissions/<language>-<framework>-<github-username>/`, containing:

| File | What it does |
|---|---|
| `install.sh` | Run once as root on a clean Ubuntu 24.04: installs your toolchain/runtime (apt, official tarballs) |
| `build.sh` | Builds your app as a normal user (may download pinned dependencies) |
| `start.sh` | Runs the server **in the foreground**, configured only by the env vars in SPEC.md |
| `README.md` | Language, framework, driver and versions; **Nginx or direct**; the optimizations you made and why |
| your code | Source only: don't commit build output (`bin/`, `target/`, `node_modules/`, …). Add a `.gitignore` |

For example, the three scripts for a Go server:

```bash
# install.sh: runs once as root on a clean Ubuntu 24.04
set -euo pipefail
apt-get update && apt-get install -y build-essential curl
curl -fsSL https://go.dev/dl/go1.27.1.linux-amd64.tar.gz | tar -C /usr/local -xz

# build.sh: runs as a normal user
set -euo pipefail
cd "$(dirname "$0")" && /usr/local/go/bin/go build -o bin/server .

# start.sh: runs the server in the foreground
exec "$(dirname "$0")/bin/server"
```

CI runs `install.sh` and `test/run.sh` on every pull request, and it must be green. Don't touch files outside your folder.
By submitting, you license your code under the repo's [MIT license](LICENSE).

## Scoring

We benchmark each passing submission exactly like the languages video: on the same droplet, with k6 on a
separate machine. Every implementation in the video ran behind Nginx.

1. **Warm-up**: 1,000 users for 2 minutes (not scored).
2. **Find the limit**: `bench/load.js` starting at 2,500 users, doubling until a run fails, then narrowing
   down to within 250 users.
3. **Confirm it**: one 5-minute hold at that number. If it fails, step down 250 users and try again.

**Your score is the most users that pass a 5-minute hold** with p95 under 500 ms, p99 under 1 s and under 1% errors.

**After your pull request is merged**, it waits for the next benchmark batch. I run merged submissions in batches,
not one at a time, on no fixed schedule, and share the results once a batch is done.
