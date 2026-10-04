# Optimización de la inferencia en CPU (2026-10-04)

Continuación de la arquitectura v2 (`docs/09`) en un equipo **sin GPU NVIDIA**. Todo lo que depende de CUDA (C3.4, escenarios E9 A y C, E4 S3/S4) queda pendiente para el equipo con la RTX A1000; este documento cubre lo que se puede medir y mejorar solo con CPU.

## Entorno de evaluación

| Atributo | Valor |
|---|---|
| CPU | Intel Core i5-10400 (6 núcleos, 12 hilos, 2.9 GHz) |
| RAM | 23.8 GB (16 GB asignados a WSL2/Docker) |
| GPU | Intel UHD Graphics 630 integrada: **no utilizable** (sin CUDA; PyTorch XPU no la soporta; los "11.9 GB" del Administrador de tareas son memoria compartida tomada de la RAM) |
| Docker | Docker Desktop + WSL2, 12 CPU y 16 GB (`.wslconfig` subido desde 4 CPU / 12 GB) |
| Corpus | `E:\IWSLT2026_Quechua_data` (2111 clips, manifiesto regenerado) |
| Clip de carga | `quechua_03068.wav`, Huqariq, 24.05 s (mediana del corpus: 23.04 s) |

## Problema

En CPU la plataforma v2 tenía un único estado de inferencia útil: el pipeline de transformers en fp32 con una sola línea de ejecución. La cuantización dinámica int8 de PyTorch fue 2× más lenta en el equipo de ayer, y el *micro-batching* no ayuda en CPU. La capacidad por réplica (≈ 7 s de audio por segundo) limita directamente la escalabilidad: por la ley de Little, el techo de usuarios es proporcional al throughput.

## Cambio: motor CTranslate2 con líneas de inferencia paralelas

| Componente | Cambio |
|---|---|
| `asr-service/app/services/ct2_engine.py` | Motor `ENGINE=ctranslate2` (faster-whisper 1.0.3, ctranslate2 4.6.0) con los **mismos pesos** del modelo ajustado, convertidos al construir la imagen. fp32/int8 se aplican al cargar, así que una conversión sirve para todos los estados de la adaptación. |
| Decodificación | Igual que la ruta de transformers: *greedy*, token de idioma `spanish`, `no_repeat_ngram_size=3`, sin condicionar en el texto previo y sin descartar segmentos por silencio. Para clips de 30 s o menos se hace **una sola pasada sobre la ventana**, como el pipeline. `transcribe()` de faster-whisper vuelve a decodificar la cola de la ventana y alucinaba continuaciones (un clip pasó de WER 0.13 a 2.67). |
| `inference_scheduler.py` | De una línea de ejecución a **N líneas** (`INFERENCE_LANES`): N lotes en paralelo, el orden de prioridad se conserva en la cola y la espera estimada para la admisión se divide entre N. Con transformers se fuerza 1 línea, porque el pipeline no es seguro entre hilos. |
| `CT2_CPU_THREADS` | Hilos por línea. Usar los 12 hilos lógicos en una sola línea fue **5× más lento** (RTF 0.67) que usar 6: el *hyperthreading* perjudica a CTranslate2. |
| Monolito | Misma opción de motor (`MONOLITH_ENGINE`, `MONOLITH_LANES`), para que E3 compare **arquitecturas y no motores**. |
| `run_v2_suite.py --cpu-only` | Matriz E8 de CPU, E9-B con ambos motores, E4 S1/S2/S2b, E6 y E3 con la configuración v2 de este equipo. |

Tests: asr-service **44** (los 42 de v2 y 2 nuevos: líneas en paralelo con prioridad, y una sola línea forzada con transformers).

## Resultados E8 en CPU (directo a asr-service, muestra estratificada de 30 clips, 45 s por nivel)

Throughput en **segundos de audio procesados por segundo**, con la latencia por solicitud (p50/p95, en segundos) por nivel de concurrencia:

| Configuración | c = 1 | c = 2 | c = 4 | c = 8 | c = 16 | Pico | × base |
|---|---|---|---|---|---|---|---|
| transformers fp32 (base, v1) | 7.1 (2.06/4.95) | 7.0 | 6.1 | 5.3 | 5.0 (38.4/47.7) | 7.1 | 1.00 |
| transformers int8 | 9.8 (1.72/3.75) | 9.4 | 8.8 | 7.7 | 8.1 | 9.8 | 1.39 |
| CTranslate2 fp32, 1 línea × 6 hilos | 8.3 | 8.0 | 7.4 | 6.7 | 6.2 | 8.3 | 1.17 |
| CTranslate2 fp32, 3 × 2 | 7.5 | 9.6 | 9.9 | 8.5 | 7.9 | 9.9 | 1.40 |
| CTranslate2 int8, 1 × 6 | 13.5 (1.14/2.21) | 13.8 | 12.2 | 11.9 | 10.3 | 13.8 | 1.95 |
| CTranslate2 int8, 2 × 3 | 12.5 | 17.4 | 15.8 | 15.0 | 14.5 | 17.4 | 2.45 |
| **CTranslate2 int8, 3 × 2 (elegida)** | 11.9 (1.49/2.42) | 18.1 (1.81/3.41) | **19.4** (3.50/5.01) | 17.5 (7.32/9.20) | 16.3 (14.2/17.5) | **19.4** | **2.74** |
| CTranslate2 int8, 4 × 3 | 13.6 | 18.0 | 18.5 | 17.3 | 16.1 | 18.5 | 2.60 |
| CTranslate2 int8, 6 × 1 | 8.0 | 13.7 | 19.6 | 18.9 | 17.3 | 19.6 | 2.76 |

- **2.7× el throughput de la base sin GPU.** Con 16 clientes simultáneos, el p95 baja de 47.7 s a 17.5 s.
- Se eligió **3 × 2** en lugar de 6 × 1 (pico equivalente) porque responde mejor con poca carga (p50 1.49 s frente a 2.11 s con 1 cliente).
- En este CPU el int8 de PyTorch **sí acelera** (1.39×), al contrario que en el equipo de ayer (0.5×). La misma política de adaptación da resultados distintos según el host, y por eso la adaptación se **verifica midiendo** (periodo de prueba, C2.4) en lugar de suponerse.

### Control de WER (paridad de motores, `engine_parity.py`, 30 clips, una solicitud a la vez)

| Motor / precisión | RTF mediano | WER medio | CER medio | Salida idéntica a transformers fp32 | Wilcoxon frente a transformers fp32 |
|---|---|---|---|---|---|
| transformers fp32 | 0.135 | 0.735 | 0.261 | 30/30 | — |
| transformers int8 | 0.102 | 0.732 | 0.276 | 2/30 | p = 0.65 |
| CTranslate2 fp32 (6 hilos) | 0.110 | 0.763 | 0.263 | 27/30 | p = 0.11 |
| CTranslate2 int8 (6 hilos) | **0.069** | 0.766 | 0.271 | 10/30 | p = 0.22 |

Ninguna diferencia es significativa y la mediana de WER es la misma (0.75). Las 3 salidas distintas en fp32 son clips de exactamente 30 s: en una decisión casi empatada después de un *timestamp*, transformers emite fin de secuencia y CTranslate2 continúa. **Pendiente:** confirmar el control sobre el corpus completo (2111 clips).

## Configuración v2 de este equipo

`ENGINE=ctranslate2 INFERENCE_LANES=3 CT2_CPU_THREADS=2 FORCE_DEVICE=cpu`, con adaptación activa: parte en fp32 y pasa a int8 bajo presión de cola, con periodo de prueba.

```bash
cd experiments
run_cpu_suite.cmd e9 e6 e4 e3     # proceso independiente; log en results/log_suite_cpu.txt
```
