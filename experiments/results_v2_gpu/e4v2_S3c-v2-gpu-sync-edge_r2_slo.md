# E4 v2 — SLO capacity report — e4v2_S3c-v2-gpu-sync-edge_r2

- Source: `experiments/results/e4v2_S3c-v2-gpu-sync-edge_r2_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      20 |        462 |          3.08 |    1.24 |    1.72 |    1.91 | 0.0%         | yes         |
|      1 |      60 |       1488 |          9.92 |    3.12 |    3.78 |    3.87 | 0.0%         | yes         |
|      2 |     120 |       2476 |          9.81 |    7.07 |    7.66 |    7.81 | 40.5%        | no          |
|      3 |     220 |       9593 |          9.39 |    8.27 |    8.62 |    8.7  | 85.3%        | no          |
|      4 |     520 |      31924 |          8.53 |    9.2  |    9.52 |    9.61 | 96.0%        | no          |
|      5 |    1000 |      65960 |          7.89 |    9.71 |   10.74 |   10.87 | 98.2%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   ok |   rejected (429/503) |
|-------:|-----:|---------------------:|
|      0 |  462 |                    0 |
|      1 | 1488 |                    0 |
|      2 | 1472 |                 1004 |
|      3 | 1408 |                 8185 |
|      4 | 1280 |                30644 |
|      5 | 1184 |                64776 |

## Capacity

- **SLO capacity: 60 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 9.92 successful req/s = 238.6 s of audio per second
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 9.92 * (10 + 2) = **119 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.