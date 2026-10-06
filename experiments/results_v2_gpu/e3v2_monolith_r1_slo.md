# E4 v2 — SLO capacity report — e3v2_monolith_r1

- Source: `experiments/results/e3v2_monolith_r1_raw.csv` — request `/api/v1/transcribe`
- SLO: p95 <= 10 s and error rate <= 5% (first 30 s of each 180 s step excluded)

|   step |   users |   requests |   goodput_rps |   p50_s |   p95_s |   p99_s | error_rate   | meets_slo   |
|-------:|--------:|-----------:|--------------:|--------:|--------:|--------:|:-------------|:------------|
|      0 |      10 |        240 |          1.6  |    4.23 |    5.11 |    5.34 | 0.0%         | yes         |
|      1 |     100 |        257 |          1.71 |   25.96 |   32.2  |   38.52 | 0.0%         | no          |
|      2 |     120 |        259 |          1.55 |   49.92 |   63.42 |   65.77 | 10.4%        | no          |
|      3 |     270 |        615 |          1.13 |   52.22 |   65.32 |   69.26 | 72.5%        | no          |
|      4 |     580 |        896 |          0.61 |   64.65 |   68.26 |   68.73 | 89.7%        | no          |
|      5 |     987 |       1080 |          0.47 |   41.64 |   69.07 |   69.59 | 93.5%        | no          |

## Failure breakdown per step (steady-state window)

|   step |   HTTP 500 |   connection error |   ok |
|-------:|-----------:|-------------------:|-----:|
|      0 |          0 |                  0 |  240 |
|      1 |          0 |                  0 |  257 |
|      2 |         27 |                  0 |  232 |
|      3 |        446 |                  0 |  169 |
|      4 |        804 |                  0 |   92 |
|      5 |       1009 |                  1 |   70 |

## Capacity

- **SLO capacity: 10 concurrent users** (largest step meeting the SLO)
- Peak goodput X_max: 1.71 successful req/s
- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = 1.71 * (10 + 2) = **21 users**

Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of request routing can meet it at this service rate — it requires more inference throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.