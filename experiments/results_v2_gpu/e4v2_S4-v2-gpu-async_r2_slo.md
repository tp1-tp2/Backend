# E4 v2 — SLO capacity report — e4v2_S4-v2-gpu-async_r2

- Source: `experiments/results/e4v2_S4-v2-gpu-async_r2_raw.csv` — request `job_e2e`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      30 |        400 |          2.67 |    2.13 |    2.15 |    2.16 | 0.0%         | yes         |
|      1 |      80 |       1277 |          8.51 |    4.15 |    4.18 |    4.2  | 0.0%         | yes         |
|      2 |     120 |       1258 |          8.39 |   10.17 |   10.21 |   10.25 | 0.0%         | no          |
|      3 |     230 |       1231 |          8.21 |   22.24 |   23.25 |   23.36 | 0.0%         | no          |
|      4 |     530 |       1004 |          6.69 |   61.76 |   83.67 |   84.24 | 0.0%         | no          |
|      5 |    1000 |       1056 |          7.04 |   97.56 |  129    |  132.02 | 0.0%         | no          |
|      6 |     723 |        723 |          4.82 |  123.45 |  129.37 |  130.21 | 0.0%         | no          |

## Failure breakdown per step (steady-state window)

|   step |   ok |
|-------:|-----:|
|      0 |  400 |
|      1 | 1277 |
|      2 | 1258 |
|      3 | 1231 |
|      4 | 1004 |
|      5 | 1056 |
|      6 |  723 |

## Capacity

- **SLO capacity: 80 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 8.51 successful req/s = 204.7 s of audio per second
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 8.51 * (10 + 2) = **102 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.