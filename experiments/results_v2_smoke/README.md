# Evidencia de las pruebas de humo v2 (2026-10-03)

Resúmenes de las corridas descritas en `docs/11-resultados-v2-preliminares.md`.
Clip sintético de 24.7 s, corridas cortas, una ejecución. No son resultados
finales. Los CSV crudos no se versionan (`experiments/results/` está en `.gitignore`).

- `e8_*`: throughput de inferencia (CPU fp32/int8, CUDA fp16 batch 8).
- `e9_*`: adaptación (A GPU, B CPU con reversión, C migración CPU→GPU).
- `e6v2_D1-asr-crash.summary.json`: caída real de asr-service (MTTR 4.9 s).
- `e6_first_smoke_docker_kill/`: primera corrida de E6, con `docker kill`
  (sin reinicio, ventanas por inicio de solicitud). Solo es indicativa.
