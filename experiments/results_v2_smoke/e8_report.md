# E8 — Inference throughput

| label        |   concurrency |   requests |   req_per_s |   audio_s_per_s |   p50_s |   p95_s | error_rate   | device   | compute   |
|:-------------|--------------:|-----------:|------------:|----------------:|--------:|--------:|:-------------|:---------|:----------|
| cpu-fp32-b1  |             1 |         13 |        0.8  |           19.86 |    1.21 |    1.49 | 0.0%         | cpu      | fp32      |
| cpu-fp32-b1  |             2 |         13 |        0.79 |           19.56 |    2.47 |    2.85 | 0.0%         | cpu      | fp32      |
| cpu-fp32-b1  |             4 |         16 |        0.81 |           20.1  |    4.8  |    5.34 | 0.0%         | cpu      | fp32      |
| cuda-fp16-b8 |             1 |         26 |        1.72 |           42.4  |    0.58 |    0.63 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b8 |             2 |         42 |        2.72 |           67.17 |    0.67 |    1.19 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b8 |             4 |         67 |        4.42 |          109.23 |    0.78 |    1.49 | 0.0%         | cuda     | fp16      |

## Peak throughput per configuration

- `cpu-fp32-b1`: 20.1 s of audio per second — **1.0x** vs `cpu-fp32-b1`
- `cuda-fp16-b8`: 109.2 s of audio per second — **5.4x** vs `cpu-fp32-b1`

## Latency at concurrency 1 vs `cpu-fp32-b1` (single-request cost)

- `cuda-fp16-b8`: median 0.577s vs 1.212s — mann-whitney-u, p=0.0000, cliffs_delta=-1.000