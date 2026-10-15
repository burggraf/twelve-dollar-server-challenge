# Supabase — independent confirmation endpoint metrics

All values are original per-hold summary metrics; no pooled/averaged percentiles. Throughput includes measured requests, including errors. Status/error counts and exact percentile reproduction from original raw streams are in [raw sample audit](setup-evidence/raw-sample-audit.json).

| Hold | Endpoint | Requests | Requests/s | p50 ms | p95 ms | p99 ms | Maximum ms | Errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | feed | 29,168 | 97.23 | 5.00 | 133.94 | 420.27 | 1,910.44 | 1 (0.00343%) |
| 1 | detail | 29,194 | 97.31 | 4.02 | 115.38 | 402.97 | 1,798.44 | 1 (0.00343%) |
| 1 | like | 4,351 | 14.50 | 4.91 | 135.98 | 458.80 | 1,202.93 | 0 (0.00000%) |
| 1 | create | 545 | 1.82 | 5.74 | 113.94 | 381.91 | 829.01 | 0 (0.00000%) |
| 2 | feed | 29,163 | 97.21 | 5.17 | 163.74 | 465.64 | 1,246.35 | 2 (0.00686%) |
| 2 | detail | 29,208 | 97.36 | 4.15 | 161.28 | 475.43 | 1,396.74 | 0 (0.00000%) |
| 2 | like | 4,439 | 14.80 | 5.08 | 179.43 | 496.76 | 1,185.85 | 0 (0.00000%) |
| 2 | create | 591 | 1.97 | 5.76 | 212.24 | 565.51 | 1,307.59 | 0 (0.00000%) |
| 3 | feed | 29,226 | 97.42 | 5.05 | 126.67 | 412.59 | 1,375.24 | 1 (0.00342%) |
| 3 | detail | 29,204 | 97.35 | 4.07 | 127.88 | 408.04 | 1,407.40 | 0 (0.00000%) |
| 3 | like | 4,398 | 14.66 | 5.06 | 151.77 | 458.96 | 900.85 | 2 (0.04548%) |
| 3 | create | 678 | 2.26 | 5.54 | 82.88 | 312.27 | 718.43 | 0 (0.00000%) |
