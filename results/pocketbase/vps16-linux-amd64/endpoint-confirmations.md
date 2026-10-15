# PocketBase — independent confirmation endpoint metrics

## Tested software and VPS slice

- **PocketBase v0.40.5**, upstream **`6f370ea741f33adf889eef02e3c1b884a47aa522`**; **Go 1.27.2**, **SQLite 3.53.4 / modernc.org/sqlite v1.60.1**, native Linux AMD64.
- Immutable serving image **`sha256:489cba19771795f5378e440c7f6d83d81f8460bf31e673aff8a392b080a9b131`**; executable SHA256 **`0e31cb09904df2e7cfb8a8e8d2fe18a577a1a2e4e55b92e7b937f1ee157123f8`**. Builder **`golang:1.27.2-bookworm@sha256:55395706e9703db746cc507abfc4eb2aea75918f8a8024e4848e2cb81004f5ad`**; runtime **`debian:bookworm-slim@sha256:a4672c0cb26fbdde88e38fa2dfb6c681942306680e41e4378b28770b6e79ee91`**. Complete module lock, source fingerprints, upstream/builder/runtime index and selected-child references: [versions](../../../services/pocketbase/versions.json), [native build](setup-evidence/full-native-build-manifest.json), [final attestation](setup-evidence/final-deployment-attestation.json).
- **Entire serving stack: 1 vCPU quota / 4 GiB RAM (4,294,967,296 bytes) / no swap** under `tdsbaaspocketbasevps16.slice`: native routes, REST/Auth/admin/realtime implementation and embedded main/auxiliary databases. No unbudgeted serving proxy or database.
- **Separate runner: k6 1.3.0 / 2 vCPU quota / 8 GiB RAM (8,589,934,592 bytes) / no swap**, `k6-2cpu-8g-v3`, selected native image `sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656`.
- Serving runs on an existing **quota-limited shared-host slice**, **not a dedicated one-vCPU VPS or measured $12/month offering**. Physical host: native AMD64 Ubuntu 24.04.5, Docker 29.8.1; 4 CPUs / 16,770,072,576 bytes RAM / no swap; this is **not** the serving allocation. At least1 CPU / 1 GiB reserve is required beyond serving and runner. Price/region unknown; no cost/request claim.


Quantiles are per endpoint/per hold, never pooled. Counts include all attempted requests; errors are separately listed. Status distributions and raw-point reproduction are in `setup-evidence/retained-attempt-review.json`.

| Hold | Endpoint | Requests | RPS | p50 ms | p95 ms | p99 ms | Maximum ms | Errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | feed | 145,847 | 486.1567 | 17.7345 | 51.5511 | 77.596 | 155.0992 | 0 |
| 1 | detail | 146,010 | 486.7 | 17.609 | 51.2124 | 77.7268 | 150.3382 | 0 |
| 1 | like | 21,718 | 72.3933 | 63.7531 | 514.1413 | 1,024.5176 | 4,668.7871 | 0 |
| 1 | create | 3,000 | 10 | 135.2255 | 583.2221 | 1,077.8064 | 3,120.1962 | 0 |
| 2 | feed | 145,868 | 486.2267 | 15.5378 | 49.1556 | 74.3063 | 177.9113 | 0 |
| 2 | detail | 146,003 | 486.6767 | 15.5853 | 49.0975 | 74.9775 | 177.6065 | 0 |
| 2 | like | 21,810 | 72.7 | 50.2165 | 414.8094 | 900.5536 | 2,930.3504 | 0 |
| 2 | create | 2,865 | 9.55 | 121.6509 | 484.1039 | 863.0952 | 3,162.3347 | 0 |
| 3 | feed | 145,844 | 486.1467 | 15.8597 | 48.0875 | 70.6714 | 135.1258 | 0 |
| 3 | detail | 145,987 | 486.6233 | 15.8055 | 48.1992 | 71.1386 | 152.5414 | 0 |
| 3 | like | 21,878 | 72.9267 | 52.8759 | 483.6016 | 992.077 | 2,791.669 | 0 |
| 3 | create | 2,909 | 9.6967 | 126.8105 | 575.2258 | 1,048.4023 | 2,727.7408 | 0 |
