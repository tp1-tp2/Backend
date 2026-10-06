# E8 — control de WER por clip (GPU)

Muestra estratificada de 30 clips. Para cada configuración se toma la primera transcripción correcta (HTTP 200) de cada clip, se normalizan referencia e hipótesis con `common.text_norm.normalize` y se calcula el WER con jiwer. Comparación pareada por clip frente a `cpu-fp32-b1` con la prueba de rangos con signo de Wilcoxon. Datos: `experiments/results/e8_<config>.csv` (no versionados).

| Configuración | Clips | WER medio | WER mediana | Salida idéntica a cpu-fp32-b1 | Wilcoxon p |
|---|---|---|---|---|---|
| `cpu-fp32-b1` | 30 | 0.735 | 0.750 | 30/30 | — |
| `cpu-int8-b1` | 30 | 0.727 | 0.748 | 3/30 | 0.781 |
| `cuda-fp32-b1` | 30 | 0.736 | 0.750 | 29/30 | 0.317 |
| `cuda-fp16-b1` | 30 | 0.742 | 0.750 | 25/30 | 0.180 |
| `cuda-fp16-b4` | 30 | 0.742 | 0.750 | 25/30 | 0.180 |
| `cuda-fp16-b8` | 30 | 0.742 | 0.750 | 25/30 | 0.180 |
| `cuda-fp16-b16` | 30 | 0.742 | 0.750 | 25/30 | 0.180 |
| `ct2-int8-l3t2` | 30 | 0.771 | 0.777 | 12/30 | 0.099 |

El WER de corpus de `e8_report.md` se calcula sobre todas las transcripciones de cada configuración, y esa cantidad varía con el throughput (cada clip aparece un número distinto de veces). Por eso el control de preservación de la salida es este WER por clip.
