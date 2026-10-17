# Tested software and VPS slice

## Nhost packaged GraphQL + measured HTTP adapter

Serving path: **k6 → measured thin HTTP adapter → Nhost's packaged Hasura GraphQL → tracked native SQL functions/transactions → PostgreSQL**. This is not Nhost Cloud Functions, the development Functions simulator, or a managed-cloud-equivalence claim.

Selection follows official self-host source commit `26cb0f1b2ff3094b36cd984204a714357c9182c5`. CLI1.52 is the source-release pin, **not a whole-stack version**. Exact native AMD64 manifests are in `versions.json`.

| Serving component | Selected software | Child ceiling |
|---|---|---|
| GraphQL | `nhost/graphql-engine:v2.46.0-ce` | 2 GiB |
| PostgreSQL | `postgres:16-bookworm`, actual16.15 | 1 GiB |
| Auth | `nhost/auth:0.40.2`, actual Go1.24.4 executable | 512 MiB |
| HTTP adapter | Node22.22.2 production HTTP runtime | 512 MiB |

All four share **one1CPU/4GiB/no-swap kernel parent**, `tdsbaasnhostvps16.slice`; this is not4GiB per component. The separate native k61.3.0 runner is **2CPU/8GiB/no-swap**, `k6-2cpu-8g-v3`. Untimed tools are separately limited and outside serving. `compose.benchmark.yaml` gives k6 only read-only benchmark code/JWT fixtures and writable output: no signing keys, private service state or Docker socket.

The designated shared AMD64 VPS has4CPUs,16,770,064,384bytes RAM, Ubuntu24.04.5/kernel6.8.0-147/Docker29.9.1 and no swap. **Region/price are unknown; this is not a price-verified dedicated $12 VPS.** Background work, storage/page caches and provider thermals prevent dedicated-machine equivalence.

## Trust and scope

- Adapter inputs contain no DB URL/password, admin secret or database driver. It validates compatibility JWTs on every write, derives a fresh restricted60s native Hasura identity, maps supported operations and serializes exact common responses. Caller admin/Hasura headers are not forwarded.
- SQL uses native transactions, unique idempotent likes, request-time counts and bytea bodies. No replica, precomputed counters, response/result cache or adapter JWT-verification cache. Native schema/query-plan caches are distinct.
- `schema.sql` is application-only. `metadata-operations.json` records the exact supported untimed tracking/permission operations, including hidden session arguments. Existing Auth/platform/probe schemas are preserved. The empty return-shape table never caches application results.
- Native Auth remains measured, but synthetic compatibility identities are not native signup/login/session throughput. Storage/MinIO, dashboard, Mailhog, development Functions and other unused platform components are excluded; this is a disclosed API-serving subset.
- No serving pool/thread/query/retry tuning. Console/dev/internal-error exposure, telemetry and function-permission inference are disabled. Core services expose no host ports; only the adapter publishes loopback14000.

## Evidence and remaining gates

Native proofs include19 adapter/helper/shared unit checks,6 actual GraphQL and7 actual HTTP small-fixture integration tests, concurrent committed creates/immediate reads, exactly-once duplicate likes, signed identity isolation and exact signed64/BOM/NUL/Unicode behavior. Historical originals and private dumps remain retained.

**The full canonical import is now proved:**50,000users,500,000posts,2,016,005likes; actual stored logical SHA-256 `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`; next post500001; native Auth/probe/catalog preserved. Canonical-input validation accounts for generator likes grouped by post with random user order. Every reset keeps a complete native-private pre-reset dump and verifies stored rows, not a copied manifest. Ordinary VACUUM ANALYZE is untimed maintenance, not a cache.

A follow-on driver initially asserted the wrong feed envelope; its failure is retained, not attributed to the product. A new read-only serving phase verified persisted canonical rows/hash after PG restart, all four healthy components, exact parent/child/process cgroups and the unchanged `{"posts":[...]}` response. Observed parent memory1,245,560,832bytes, no OOM/restarts. Raw memory.events includes max2261, not all-zero events; do not hide reclamation/child-pressure observations or infer capacity from one sample.

**Shutdown caveat:** stock GraphQL PID1 is dash with a graphql-engine child; even90s `docker stop` ends137(nonOOM). Stock Go Auth exits2 while PG is healthy. Adapter/PG exit0, all processes stop, but this is **not clean full-stack exit**. Do not call Auth2 a proven panic or invent a signal workaround. An actual acknowledged HTTP-write restart test is required; it certifies logical restart persistence, not power-loss survival.

Full unchanged42-check/golden, shared/native/metadata/dependency/restart gates and current-source freeze must pass before any load. Short25/100VU smokes are unscored. Capacity requires the unchanged30/120/60/300/30s protocol, strict latency/error/schema gates, complete actual runner/serving/host evidence, bounded slots and independent confirmations. Runner OOM/saturation/memory pressure, missing monitoring and increased host swap-outs invalidate attempts rather than establish a target bracket. All failures consume declared slots and remain retained.

## Native-only controls

These controls are deliberately bound to the approved existing owned workspace/project, source baseline and exact retained IDs/configuration. They are **not portable automatic adoption/installation scripts**. Fresh-host reproduction requires independently provisioned private inputs and requalification; use the source/config/image pins and recorded source overlay, not demonstration defaults.

In `/opt/twelve-dollar-baas-nhost-16g/src` on the designated native host:

- `bash services/nhost/run.sh qualify --name <exclusive-name>` runs canonical/full contract/native checks, actual unavailable-storage responses, acknowledged writes across a real process restart, canonical reset and exact-current freeze. It refuses an existing frozen proof; preserve/classify it before requalification.
- `benchmark --vus N --smoke` owns a fresh exclusive claim/start/offline reset/load/stop phase; do not separately start the stack first. Before any lifecycle action it fsyncs an immutable physical reservation. The immutable base policy permits24full attempts and4smokes, including failures/invalids across revisions. A separately SHA-bound explicit owner amendment (interview54c01181-5530-4b51-97ff-199460cb3cca) permits6smokes total for fresh qualification after an untimed log-capture repair; all old slots remain consumed and the full cap stays24. No automatic extension, refill or unfinished-slot adoption. Current-source25/100VU smokes must pass before full search.
- `benchmark --campaign-step` replays only immutable observations from the exact frozen qualification through the unchanged shared search and performs at most **one** new full attempt per finite native job. Repeat only after reviewing the completed prior job; invalid measurements pause the campaign, not establish a target bracket. The fixed search starts2500, doubles to a20,000fixture ceiling, refines250/25, and requires three independent confirmations. Ceiling passes establish at most a confirmed lower bound, not a maximum. Never pool changed hosts/profiles/freezes.
- `down` stops every remaining exact-owned role despite earlier errors, captures complete lifetime logs with a bounded120s per-role reader, and only cancels the independent45min timer after terminal proof. The old10s reader failed on accumulated GraphQL logs; original failures remain retained and are not retroactively promoted. A failed claim/start/run retains originals and consumes its reserved slot; inspect it rather than blindly relaunching.
- Native strict manager-journal/host/service guards retain failed originals and positively classify completed nonresident oneshots without named-unit exceptions. **The historical Convex-only fwupd approval does not authorize an Nhost waiver.**

Keep private env/JWTs/dumps on the native host under ignored state/evidence paths. Never publish resolved Compose, raw credential-bearing inspections or unscreened/decompressed archives. Use the native actual-value/signature privacy gate before retrieval. No local Mac product execution, unrelated-service administration, secret rotation, global Docker cleanup or automatic retry. This work does not authorize commit/push/publication.
