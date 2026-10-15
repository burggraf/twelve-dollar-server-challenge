# Supabase — designated native AMD64 host

**Completed outcome: [2,000-VU confirmed capacity](CONFIRMED_CAPACITY.md)**, with three independent five-minute holds. [Summary](confirmed-capacity.json) · [All 11 scored attempts](campaign.json) · [Per-endpoint metrics](endpoint-confirmations.md). The 2,250-VU single-probe pass failed all three confirmation repeats and is not scored as confirmed capacity. No exact mathematical maximum or finer-than-250-VU result is claimed.

Current profile: `azabab.com`, Ubuntu 24.04.5 LTS, native x86-64, four CPUs, 16,770,072,576 bytes RAM, no host swap, Docker 29.8.1. Shared existing host; price/region unknown. Workspace `/opt/twelve-dollar-baas-supabase-16g/src`, project `baas-supabase-vps16`, loopback 14000; original listener4000 preserved.

## Serving and authentication scope

The entire five-process API-serving stack—official pinned PostgreSQL17.6, Auth2.196.0, PostgREST14.17, Edge Runtime1.76.2 and Envoy1.39.1—shares one verified **1 CPU / 4 GiB / zero-swap** kernel parent cgroup. Native selected AMD64 manifests, actual process membership and absence of unaccounted children are checked. k6 remains separately bounded to **2 CPU / 8 GiB / zero swap**.

Synthetic application users and pre-issued compatibility JWTs are retained from the common scope. Native Auth is present and budgeted but native accounts/login/session throughput are not measured. Each write verifies compatibility auth and a scoped native JWT; PostgREST verification caching is disabled. See [complete profile and source](../../../services/supabase/README.md).

## Correctness and setup evidence

The full gate covers all42 inherited exact-byte checks, six shared API/concurrency/auth/Unicode tests, five native RPC/API-key/permission/encoding tests, strict scalar JSON/JWT/body/ID units, four workload tests, seed-log privacy, original24 scoring/host and3 isolation regressions, native harness/config/import/aggregate-budget/frozen-input regressions, and storage failure/recovery plus actual five-process restart persistence.

[Final full gate log](setup-evidence/full-correctness.log), [its attestation](setup-evidence/full-correctness-manifest.json), and [service/listener continuity](setup-evidence/final-correctness-continuity.json) are retained, as are the [earlier pre-policy gate](setup-evidence/pre-policy-full-correctness.log) and its attestation. The final gate additionally ran all3 existing repository artifact-policy regressions. All26 persistent services and the original listener/start identities matched. Root `user@0.service` is separately identified as the ordinary SSH-session manager, not a general application exception.

The prototype's two exact-byte like-response key-order failures were fixed and all42 checks subsequently passed; raw red/green evidence remains in [implementation checks](../implementation-checks/). The official webhooks-before-roles bootstrap dependency and privileged offline operator role were diagnosed with retained failed attempts. The first incomplete owned data volume is preserved; current data uses the documented second volume. No resource limit or SLO was raised to repair setup.

## Calibration — not scored capacity

[Initial 1,000-VU smoke](20261015T044425811639Z-standard-1000vu-k6-2cpu-8g-v3-smoke/report.md): 2,238 hold requests,111.90 requests/s, p50/p95/p99 4.38/45.34/144.24ms, maximum243.73ms, zero request/schema errors. Full checksums/raw stream/source privacy/aggregate limits/scoring replay verified. A 20-second smoke does not establish a maximum or five-minute steady state.

After synchronizing the verification-input set with the repository's existing bulk-artifact ignore-policy tests, fresh full correctness passed. [Final-source 1,000-VU calibration](20261015T045317043850Z-standard-1000vu-k6-2cpu-8g-v3-smoke/report.md) also passed:2,194 requests/109.70 requests/s, p50/p95/p99 4.28/95.67/152.52ms, maximum329.69ms, zero errors. [Resource replay](setup-evidence/final-calibration-resource-review.json):4 hold samples, runner peak11.19% of one CPU and4.2% of8GiB, parent memory peak2,025,955,328 bytes including cache, swap-outs0→0, no serving restart or input drift. Scored inputs stayed frozen throughout all 11 attempts; bounded search, backoff and three final 2,000-VU confirmations are complete. Historical attempts remain immutable and are not pooled across changed verification inputs.

## Publication and reproducibility

All scored search/failure/confirmation attempts passed full source/image/data/runtime/schema/cgroup/host/continuity review and retain original raw measurements. Native raw-sample audit reproduced each hold's exact quantiles, request/error counts and HTTP-status distribution. The completed owned serving containers were stopped after final live-input review; [stop/volume/continuity proof](setup-evidence/completed-owned-stop-proof.json) confirms unrelated services and the original listener remain unchanged. A maximum needs a valid target-failure bracket and three independent passing holds; generator limitations yield only an accurately labelled lower bound/blocked outcome.

Raw streams and generated source overlays remain intact locally and on the VPS, with original checksums. The [current Git policy](../../README.md) excludes bulky generated files; a partial checkout cannot satisfy complete `SHA256SUMS` until those original files are restored. No external artifact-upload location is established. Keys, issued tokens, database volumes, runtime config and private bootstrap logs are excluded.
