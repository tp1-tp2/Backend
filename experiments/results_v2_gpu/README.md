# Evidencia de los experimentos v2 con GPU (2026-10-05)

Resúmenes de las corridas descritas en `docs/18-resultados-v2-gpu.md`. Protocolo en `docs/15-pendientes-gpu.md`. Corpus real (IWSLT2026: Huqariq + Siminchik) y 3 repeticiones por condición, salvo E8 y E2 (una corrida). Los CSV crudos no se versionan (`experiments/results/` está en `.gitignore`).

- `e8_report.md`, `e8_report.csv`: throughput de inferencia, 7 configuraciones (CPU fp32/int8; CUDA fp32 y fp16 con *batch* 1, 4, 8 y 16), concurrencia 1–32.
- `e8_report_cpuref.md`, `e8_report_cpuref.csv`: referencia de CPU optimizada (`ct2-int8-l3t2`) en el mismo equipo, concurrencia 1–16.
- `e8_wer_control.md`: control de WER por clip frente a `cpu-fp32-b1` (Wilcoxon).
- `e8_*.batches.json`: histograma de tamaños de *batch* por nivel de concurrencia.
- `e9_<escenario>_r<k>.{summary.json,decisions.json,timeline.csv}`: adaptación (A GPU, B solo CPU, C migración CPU→GPU), 3 repeticiones.
- `e4v2_S3-v2-gpu-sync_*`: E4 síncrono en GPU sin admisión en el borde (ablación y calibración del límite).
- `e4v2_S3c-v2-gpu-sync-edge_*`: E4 síncrono, v2 completa (admisión en el borde, N = 73).
- `e4v2_S4-v2-gpu-async_*`: E4 asíncrono (`/api/v1/jobs`); `_jobs.json` con los trabajos enviados, aceptados, procesados y fallidos (evidencia de C2.2).
- `e4v2_S3_aggregate.md`, `e4v2_gpu_aggregate.md`: medianas entre repeticiones (`aggregate_v2.py`).
- `e3v2_<arquitectura>_r<k>_slo.*`, `e3v2_gpu_report.md`: propuesta frente a monolito, ambos en cuda/fp32 (`compare_e3_v2.py`).
- `e2_gpu_report.md`: RTF, WER y CER sobre los 2111 clips.

En los `_slo.md`, la columna `users` muestra el máximo de usuarios activos en la ventana de cada escalón (por ejemplo, 30 o 60 en lugar de 10 o 50), porque al final de la ventana ya entran usuarios del escalón siguiente. Las medianas por escalón son 10, 50, 100, 200, 500 y 1000; los agregados usan esos valores.
