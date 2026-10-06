# E4 v2 — SLO capacity report — e4v2_S3c-v2-gpu-sync-edge_r1

- Source: `experiments/results/e4v2_S3c-v2-gpu-sync-edge_r1_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      20 |        455 |          3.03 |    1.24 |    1.88 |    2.08 | 0.0%         | yes         |
|      1 |      70 |       1488 |          9.92 |    3.13 |    3.77 |    3.96 | 0.0%         | yes         |
|      2 |     120 |       2458 |          9.81 |    7.03 |    7.59 |    7.75 | 40.1%        | no          |
|      3 |     210 |       9581 |          9.28 |    8.33 |    8.68 |    8.76 | 85.5%        | no          |
|      4 |     520 |      31938 |          8.53 |    9.26 |    9.57 |    9.85 | 96.0%        | no          |
|      5 |    1000 |      65789 |          8    |    9.68 |   10.57 |   10.73 | 98.2%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   ok |   rejected (429/503) |
|-------:|-----:|---------------------:|
|      0 |  455 |                    0 |
|      1 | 1488 |                    0 |
|      2 | 1472 |                  986 |
|      3 | 1392 |                 8189 |
|      4 | 1280 |                30658 |
|      5 | 1200 |                64589 |

## Capacity

- **SLO capacity: 70 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 9.92 successful req/s = 238.6 s of audio per second
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 9.92 * (10 + 2) = **119 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.