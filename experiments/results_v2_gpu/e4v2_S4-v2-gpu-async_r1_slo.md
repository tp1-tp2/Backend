# E4 v2 — SLO capacity report — e4v2_S4-v2-gpu-async_r1

- Source: `experiments/results/e4v2_S4-v2-gpu-async_r1_raw.csv` — request `job_e2e`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      30 |        401 |          2.67 |    2.13 |    2.15 |    2.16 | 0.0%         | yes         |
|      1 |      70 |       1301 |          8.67 |    4.14 |    4.17 |    4.19 | 0.0%         | yes         |
|      2 |     120 |       1277 |          8.51 |   10.16 |   10.21 |   10.24 | 0.0%         | no          |
|      3 |     230 |       1256 |          8.37 |   22.22 |   22.31 |   22.38 | 0.0%         | no          |
|      4 |     520 |       1189 |          7.93 |   60.04 |   61.81 |   62.24 | 0.0%         | no          |
|      5 |    1000 |       1071 |          7.14 |   97.05 |  127.27 |  130.33 | 0.0%         | no          |
|      6 |     712 |        712 |          4.75 |  119.83 |  126.02 |  126.78 | 0.0%         | no          |

## Failure breakdown per step (steady-state window)

|   step |   ok |
|-------:|-----:|
|      0 |  401 |
|      1 | 1301 |
|      2 | 1277 |
|      3 | 1256 |
|      4 | 1189 |
|      5 | 1071 |
|      6 |  712 |

## Capacity

- **SLO capacity: 70 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 8.67 successful req/s = 208.6 s of audio per second
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 8.67 * (10 + 2) = **104 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.