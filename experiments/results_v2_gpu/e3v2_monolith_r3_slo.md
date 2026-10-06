# E4 v2 — SLO capacity report — e3v2_monolith_r3

- Source: `experiments/results/e3v2_monolith_r3_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      50 |        247 |          1.65 |    4.28 |    4.93 |    5.26 | 0.0%         | yes         |
|      1 |      80 |        259 |          1.73 |   25.84 |   33.75 |   36.43 | 0.0%         | no          |
|      2 |     170 |        245 |          1.63 |   50.01 |   55.04 |   60.3  | 0.4%         | no          |
|      3 |     270 |        329 |          1.43 |   60.06 |   66.06 |   67.45 | 34.7%        | no          |
|      4 |     580 |        734 |          0.67 |   67.02 |   68.6  |   68.78 | 86.2%        | no          |
|      5 |    1000 |       1506 |          0.65 |   67.42 |   69.81 |   70.22 | 93.6%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   HTTP 500 |   connection error |   ok |
|-------:|-----------:|-------------------:|-----:|
|      0 |          0 |                  0 |  247 |
|      1 |          0 |                  0 |  259 |
|      2 |          1 |                  0 |  244 |
|      3 |        114 |                  0 |  215 |
|      4 |        633 |                  0 |  101 |
|      5 |       1033 |                376 |   97 |

## Capacity

- **SLO capacity: 50 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 1.73 successful req/s
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 1.73 * (10 + 2) = **21 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.