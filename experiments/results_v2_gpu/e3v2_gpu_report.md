# E3 v2 — propuesta (n=3) frente a monolito (n=3)

| Usuarios | Arquitectura | Solicitudes | Éxito | Goodput (mediana) | p50 | p95 | p99 | Fallos |
|---|---|---|---|---|---|---|---|---|
| 10 | Propuesta | 1651 | 100.0 % | 3.06 | 1.3 | 1.8 | 2.7 | — |
| 10 | Monolito | 883 | 100.0 % | 1.63 | 4.3 | 5.2 | 6.4 | — |
| 50 | Propuesta | 2663 | 100.0 % | 4.94 | 7.8 | 9.9 | 10.2 | — |
| 50 | Monolito | 836 | 100.0 % | 1.52 | 25.4 | 32.9 | 35.9 | — |
| 100 | Propuesta | 8087 | 33.6 % | 5.07 | 14.5 | 15.3 | 15.6 | 503×5367 |
| 100 | Monolito | 886 | 94.6 % | 1.56 | 45.3 | 56.5 | 60.8 | 500×48 |
| 200 | Propuesta | 33779 | 7.3 % | 4.53 | 16.6 | 17.8 | 18.1 | 503×31315 |
| 200 | Monolito | 1421 | 48.9 % | 1.28 | 53.5 | 66.0 | 68.5 | 500×726 |
| 500 | Propuesta | 108274 | 2.1 % | 4.18 | 18.5 | 20.2 | 21.0 | 503×106002 |
| 500 | Monolito | 5439 | 10.5 % | 0.97 | 53.7 | 68.9 | 69.4 | 500×4869 |
| 1000 | Propuesta | 228192 | 0.9 % | 3.91 | 19.6 | 22.3 | 22.8 | 503×226080 |
| 1000 | Monolito | 1719 | 9.2 % | 0.30 | 67.9 | 69.5 | 71.0 | 500×1161, 0×400 |

| Usuarios | Prueba | Valor p | Tamaño de efecto | Magnitud | Mediana propuesta (s) | Mediana monolito (s) | Significativo |
|---|---|---|---|---|---|---|---|
| 10 | mann-whitney-u | 0 | cliffs_delta = -0.933 | grande | 1.3 | 4.3 | Sí |
| 50 | mann-whitney-u | 0 | cliffs_delta = -0.976 | grande | 7.8 | 25.4 | Sí |
| 100 | mann-whitney-u | 0 | cliffs_delta = -0.974 | grande | 14.5 | 45.3 | Sí |
| 200 | mann-whitney-u | 0 | cliffs_delta = -0.963 | grande | 16.6 | 53.5 | Sí |
| 500 | mann-whitney-u | 8.378e-180 | cliffs_delta = -0.784 | grande | 18.5 | 53.7 | Sí |
| 1000 | mann-whitney-u | 1.284e-68 | cliffs_delta = -0.835 | grande | 19.6 | 67.9 | Sí |
