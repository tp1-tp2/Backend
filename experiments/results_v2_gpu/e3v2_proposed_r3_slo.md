# E4 v2 — SLO capacity report — e3v2_proposed_r3

- Source: `experiments/results/e3v2_proposed_r3_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      20 |        456 |          3.04 |    1.23 |    1.74 |    1.98 | 0.0%         | yes         |
|      1 |      60 |        752 |          5.01 |    7.78 |    9.88 |   10.07 | 0.0%         | yes         |
|      2 |     120 |       2301 |          5.01 |   14.75 |   15.34 |   15.54 | 67.3%        | no          |
|      3 |     210 |       9554 |          4.69 |   16.7  |   17.69 |   17.79 | 92.6%        | no          |
|      4 |     520 |      31996 |          4.27 |   18.49 |   18.98 |   19.89 | 98.0%        | no          |
|      5 |    1000 |      66372 |          3.84 |   19.7  |   22.63 |   23.08 | 99.1%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   ok |   rejected (429/503) |
|-------:|-----:|---------------------:|
|      0 |  456 |                    0 |
|      1 |  752 |                    0 |
|      2 |  752 |                 1549 |
|      3 |  704 |                 8850 |
|      4 |  640 |                31356 |
|      5 |  576 |                65796 |

## Capacity

- **SLO capacity: 60 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 5.01 successful req/s
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 5.01 * (10 + 2) = **60 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.