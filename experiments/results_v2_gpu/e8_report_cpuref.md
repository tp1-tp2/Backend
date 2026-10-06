# E8 — Inference throughput

| label         |   concurrency |   requests |   req_per_s |   audio_s_per_s |   p50_s |   p95_s | error_rate   | device   | compute   |
|:--------------|--------------:|-----------:|------------:|----------------:|--------:|--------:|:-------------|:---------|:----------|
| ct2-int8-l3t2 |             1 |         48 |        1.05 |           19.24 |    0.83 |    1.5  | 0.0%         | cpu      | int8      |
| ct2-int8-l3t2 |             2 |         69 |        1.5  |           28.09 |    1.16 |    2.11 | 0.0%         | cpu      | int8      |
| ct2-int8-l3t2 |             4 |         73 |        1.57 |           27.88 |    2.62 |    3.77 | 0.0%         | cpu      | int8      |
| ct2-int8-l3t2 |             8 |         76 |        1.53 |           28.42 |    5.17 |    6.69 | 0.0%         | cpu      | int8      |
| ct2-int8-l3t2 |            16 |         84 |        1.52 |           27.55 |   10.37 |   11.92 | 0.0%         | cpu      | int8      |

## Peak throughput per configuration

- `ct2-int8-l3t2`: 28.4 s of audio per second

## Output-preservation control (WER per configuration)

- `ct2-int8-l3t2`: corpus WER 0.854 over 350 transcriptions