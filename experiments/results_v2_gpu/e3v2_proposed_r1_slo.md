# E4 v2 — SLO capacity report — e3v2_proposed_r1

- Source: `experiments/results/e3v2_proposed_r1_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      30 |        464 |          3.09 |    1.26 |    1.83 |    2.02 | 0.0%         | yes         |
|      1 |      60 |        752 |          5.01 |    7.83 |    9.9  |   10.14 | 0.0%         | yes         |
|      2 |     120 |       2269 |          5.01 |   14.66 |   15.31 |   15.59 | 66.9%        | no          |
|      3 |     220 |       9543 |          4.59 |   16.82 |   17.82 |   18.06 | 92.8%        | no          |
|      4 |     520 |      31961 |          4.27 |   18.68 |   18.94 |   20.36 | 98.0%        | no          |
|      5 |    1000 |      66828 |          3.95 |   19.53 |   22.19 |   22.55 | 99.1%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   ok |   rejected (429/503) |
|-------:|-----:|---------------------:|
|      0 |  464 |                    0 |
|      1 |  752 |                    0 |
|      2 |  752 |                 1517 |
|      3 |  688 |                 8855 |
|      4 |  640 |                31321 |
|      5 |  592 |                66236 |

## Capacity

- **SLO capacity: 60 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 5.01 successful req/s
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 5.01 * (10 + 2) = **60 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.