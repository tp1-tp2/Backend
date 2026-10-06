# E4 v2 — SLO capacity report — e3v2_monolith_r2

- Source: `experiments/results/e3v2_monolith_r2_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      50 |        248 |          1.65 |    4.2  |    4.99 |    5.99 | 0.0%         | yes         |
|      1 |     100 |        265 |          1.77 |   24.91 |   32.06 |   34.04 | 0.0%         | no          |
|      2 |     170 |        255 |          1.68 |   43.63 |   50.62 |   53.21 | 1.2%         | no          |
|      3 |     270 |        467 |          1.2  |   55.75 |   67.81 |   68.56 | 61.5%        | no          |
|      4 |     580 |        840 |          0.49 |   40.42 |   68.5  |   69.18 | 91.2%        | no          |
|      5 |    1000 |       1082 |          0.53 |   68.27 |   70.05 |   71.17 | 92.6%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   HTTP 500 |   connection error |   ok |
|-------:|-----------:|-------------------:|-----:|
|      0 |          0 |                  0 |  248 |
|      1 |          0 |                  0 |  265 |
|      2 |          3 |                  0 |  252 |
|      3 |        287 |                  0 |  180 |
|      4 |        766 |                  0 |   74 |
|      5 |        979 |                 23 |   80 |

## Capacity

- **SLO capacity: 50 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 1.77 successful req/s
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 1.77 * (10 + 2) = **21 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.