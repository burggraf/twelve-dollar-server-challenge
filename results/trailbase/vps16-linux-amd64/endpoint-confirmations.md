# Confirmation endpoint breakdowns

Each row covers a separate 300-second scored hold at 15,000 VUs. No quantiles are pooled or averaged. All successful-response schema checks passed; aggregate schema-error rate is zero for every hold. Full precision, maxima, and all-phase metrics remain in each raw `k6-summary.json`.

| Hold | Endpoint | Requests | Requests/s | p50 / p95 / p99 ms | Request errors |
|---|---|---:|---:|---:|---:|
| 1 | feed | 219,152 | 730.51 | 1.03 / 26.98 / 63.82 | 0% |
| 1 | detail | 219,481 | 731.60 | 0.75 / 20.90 / 60.14 | 0% |
| 1 | like | 32,983 | 109.94 | 1.10 / 26.11 / 67.40 | 0% |
| 1 | create | 4,431 | 14.77 | 1.16 / 24.47 / 62.11 | 0% |
| 2 | feed | 219,050 | 730.17 | 1.02 / 34.20 / 99.79 | 0% |
| 2 | detail | 219,297 | 730.99 | 0.75 / 28.12 / 97.34 | 0% |
| 2 | like | 32,868 | 109.56 | 1.09 / 34.70 / 103.80 | 0% |
| 2 | create | 4,372 | 14.57 | 1.16 / 32.35 / 99.17 | 0% |
| 3 | feed | 219,127 | 730.42 | 1.03 / 27.66 / 97.02 | 0% |
| 3 | detail | 219,470 | 731.57 | 0.75 / 21.48 / 91.24 | 0% |
| 3 | like | 32,942 | 109.81 | 1.09 / 25.86 / 89.02 | 0% |
| 3 | create | 4,485 | 14.95 | 1.18 / 24.86 / 87.91 | 0% |
