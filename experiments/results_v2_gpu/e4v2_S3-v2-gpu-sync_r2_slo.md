# E4 v2 — SLO capacity report — e4v2_S3-v2-gpu-sync_r2

- Source: `experiments/results/e4v2_S3-v2-gpu-sync_r2_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      20 |        456 |          3.04 |    1.27 |    1.87 |    2.07 | 0.0%         | yes         |
|      1 |      50 |       1456 |          9.71 |    3.1  |    3.8  |    3.93 | 0.0%         | yes         |
|      2 |     120 |       1831 |          9.71 |    7.75 |    8.47 |    8.63 | 20.5%        | no          |
|      3 |     210 |       4446 |          4.91 |   17.9  |   19.43 |   20.22 | 83.4%        | no          |
|      4 |     510 |       5202 |          3.59 |   28.84 |   35.02 |   37.86 | 89.6%        | no          |
|      5 |    1000 |       4139 |          3.63 |   45.32 |   67.32 |   74.48 | 86.9%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   HTTP 500 |   ok |   rejected (429/503) |
|-------:|-----------:|-----:|---------------------:|
|      0 |          0 |  456 |                    0 |
|      1 |          0 | 1456 |                    0 |
|      2 |          0 | 1456 |                  375 |
|      3 |          0 |  736 |                 3710 |
|      4 |          0 |  539 |                 4663 |
|      5 |        441 |  544 |                 3154 |

## Capacity

- **SLO capacity: 50 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 9.71 successful req/s = 233.4 s of audio per second
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 9.71 * (10 + 2) = **116 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.