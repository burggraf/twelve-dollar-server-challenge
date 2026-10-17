Tested software and VPS slice
=============================

# Nhost — benchmark closed

**Highest tested passing load: 3,250 VUs. Next higher tested load: 3,500 VUs, failed latency limits. Exact maximum not established.**

The 3,250-VU result is one valid historical pass, not three confirmations. Separately, three fresh qualification-v6 runs confirmed **3,000 VUs as a repeatable lower bound**. These proof generations are not pooled. The owner accepted closure: no further load, qualification, calibration or audit campaigns.

## Tested stack and limits

Measured path: k6 → thin compatibility HTTP adapter → packaged Hasura GraphQL → native SQL transactions → PostgreSQL. Native Auth is inside the serving envelope. This is a disclosed Nhost API-serving subset, not Nhost Cloud or default whole-platform equivalence.

| Component | Version | Memory ceiling |
|---|---|---:|
| PostgreSQL |16.15|1 GiB|
| Hasura GraphQL |v2.46.0-ce|2 GiB|
| Nhost Auth |0.40.2|512 MiB|
| Adapter |Node22.22.2|512 MiB|

The four components share **one kernel-enforced aggregate1CPU/4GiB/no-swap slice**. Separate native k61.3.0 runner: **2CPU/8GiB/no-swap**, profile `k6-2cpu-8g-v3`. Shared AMD64 host:4CPUs,16,770,064,384bytes RAM, Ubuntu24.04.5/kernel6.8.0-147/Docker29.9.1, no swap. Price/region are unknown: no dedicated-$12 or cost/request claim.

Compatibility JWT verification occurs on every write, followed by a fresh restricted native identity. Native signup/login/session throughput is not measured. No adapter DB driver, timed SQL bypass, response/count/JWT-verification cache, replica or development Functions simulator.

Canonical reset per attempt:50,000users/500,000posts/2,016,005likes; stored logical-row SHA256 `738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d`. Native Auth account count remains zero. Full timing:30s warmup ramp/120s warmup at1,000VUs/60s target ramp/**300s scored hold**/30s drain. VUs include think time; they are not requests/s or simultaneous in-flight requests.

## Highest passing and next failing tested points — historical v5

| Physical | VUs | Outcome | Hold requests | Hold requests/s | p95 ms | p99 ms | Hold errors |
|---|---:|---|---:|---:|---:|---:|---:|
|11|3250|PASS|101963|339.87666666666667|349.4141833999999|512.0695798000003|14|
|12|3500|FAIL latency|101200|337.3333333333333|1885.0945765499994|2031.08329081|15|

Both have independent original-sample/resource/continuity reviews. Their valid quality verdicts remain historical evidence. A pass at3,250 does not prove an exact maximum, nor do these two observations establish three-run repeatability at3,250.

## Fresh fixed3,000-VU study — v6

The predeclared study was two fresh calibrations followed by exactly three fixed3,000-VU confirmations, without replacement, target reduction, ceiling search or selection of the best three. All five independently passed.

| Physical | Role | VUs | Hold requests | Hold requests/s | p95 ms | p99 ms | Hold errors |
|---|---|---:|---:|---:|---:|---:|---:|
|14|Calibration|25|54|2.7|6.801566749999999|13.95475199999999|0|
|15|Calibration|100|230|11.5|5.037920499999999|6.639326390000001|0|
|16|Confirmation1|3000|94831|316.10333333333335|143.90276699999998|236.10424309999974|12|
|17|Confirmation2|3000|94913|316.37666666666667|141.77547599999994|241.13512692|13|
|18|Confirmation3|3000|95128|317.0933333333333|101.36438015|180.41693023999963|8|

All rows have zero schema errors. Values are individual unrounded observations; percentiles are not averaged or pooled. The calibrations each observed only one create and are not create-throughput proof. Quality gates: hold p95<500ms/p99<1000ms/errors<1%/schema0, plus unchanged runner/resource/monitoring/ownership/continuity validity checks.

Full-run hold error ratios:16=`0.00012654089907308792`,17=`0.00013696753869332968`,18=`8.409721638213776e-05`. Whole-scenario failed requests were15/14/8 respectively, distinct from hold errors12/13/8. Legitimate nonzero errors are not hidden.

Each full run has110resource observations/59scored observations, complete monitoring, no OOM/restarts or increased host swapouts. Scored runner CPU maxima136.57%/136.40%/119.84%; RAM16.14%/16.32%/16.25%. **Memory pressure is not zero:** hierarchical parent `memory.events:max` stayed6362 during16/17, then rose6362→6509 (+147) DURING18's scored hold. This counter alone is not an invalidity condition, and all required validity checks passed; do not infer its cause or claim pressure-free operation.

All complete strict preceding600s and timed manager-journal/coverage-anchor/clock/26protected-service checks passed. No Nhost fwupd waiver or timer/service suppression. Completed nonresident oneshots were disclosed; these checks do not prove absence of all interference. Existing production process/listener and unrelated services remained protected.

## Preserved physical history

| Physical | Generation / VUs | Disposition |
|---|---|---|
|1|v4smoke|INVALID preceding quiet proof|
|2|v4smoke|INVALID report assembly|
|3|v5/25smoke|PASS|
|4|v5/100smoke|PASS|
|5|v5/2500full|INVALID fwupd continuity|
|6|v5/2500full|PASS|
|7|v5/5000full|FAIL latency/errors|
|8|v5/3750full|FAIL latency|
|9|v5/3000full|INVALID fwupd continuity|
|10|v5/3000full|PASS, historical|
|11|v5/3250full|PASS, highest tested passing load|
|12|v5/3500full|FAIL latency|
|13|v5/3250confirmation|INVALID complete-log-capture timeout|
|14|v6/25smoke|PASS calibration|
|15|v6/100smoke|PASS calibration|
|16|v6/3000full|PASS confirmation1|
|17|v6/3000full|PASS confirmation2|
|18|v6/3000full|PASS confirmation3; studyCLOSED|

Physical13 remains consumed INVALID, never promoted. Its diagnostic p95=506.6687629999999ms is not an admitted scored verdict. The owner approved a prospective **untimed** complete-log capture repair10→120s, not serving-performance changes. Fresh qualification/calibrations/confirmations followed. The v5 observations did not disappear and are not silently counted as v6 confirmations.

Final consumption: **12/24 full attempts and6/6 smokes,18physical observations**. The original24full/4smoke policy remains immutable; a separate SHA-bound owner amendment permits six smokes without refunds. Spare global full slots do not authorize more runs. All earlier failures/invalidity/qualification originals remain retained, including those not copied into this report package.

## Provenance and available evidence

- Native immutable Git baseline:`161af0ef353aa6842b15046090a9e1af0068632b`.
- v5 qualification:`9f15d527f382b2baaaa5ba8132a1d395b2988e27a474aa22fc9382698c7eb281`.
- v6 qualification:`5f810093f7cc061d764ecb62804facd733584ec076604b9b5a55e6d5857d8274`.
- v6 correctness original:`51a6e805b9edd57c08b8e405b0295431d2185fb73b7f720e2400ee0bb5fa179a`.
- Measured v6 app fingerprint:`4880698fde7c5b947305482566f47282e08c43126ba985f86c37200de2916fbb`.
- Measured v6 verifier fingerprint:`32e6f7ac0e9c97537ce60a22dd5d62b498ccbfae8943b1bf77e03e4236cb8122`.
- Fixed-study authority:`d07b041786addbce6bfd7a68538849ca4924b317ec1c58dbbcbdf06352e63431`.
- Smoke amendment:`0853e766456d1540aa4336b43966ec8327d6730a0619ab0feb1a92073041b049`.

[`evidence/`](evidence/) contains byte-preserved, previously privacy-cleared native audit logs for the two historical bracket observations, five new study observations, v6 qualification and native regression checks. Each transport footer binds the preceding native original byte count/SHA and records actual-value/signature screening. These are independent review outputs, not substituted raw samples. `REPORT_SHA256SUMS` is a new publication inventory, not a rewrite of any original per-run manifest.

**The complete raw bundles are NOT published or export-cleared.** Full archive privacy screening hit its900s bound twice; no final archive clearance was obtained. Scalar and literal-matcher diagnostics/optimizations do not clear complete archives. `source.tar.gz`, `samples.json.gz`, raw journals, runtime secrets/JWT fixtures, database dumps and private state remain native; no download endpoint is provided. Original bundle hashes in the audit logs are provenance, not proof those archives are available from this repository.

Published implementation/configuration/tests are a scoped source release, excluding unrelated dirty Convex work. The exact measured worktree overlays remain in the native archives: do not treat the published checkout as a byte-identical historical snapshot or a complete independently reproducible evidence bundle.

Recorded pre-load native checks included93Nhost/24shared/3isolation regressions and qualification42original/19Node/6shared/7native methods, unavailable-storage behavior, acknowledged HTTP post/exactly-once like survival across actual same-owned-component restart, canonical reset and input freeze. No new product tests or load were run for this publication after owner closure; publication checks are Git/index/hash/format checks only.

## Shutdown and closure

Exact serving components are stopped/PID0/no OOM/restarts, but stock exits remain **PostgreSQL0/GraphQL137(non-OOM)/Auth2/adapter0**. This is not clean full-stack shutdown or power-loss certification. Controlled restart persistence is narrower evidence.

**Nhost benchmark is complete by owner decision. Highest tested passing load3,250VUs; next tested3,500failed. Exact maximum not established. No further tests or audits are scheduled.** Evidence export remains explicitly incomplete and separate from closure.
