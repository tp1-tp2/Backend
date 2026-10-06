# E4 v2 — SLO capacity report — e4v2_S3c-v2-gpu-sync-edge_r3

- Source: `experiments/results/e4v2_S3c-v2-gpu-sync-edge_r3_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      20 |        461 |          3.07 |    1.25 |    1.82 |    1.99 | 0.0%         | yes         |
|      1 |      50 |       1472 |          9.81 |    3.12 |    3.79 |    4.12 | 0.0%         | yes         |
|      2 |     120 |       2441 |          9.81 |    7.03 |    7.63 |    7.84 | 39.7%        | no          |
|      3 |     210 |       9622 |          9.28 |    8.27 |    8.67 |    8.76 | 85.5%        | no          |
|      4 |     520 |      31905 |          8.53 |    9.22 |    9.51 |    9.93 | 96.0%        | no          |
|      5 |    1000 |      65670 |          7.89 |    9.81 |   10.45 |   10.59 | 98.2%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   ok |   rejected (429/503) |
|-------:|-----:|---------------------:|
|      0 |  461 |                    0 |
|      1 | 1472 |                    0 |
|      2 | 1472 |                  969 |
|      3 | 1392 |                 8230 |
|      4 | 1280 |                30625 |
|      5 | 1184 |                64486 |

## Capacity

- **SLO capacity: 50 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 9.81 successful req/s = 236.0 s of audio per second
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 9.81 * (10 + 2) = **118 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.