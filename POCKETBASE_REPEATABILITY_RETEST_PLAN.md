# Tested software and VPS slice

**APPROVED FOR IMPLEMENTATION, VERIFICATION AND CONDITIONAL EXECUTION** in owner interview `9c8b8369-0955-4a93-ad2f-a99c7b2dbcc6`: the fixed protocol and **12 further attempts / +9 cap extension / 19 cumulative supplemental / 30 cumulative physical** are approved, with load only after all post-update gates pass. The owner confirmed that the reboot/security updates did not concern the benchmark application.

The earlier planning-only interview `51559c66-762b-4018-9a50-1ec160adee2d` is superseded only by this explicit approval. The original 20,493-byte review draft is preserved with SHA-256 `ae82fa8f045465443ead7550e1768558e15f84586ed41b07ce4bdc055428a2a0`. This amendment does not consume slots, erase past outcomes, authorize product tuning or authorize publication/force-push.

**New prospective host context:** the owner separately authorized stopping/disabling `dmarie.service`; that action was verified at 2026-10-16T12:19:59Z, with restoration instructions in `/opt/dmarie/BENCHMARK-PAUSE.md`. The owner-applied updates/reboot changed kernel/Docker/background state. Historical listener PID811/startticks691 equality remains false; the post-update listener PID812/startticks759 at the same executable path is a distinct, recorded prospective identity to preserve throughout this study. Do not restart that unrelated listener or rewrite its older evidence. All future rows require fresh host/correctness/resource attestations and the quiet-window gate. PocketBase was already stopped by the host shutdown; its controlled correctness lifecycle is authorized, not a Convex revival.

## Frozen serving configuration to preserve

| Component | Last verified input; reverify before any future execution |
|---|---|
| PocketBase | v0.40.5, upstream `6f370ea741f33adf889eef02e3c1b884a47aa522` |
| Native toolchain/storage | Go 1.27.2; modernc.org/sqlite v1.60.1 / SQLite 3.53.4; native linux/amd64, CGO disabled |
| Serving image | `sha256:489cba19771795f5378e440c7f6d83d81f8460bf31e673aff8a392b080a9b131` |
| Serving executable SHA-256 | `0e31cb09904df2e7cfb8a8e8d2fe18a577a1a2e4e55b92e7b937f1ee157123f8` |
| Application SHA-256 | `985a44c5d53a0167ecaba053d7e07bc5fb63c02ff47902f074dd631367abe801` |
| Entire serving allocation | **1 CPU / 4 GiB (4,294,967,296 bytes) / zero swap**, aggregate kernel enforcement, not per component |
| Separate load generator | **k6 1.3.0 / 2 CPUs / 8 GiB (8,589,934,592 bytes) / zero swap**, profile `k6-2cpu-8g-v3`; actual reported build `v1.3.0+dirty`, commit `5870e99ae8-dirty`, Go 1.25.1, linux/amd64 |
| Native k6 manifest | `sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656` |
| Post-update host | `claudius.azabab.com`, accessed through `root@azabab.com`; Ubuntu 24.04.5 / kernel 6.8.0-147-generic / Docker 29.9.1 / 4 CPUs / 16,770,064,384 bytes / zero swap; read-only capture, not yet a scored result |

This is a quota-limited slice on a **shared host**, not a dedicated or measured $12/month VPS. Region and monthly price are unknown. All product checks and load must run on that native host, never the Mac or the historical host. Untimed heavy tools and controller units remain capped at 2 CPUs / 4 GiB / no swap. No builds, heavy audits or transfers overlap scored holds; record the ongoing lightweight controller/monitor overhead instead of claiming it is absent. Require the existing CPU/memory reserve checks, including at least one CPU and one GiB beyond serving plus runner, and actual available headroom.

## 1. Question and rationale

**Prospective question:** under the unchanged implementation and workload, does a fixed **11,000-VU candidate** consistently pass while its **11,250-VU adjacent point** consistently fails, with a repeated **10,000-VU control** remaining sound?

Choose this one pair before observing any new results. The candidate is one 250-VU step below the already observed unstable point; it is **not an established passing capacity**. A fixed pair is smaller and easier to audit than another adaptive search. There is no fallback to 10,750, upward expansion, or second pair within this proposal.

The seven supplemental holds already retained were:

| Supplemental slot | VUs | Recorded SLO verdict |
|---:|---:|---|
| 1 | 10,000 | PASS |
| 2 | 11,250 | PASS; contradicted the original failing upper anchor |
| 3 | 12,250 | FAIL |
| 4 | 11,750 | FAIL |
| 5 | 11,500 | FAIL |
| 6 | 11,250 | PASS |
| 7 | 11,250 | FAIL; contradicted candidate confirmation |

Fresh 11,250-VU p99 values were approximately **941 / 885 / 1,832 ms**; the strict limit is below 1,000 ms. Original raw/resource replays reproduced these verdicts without runner-invalid or serving-OOM classification. That does not pass the separate host-continuity issue below. The causal explanation of the performance variation remains unestablished.

No historical or supplemental hold is reused as a new confirmation. The historical **10,000-VU confirmed lower bound** and all mixed 11,250-VU evidence remain unchanged. The new study can remain inconclusive; it is not a promise to produce a resolved score.

## 2. Mandatory host-continuity gate — currently unresolved

The known unrelated `dmarie.service` had **57–58 scheduled restarts in every one of the seven scored holds**, including passing and failing holds. Two endpoint comparisons also failed. Matching endpoints did not prove continuous stability. These findings neither establish causality nor justify ignoring that service.

**Do not launch this study with that unresolved continuity condition and then claim a clean comparison.** Before any execution authorization can be used:

1. The owner must address the unrelated service through its owner/operator or a **separately authorized** investigation/remediation. This proposal authorizes no unrelated service stop, disable, restart, exclusion, configuration edit, or credential inspection. A quiet window alone is not proof of a permanent fix.
2. Record any operator action and host-background change as a **new prospective study context**, without changing the historical guards or pooling old holds into the new confirmations. Do not rebaseline away unexplained changes or the original port-4000 listener identity.
3. As a proposed additional preflight, obtain read-only evidence for an immediately preceding **10-minute window** with no unexplained persistent-service lifecycle churn, plus current service identities and the existing ownership/headroom checks. Query recorded history; do not keep the agent in a sleep/poll loop. If evidence is unavailable or churn continues, stay blocked and consume no load slots.
4. Preserve identity snapshots and read-only numeric service-event evidence across each new attempt, not only at campaign endpoints. An unexplained persistent-service addition/removal/restart, a failed existing identity guard, or missing continuity evidence pauses the study. Preserve any affected attempt; never turn a failed guard green or use it to establish the candidate/failing boundary.

The 10-minute preflight and per-attempt event gate are **proposed prospective safeguards**, not retroactive reclassification of earlier holds. They do not prove absence of contention, a quiet dedicated host, or causal isolation. Continue recording raw whole-host CPU/steal/I/O/pressure data and disclose shared-host limitations. Only the already established SSH-session manager exception remains; do not add a `dmarie.service` exception.

### Owner-approved completed-oneshot clarification

Owner interview `f81b2fc4-35f2-4a51-925b-aa303ea7b68d` approved a **uniform transient-job classification for completed oneshot units with verified no resident processes**, with all event counts disclosed and every persistent-service guard unchanged. This is not a named SSH or dmarie exception. Require completed unit state, zero main/control PIDs, no pending job and positive systemd/kernel evidence of no resident processes; missing or contradictory evidence fails closed. A oneshot with resident processes or incomplete/pending execution remains watched.

The earlier preflight remains stopped/failed: its complete 2026-10-16T12:48:49.012726Z–12:58:49.012726Z window counted three `user-runtime-dir@0.service` events as persistent because `RemainAfterExit=yes`. The subsequent read-only unit check showed oneshot / active-exited / MainPID0. Preserve that result, original classifier/source/catalog and raw journal; use separately frozen revised orchestration and exclusive new preflight outputs. The clarification changes no workload, SLO, resource or attempt budget and authorizes no service-management action or publication.

## 3. Fixed schedule: twelve full attempts, no replacements

Four rounds, three full attempts per round. The control is always first; candidate and adjacent point alternate order, so each occupies each non-control position twice. This balances those positions, **not all possible time/cache/carry-over effects**. There is no randomness or statistical independence guarantee from the ordering.

| Round | First | Second | Third |
|---:|---:|---:|---:|
| 1 | 10,000 control | 11,000 candidate | 11,250 adjacent |
| 2 | 10,000 control | 11,250 adjacent | 11,000 candidate |
| 3 | 10,000 control | 11,000 candidate | 11,250 adjacent |
| 4 | 10,000 control | 11,250 adjacent | 11,000 candidate |

Machine-readable description of the same proposed schedule:

```json
[
  {"round": 1, "vus": [10000, 11000, 11250]},
  {"round": 2, "vus": [10000, 11250, 11000]},
  {"round": 3, "vus": [10000, 11000, 11250]},
  {"round": 4, "vus": [10000, 11250, 11000]}
]
```

For the candidate, round 1 is characterization; rounds 2–4 are **three additional independent executions**, all required to pass. Four adjacent executions provide at least the required three fresh adjacent failures if all four fail. For repeatability classification, retain the fourth adjacent result too: a 3-FAIL/1-PASS mixture is **mixed**, not a stable failing boundary. The control's four outcomes are reported and scored under the same gates, not discarded as unscored warm-up.

Each full attempt retains the unchanged phases: **30s initial ramp / 120s warm hold at 1,000 VUs / 60s target ramp / 300s scored hold / 30s drain**, with existing graceful allowances and 10s request timeout. No smoke substitutes, longer timeouts, added client retries, seeded journey changes, cache flushes, special cool-downs, or asymmetric preconditioning. Use ordinary native caches and the original per-attempt canonical app reset; warm-up writes carry into that attempt's hold only. Record reset duration, preceding target and actual start/end times.

## 4. Explicit proposed budget amendment

| Accounting item | Full physical attempt slots |
|---|---:|
| Historical campaign, retained | 11 |
| Supplemental already consumed, retained | 7 |
| Total already consumed | **18** |
| Previously approved supplemental cap | 10 |
| Unused under that previous cap | 3 |
| Now-approved further fixed study | **12** |
| Approved cap extension beyond those three unused slots | **9** |
| Now-approved cumulative supplemental cap | **19 = 7 + 12** |
| Now-approved cumulative all-history physical ceiling | **30 = 11 + 19** |

This asks for **twelve further attempts, not nine further attempts**: three from the previously unused allowance plus nine new slots. The owner has now explicitly approved this amendment, so the controlling caps are **19 supplemental / 30 historical-plus-supplemental physical attempts**. Before this amendment the caps were 10 / 21. At approval, 7 supplemental / 18 overall were consumed; no new rows may launch until the fresh gates pass.

Every started/partial/invalid/aborted full attempt consumes a slot and is retained. Persist intent before side effects; account conservatively for an interrupted pending attempt before any later decision. An invalid or interrupted attempt stops the study, with **no automatic replacement**, implicit resume, budget reset or reallocation of unrun rows. Unstarted rows consume no physical attempts and do not establish evidence.

Twelve 300s holds mean **3,600s / 60 minutes of scored windows**. Nominal full phases total **6,480s / 108 minutes**, before reset, validation, startup and audit overhead. Recent attempt cadence suggests roughly **2–2.5 hours** for the load sequence, plus untimed correctness/setup. Propose a **3-hour bounded campaign unit**, which is a safety ceiling, not permission to add attempts. Timeout retains partial evidence and pauses; no automatic restart.

## 5. What changes, and what does not

**Two orchestration amendments are explicitly approved:** the cap increase above, and permission to finish the fixed matrix after **valid SLO pass/fail variation at the candidate/adjacent levels**. The previous confirmation controller stopped on the first contradiction. This study instead records variation at its predeclared points; it does not accept a failure or choose a different passing subset. Control/invalid/runtime/continuity stops remain mandatory; the old controllers and their stopped phases remain immutable.

Everything else stays fixed:

- `SPEC.md` and unchanged `test/test.sh` dominate newer checks. No modifications to schema, goldens, seed algorithm, legacy submissions, native API path, query/transaction semantics, indexes or serving code.
- Canonical 50,000 users / 500,000 posts / 2,016,005 likes; logical SHA-256 `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`. Bound native reset to known app state and preserve all platform/Auth/settings/credential/auxiliary state.
- Synthetic preissued HS256 JWT compatibility, not native Auth signup/login/session throughput. No fixture/key rotation implicit in this plan; if validity/fingerprints no longer match, stop for review.
- p95 **<500ms**, p99 **<1,000ms**, request errors **<1%**, malformed successful responses **0**, using unrounded metrics for requests **started in the scored hold**. Missing samples/contradictory collection are not target failures. Never pool requests across holds to hide a failing hold.
- Original kernel-enforced serving/runner budgets and invalidation: runner OOM; failed/missing/incomplete monitoring; three consecutive scored-hold CPU samples >=180% of one core; scored-hold RAM >=90% of runner allocation; increased host swap-outs. Preserve exact existing verdicts and raw counters.
- Serving OOM, unexpected exit/restart/outage or source/input drift stops the study with the actual target outcome retained, not relabeled a generator failure or discarded outlier. Expected reset/restart happens only through the original owned per-attempt lifecycle, before the timed process-identity epoch.
- WAL / synchronous NORMAL and original SQLite settings stay unchanged. No app response/query-result/JWT-verification cache, precomputed counts, replicas, unsupported SQL-serving shortcut, resource increase, native-limit change, dependency install, pull or rebuild.
- Preserve all unrelated services/volumes/private inputs and port 4000. Retain the failed historical comparison to original PID811 / startticks691; preserve the approved prospective PID812 / startticks759 / `/opt/trailbase-server/bin/trail` identity after the owner reboot. Do not perform global Docker/package/plugin/firewall changes, pruning or cache flushing.

## 6. Predeclared classification and stop rules

Classify a complete four-hold series as **all-pass**, **all-fail**, or **mixed**, using each original per-hold gate. These are finite observed outcomes, not proof of a deterministic capacity or of a high probability of future SLO compliance. Four runs cannot establish a high-reliability guarantee; individual requests are not independent repeatability trials.

| Complete, fully reviewed result | Permitted conclusion |
|---|---|
| All four controls PASS; candidate all-pass; adjacent all-fail; every other gate accepted | An observed **11,000-VU confirmed candidate with a 250-VU adjacent failing point for this prospective study**, pending publication/owner acceptance; not a mathematical maximum. Report all older 11,250-VU passes/failures and changed background context prominently. |
| Candidate all-pass; adjacent mixed | Repeated passing evidence at 11,000, but **no clean resolved adjacent failing boundary**. Do not label mixed as fail or erase its passes. |
| Candidate and adjacent all-pass | No failing boundary; no upward expansion. Report passing points/lower-bound evidence only. |
| Candidate mixed or all-fail | No candidate confirmation; no step-down to another target. Publish the observations, not a selected subset. |
| Candidate fails while adjacent passes | Preserve the non-monotonic observation; no monotonic interpolation or maximum claim. |

**Stop immediately, preserving the slot/evidence**, for any failed 10,000-VU control; invalid runner/monitor measurement; failed continuity/ownership/headroom/source/correctness gate; runtime failure; unexpected state; or budget/time ceiling. A control SLO failure is a real observed failure at that control, not automatically proof of host causality. It makes this study inconclusive and does not authorize lowering the control.

Otherwise finish only the fixed candidate/adjacent rows despite valid SLO variation. Do not stop early and call three favorable candidate results sufficient; do not replace an unfavorable first result with later passing runs. After the final row, the controller must stop at **complete_pending_human_review**, never automatically advance to Convex. Missing rows leave an incomplete study, not a resolved result.

## 7. Authorized implementation and verification requirements

The approval above permits this work. Each completed step still needs fresh evidence; the plan itself proves no pass. Implementation must:

1. Use a separate external helper and new exclusive ledger/evidence paths, outside the original frozen PocketBase source tree. Preserve both prior paused controllers, policies, ledgers, journals, 18 physical attempts and all archived input/checksum evidence byte-for-byte. Do **not** synchronize newer local common/Convex code over the older frozen VPS common code.
2. Write policy tests first and observe meaningful native reds. Cover exact twelve-row order/counts; all pass/fail patterns for each four-hold series; control failure; all invalid/continuity/runtime stops; no replacement/resume/expansion; pending intent before side effects; partial exceptions; immutable history; both cumulative caps; and classification of mixed/non-monotonic/incomplete observations. Run the existing supplemental policy tests unchanged too. Model review is not a substitute for these checks; no delegation is authorized.
3. Reverify the complete actual 107-entry source and 14,330-entry module inventories, compiler/runtime/tools/generated/schema/private fixture inputs and exact serving executable/image. Preserve historical correctness manifests before producing new attestations; a selected source overlay alone is insufficient. Re-run the full frozen correctness gate (previously 10 Go +42 inherited +64 Python +4 workload checks), including actual acknowledged-write/restart/next-ID proof, on the same immutable binary without a rebuild or reduced assertions. Canonically restore app state afterward.
4. Before every side effect, verify native ownership, frozen inputs, all-history slot accounting, original listener, stopped Convex containers and real resource reserve. Verify the proposed host gate before launch and each hold. Freeze the complete new controller/policy/auditor sources and test evidence before the first load row.
5. Use managed `process` readiness/exit notifications and bounded native systemd units; no shell backgrounding, polling/sleep-wait, blind retries or implicit restarts. Avoid heavy audits/transfers during timed holds. Run the unchanged native benchmark entry point for each row, with the original per-attempt reset and health/clock/resource collection.
6. After each hold, independently replay original checksums, input/runtime/source identity, all raw metric rows, request counts/status/error/schema classifications, quantiles, scenario clock, monitor completeness and kernel/resource verdicts. Retain host numeric lifecycle/pressure diagnostics without exporting unrelated messages or claiming causality. A successful controller exit is not evidence acceptance.

## 8. Privacy, publication and completion gates

Preserve original raw bytes, outliers, counters, failures and checksums. Before any retrieval/publication, scan on the native host against all three actual PocketBase private values and 20,000 issued signatures, JWT shapes, **all HTTP queries** and explicit private-path guards. Verify original/copy/screened-derivative SHA-256 and byte provenance as separate links. Do not compare redacted manifest bytes to the original hash as though they were identical. Raw native databases, keys, tokens, credentials, unrelated journals, environment/argv and private archives stay private.

Report every scheduled/started/unstarted row, all four observations per level if complete, endpoint mixes, per-hold unrounded gates, errors, latency ranges/maxima, raw/source/resource provenance, continuity failures and actual cumulative budget use. No lossy averaging, fabricated confidence, native-Auth/power-loss claim or standalone public-download/fresh-build claim. Keep code-only whitespace checks separate from preserved raw formatting diagnostics.

A future publication requires exact staged-tree/privacy/checksum audits and, if commit/push is separately authorized, ordinary non-force Git publication plus independent remote-ref verification. Planning this document is not publication authorization.

**Convex remains stopped and its retest plan unread. Nhost remains paused; Directus remains unauthorized.** A mixed, incomplete or merely repeated-lower-bound outcome does not meet the owner's current PocketBase 250-VU-resolved completion gate. Any alternative acceptance/progression needs an explicit owner decision; even a qualifying matrix still needs full evidence review, publication and acceptance before reading the actual Convex plan.

## 9. Approval record and remaining gates

1. The **fixed 10,000 / 11,000 / 11,250-VU four-round study**, stronger all-four-fail adjacent classification, control-stop rule and continuation through valid candidate/adjacent SLO variation are approved.
2. The **12 further slots / +9 cap extension / 19 cumulative supplemental / 30 cumulative all-history** limits are approved. The three unused old slots are not a separate retry reserve.
3. The owner-authorized dmarie stop/disable and owner-applied security updates/reboot are recorded changes, not retroactive continuity passes. Fresh ten-minute/per-attempt checks remain mandatory; record every unexplained difference and stop on a failed gate.
4. Implementation, untimed native verification and conditional load execution are authorized. **Do not launch load before reviewing fresh passing gates.** No further expansion, replacement, implicit resume, product/host tuning, unrelated-service action, commit/push or Convex-plan read is authorized by this amendment.
