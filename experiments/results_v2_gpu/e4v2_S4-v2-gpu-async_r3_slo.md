# E4 v2 — SLO capacity report — e4v2_S4-v2-gpu-async_r3

- Source: `experiments/results/e4v2_S4-v2-gpu-async_r3_raw.csv` — request `job_e2e`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      40 |        408 |          2.72 |    2.13 |    2.15 |    2.16 | 0.0%         | yes         |
|      1 |      70 |       1293 |          8.62 |    4.14 |    4.17 |    4.2  | 0.0%         | yes         |
|      2 |     120 |       1278 |          8.52 |   10.17 |   10.21 |   10.24 | 0.0%         | no          |
|      3 |     230 |       1252 |          8.35 |   22.22 |   22.33 |   23.24 | 0.0%         | no          |
|      4 |     520 |       1063 |          7.09 |   60.7  |   75.41 |   76.09 | 0.0%         | no          |
|      5 |    1000 |       1056 |          7.04 |   97.57 |  127.97 |  130.82 | 0.0%         | no          |
|      6 |     715 |        715 |          4.77 |  120.31 |  126.56 |  127.26 | 0.0%         | no          |

## Failure breakdown per step (steady-state window)

|   step |   ok |
|-------:|-----:|
|      0 |  408 |
|      1 | 1293 |
|      2 | 1278 |
|      3 | 1252 |
|      4 | 1063 |
|      5 | 1056 |
|      6 |  715 |

## Capacity

- **SLO capacity: 70 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 8.62 successful req/s = 207.3 s of audio per second
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 8.62 * (10 + 2) = **103 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.