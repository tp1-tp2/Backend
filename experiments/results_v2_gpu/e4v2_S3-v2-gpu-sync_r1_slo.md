# E4 v2 — SLO capacity report — e4v2_S3-v2-gpu-sync_r1

- Source: `experiments/results/e4v2_S3-v2-gpu-sync_r1_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      30 |        469 |          3.13 |    1.21 |    1.71 |    1.88 | 0.0%         | yes         |
|      1 |      60 |       1488 |          9.92 |    3.06 |    3.75 |    3.95 | 0.0%         | yes         |
|      2 |     110 |       1821 |          9.71 |    7.71 |    8.46 |    8.64 | 20.0%        | no          |
|      3 |     230 |       4699 |          4.59 |   18.21 |   20.47 |   21.36 | 85.4%        | no          |
|      4 |     520 |       5190 |          3.41 |   31.45 |   36.73 |   42.62 | 90.1%        | no          |
|      5 |    1000 |       4305 |          3.31 |   47.18 |   68.96 |   80.39 | 88.5%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   HTTP 500 |   ok |   rejected (429/503) |
|-------:|-----------:|-----:|---------------------:|
|      0 |          0 |  469 |                    0 |
|      1 |          0 | 1488 |                    0 |
|      2 |          0 | 1456 |                  365 |
|      3 |          0 |  688 |                 4011 |
|      4 |          0 |  512 |                 4678 |
|      5 |        466 |  496 |                 3343 |

## Capacity

- **SLO capacity: 60 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 9.92 successful req/s = 238.6 s of audio per second
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 9.92 * (10 + 2) = **119 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.