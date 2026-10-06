# E4 v2 — SLO capacity report — e3v2_proposed_r2

- Source: `experiments/results/e3v2_proposed_r2_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      20 |        461 |          3.07 |    1.25 |    1.79 |    1.92 | 0.0%         | yes         |
|      1 |      70 |        752 |          5.01 |    7.84 |    9.97 |   10.16 | 0.0%         | yes         |
|      2 |     120 |       2293 |          5.01 |   14.76 |   15.37 |   15.49 | 67.2%        | no          |
|      3 |     210 |       9537 |          4.59 |   16.91 |   17.68 |   17.91 | 92.8%        | no          |
|      4 |     520 |      31932 |          4.16 |   18.65 |   19.04 |   20.43 | 98.0%        | no          |
|      5 |    1000 |      67458 |          3.84 |   19.8  |   22.27 |   22.68 | 99.1%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   ok |   rejected (429/503) |
|-------:|-----:|---------------------:|
|      0 |  461 |                    0 |
|      1 |  752 |                    0 |
|      2 |  752 |                 1541 |
|      3 |  688 |                 8849 |
|      4 |  624 |                31308 |
|      5 |  576 |                66882 |

## Capacity

- **SLO capacity: 70 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 5.01 successful req/s
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 5.01 * (10 + 2) = **60 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.