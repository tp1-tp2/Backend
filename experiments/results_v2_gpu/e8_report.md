# E8 — Inference throughput

| label         |   concurrency |   requests |   req_per_s |   audio_s_per_s |   p50_s |   p95_s | error_rate   | device   | compute   |
|:--------------|--------------:|-----------:|------------:|----------------:|--------:|--------:|:-------------|:---------|:----------|
| cpu-fp32-b1   |             1 |         37 |        0.61 |           10.94 |    1.37 |    3.17 | 0.0%         | cpu      | fp32      |
| cpu-fp32-b1   |             2 |         37 |        0.58 |           11.18 |    3.42 |    5.71 | 0.0%         | cpu      | fp32      |
| cpu-fp32-b1   |             4 |         39 |        0.6  |           11.03 |    6.68 |    9.36 | 0.0%         | cpu      | fp32      |
| cpu-fp32-b1   |             8 |         46 |        0.63 |           11.06 |   12.37 |   16.05 | 0.0%         | cpu      | fp32      |
| cpu-fp32-b1   |            16 |         51 |        0.61 |           11.1  |   26.73 |   29.39 | 0.0%         | cpu      | fp32      |
| cpu-fp32-b1   |            32 |       4479 |        0.52 |           10.05 |   53.34 |   70.17 | 98.7%        | cpu      | fp32      |
| cpu-int8-b1   |             1 |         54 |        0.88 |           16.79 |    1.07 |    1.91 | 0.0%         | cpu      | int8      |
| cpu-int8-b1   |             2 |         57 |        0.92 |           16.28 |    2.21 |    3.57 | 0.0%         | cpu      | int8      |
| cpu-int8-b1   |             4 |         59 |        0.9  |           16.61 |    4.29 |    5.95 | 0.0%         | cpu      | int8      |
| cpu-int8-b1   |             8 |         62 |        0.9  |           16.39 |    8.92 |   10.74 | 0.0%         | cpu      | int8      |
| cpu-int8-b1   |            16 |         72 |        0.94 |           16.22 |   17.19 |   19.98 | 0.0%         | cpu      | int8      |
| cpu-int8-b1   |            32 |         83 |        0.87 |           16.71 |   35.61 |   40.42 | 0.0%         | cpu      | int8      |
| cuda-fp16-b1  |             1 |        190 |        3.15 |           57.55 |    0.24 |    0.64 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b1  |             2 |        191 |        3.17 |           57.78 |    0.64 |    1.19 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b1  |             4 |        198 |        3.22 |           58.5  |    1.31 |    1.85 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b1  |             8 |        198 |        3.15 |           57.91 |    2.58 |    3.6  | 0.0%         | cuda     | fp16      |
| cuda-fp16-b1  |            16 |        209 |        3.2  |           58.17 |    5.04 |    5.88 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b1  |            32 |        226 |        3.22 |           58.68 |    9.88 |   11.1  | 0.0%         | cuda     | fp16      |
| cuda-fp16-b16 |             1 |        172 |        2.85 |           52.32 |    0.27 |    0.68 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b16 |             2 |        250 |        4.17 |           75.23 |    0.47 |    0.8  | 0.0%         | cuda     | fp16      |
| cuda-fp16-b16 |             4 |        288 |        4.72 |           86.71 |    0.87 |    1.12 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b16 |             8 |        312 |        5.18 |           93.65 |    1.49 |    1.85 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b16 |            16 |        337 |        5.47 |           99.95 |    3.13 |    3.53 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b16 |            32 |        342 |        5.38 |           98.07 |    5.92 |    6.35 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b4  |             1 |        171 |        2.85 |           52.09 |    0.27 |    0.68 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b4  |             2 |        232 |        3.85 |           70.47 |    0.55 |    0.79 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b4  |             4 |        300 |        4.98 |           90.73 |    0.88 |    1.09 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b4  |             8 |        308 |        5.04 |           91.28 |    1.64 |    2.04 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b4  |            16 |        312 |        5.01 |           90.64 |    3.12 |    3.74 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b4  |            32 |        328 |        4.98 |           91    |    6.31 |    6.89 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b8  |             1 |        171 |        2.85 |           52.09 |    0.27 |    0.68 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b8  |             2 |        232 |        3.85 |           70.62 |    0.55 |    0.79 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b8  |             4 |        296 |        4.85 |           87.86 |    0.9  |    1.12 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b8  |             8 |        320 |        5.3  |           96.62 |    1.5  |    1.76 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b8  |            16 |        336 |        5.34 |           96.64 |    3.09 |    3.26 | 0.0%         | cuda     | fp16      |
| cuda-fp16-b8  |            32 |        351 |        5.35 |           98.35 |    5.96 |    6.12 | 0.0%         | cuda     | fp16      |
| cuda-fp32-b1  |             1 |        117 |        1.95 |           36.16 |    0.39 |    1    | 0.0%         | cuda     | fp32      |
| cuda-fp32-b1  |             2 |        123 |        2.04 |           36.44 |    1    |    1.86 | 0.0%         | cuda     | fp32      |
| cuda-fp32-b1  |             4 |        123 |        2.02 |           36.4  |    2.1  |    2.95 | 0.0%         | cuda     | fp32      |
| cuda-fp32-b1  |             8 |        127 |        1.97 |           36.44 |    4.04 |    5.72 | 0.0%         | cuda     | fp32      |
| cuda-fp32-b1  |            16 |        135 |        1.98 |           36.5  |    8.18 |    9.26 | 0.0%         | cuda     | fp32      |
| cuda-fp32-b1  |            32 |        151 |        2.01 |           36.39 |   15.75 |   16.94 | 0.0%         | cuda     | fp32      |

## Peak throughput per configuration

- `cpu-fp32-b1`: 11.2 s of audio per second — **1.0x** vs `cpu-fp32-b1`
- `cpu-int8-b1`: 16.8 s of audio per second — **1.5x** vs `cpu-fp32-b1`
- `cuda-fp32-b1`: 36.5 s of audio per second — **3.3x** vs `cpu-fp32-b1`
- `cuda-fp16-b1`: 58.7 s of audio per second — **5.3x** vs `cpu-fp32-b1`
- `cuda-fp16-b4`: 91.3 s of audio per second — **8.2x** vs `cpu-fp32-b1`
- `cuda-fp16-b8`: 98.4 s of audio per second — **8.8x** vs `cpu-fp32-b1`
- `cuda-fp16-b16`: 100.0 s of audio per second — **8.9x** vs `cpu-fp32-b1`

## Latency at concurrency 1 vs `cpu-fp32-b1` (single-request cost)

- `cpu-int8-b1`: median 1.070s vs 1.375s — mann-whitney-u, p=0.0052, cliffs_delta=-0.346
- `cuda-fp16-b1`: median 0.241s vs 1.375s — mann-whitney-u, p=0.0000, cliffs_delta=-0.979
- `cuda-fp16-b16`: median 0.270s vs 1.375s — mann-whitney-u, p=0.0000, cliffs_delta=-0.967
- `cuda-fp16-b4`: median 0.273s vs 1.375s — mann-whitney-u, p=0.0000, cliffs_delta=-0.967
- `cuda-fp16-b8`: median 0.272s vs 1.375s — mann-whitney-u, p=0.0000, cliffs_delta=-0.966
- `cuda-fp32-b1`: median 0.389s vs 1.375s — mann-whitney-u, p=0.0000, cliffs_delta=-0.827

## Output-preservation control (WER per configuration)

- `cpu-fp32-b1`: corpus WER 0.792 over 268 transcriptions
- `cpu-int8-b1`: corpus WER 0.808 over 387 transcriptions
- `cuda-fp16-b1`: corpus WER 0.800 over 1212 transcriptions
- `cuda-fp16-b16`: corpus WER 0.795 over 1701 transcriptions
- `cuda-fp16-b4`: corpus WER 0.795 over 1651 transcriptions
- `cuda-fp16-b8`: corpus WER 0.795 over 1706 transcriptions
- `cuda-fp32-b1`: corpus WER 0.792 over 776 transcriptions