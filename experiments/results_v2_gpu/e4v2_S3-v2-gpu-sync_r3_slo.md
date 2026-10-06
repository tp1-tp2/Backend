# E4 v2 — SLO capacity report — e4v2_S3-v2-gpu-sync_r3

- Source: `experiments/results/e4v2_S3-v2-gpu-sync_r3_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      30 |        460 |          3.07 |    1.24 |    1.82 |    2.04 | 0.0%         | yes         |
|      1 |      60 |       1472 |          9.81 |    3.13 |    3.85 |    4.19 | 0.0%         | yes         |
|      2 |     120 |       1829 |          9.49 |    7.81 |    8.55 |    8.68 | 22.1%        | no          |
|      3 |     220 |       4529 |          4.8  |   17.74 |   19.71 |   22.37 | 84.1%        | no          |
|      4 |     520 |       5171 |          3.49 |   30.87 |   35.4  |   35.99 | 89.9%        | no          |
|      5 |    1000 |       4100 |          3.52 |   46.17 |   68.43 |   78.33 | 87.1%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   HTTP 500 |   ok |   rejected (429/503) |
|-------:|-----------:|-----:|---------------------:|
|      0 |          0 |  460 |                    0 |
|      1 |          0 | 1472 |                    0 |
|      2 |          0 | 1424 |                  405 |
|      3 |          0 |  720 |                 3809 |
|      4 |          0 |  523 |                 4648 |
|      5 |        405 |  528 |                 3167 |

## Capacity

- **SLO capacity: 60 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 9.81 successful req/s = 236.0 s of audio per second
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 9.81 * (10 + 2) = **118 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.