# Experimentos v2 — protocolo por dimensión

Complementa el protocolo del capítulo 5 (E1–E7) para evaluar la arquitectura v2 (`docs/09-arquitectura-v2.md`). Las dimensiones de calidad de reconocimiento (WER/CER) y usabilidad no cambian y quedan fuera de este documento. WER solo aparece en E8 como **control** de que una optimización no altera la salida.

Entorno nuevo: el equipo local con GPU **NVIDIA RTX A1000 de 8 GB** (Docker Desktop + WSL2). Esto permite medir lo que v1 dejó pendiente: la conmutación CPU/GPU (RQ1) y el rendimiento con aceleración.

## Diseño general: ablación sobre interruptores de configuración

Cada cambio v2 se activa con una variable de entorno, así que el efecto de cada decisión se aísla comparando configuraciones que difieren en un solo factor (diseño coherente con DSR: cada iteración prueba una hipótesis).

| Config | Descripción | Variables |
|---|---|---|
| **V1-CPU** | Réplica de v1 | `AUTH_MODE=remote RESTART_POLICY=on-failure FORCE_DEVICE=cpu FORCE_COMPUTE_TYPE=fp32 FORCE_BATCH_SIZE=1 MAX_QUEUE_DEPTH=100000 ADMISSION_MAX_WAIT_SECONDS=100000 JOB_WORKER_ENABLED=false` |
| **V2-CPU** | v2 completo sin GPU | defaults + `FORCE_DEVICE=cpu` |
| **V2-GPU** | v2 completo | defaults + `docker-compose.gpu.yml` |
| **V2-GPU-async** | v2 + carga por `/jobs` | V2-GPU con `E4_MODE=async` en Locust |

## Disponibilidad — E6 v2 (`experiments/e6_fault_injection/run_scenario.py`)

Un solo comando orquesta la carga constante, el fallo y las métricas.

| Escenario | Contenedor | Modo | Carga | Pregunta |
|---|---|---|---|---|
| D1 | asr-service | `crash` | sync | ¿Se recupera solo y en cuánto tiempo (MTTR)? ¿Cuántas solicitudes fallan **de verdad**? |
| D2 | auth-service | `crash` | sync | ¿Desaparece el punto único de fallo con `AUTH_MODE=local`? (comparar con `AUTH_MODE=remote`) |
| D3 | transcription-manager | `crash` | sync | ¿Sigue siendo no crítico con persistencia en segundo plano y reintentos? |
| D4 | asr-service | `crash` | **async** | ¿Se pierde algún trabajo? (*at-least-once*: debe ser 0) |
| D5 | redis | `crash` | sync | ¿La ruta síncrona y la autenticación sobreviven a la caída de Redis (*fail-open*)? |
| D6 | asr-service | `pause` | sync | Proceso vivo pero colgado: ¿los timeouts y `/ready` lo aíslan? |
| D7 | monolith-baseline | `crash` | sync | Línea base (`--host http://localhost:8006`) |

**Modo `crash`:** mata el proceso principal del contenedor con `SIGKILL` desde el espacio de PIDs del host de Docker (contenedor auxiliar privilegiado). Docker lo ve como una salida inesperada y aplica la política de reinicio, así que sí se puede medir el MTTR. `docker kill` y `docker stop` se tratan como paradas **manuales** y la política no se aplica. Ese fue el motivo por el que v1 no pudo observar la recuperación, y la primera prueba de humo de v2 repitió el mismo problema con `kill`.

Las ventanas antes, durante y después se asignan por **instante de finalización** de cada solicitud: las solicitudes en vuelo que mueren con el fallo cuentan como fallos "durante".

Métricas por escenario (`results/e6v2_<escenario>.summary.json`): tasa de éxito antes, durante y después del corte; fallos por código; tiempo de detección; **MTTR**; propagación a vecinos; `jobs_lost` en modo async.

Criterios:

| Código | Criterio | Estado en v1 |
|---|---|---|
| C1.1 | Éxito ante la caída de un servicio > monolito, y ninguna caída afecta al 100 % | Cumplido, pero la medición de asr-service estaba inflada (ver docs/09 §1.2) |
| C1.2 | Detección ≤ 5 s | Cumplido |
| C1.3 | Sin propagación a vecinos | Cumplido |
| C1.4 | Éxito ≥ 95 % bajo carga **dentro de la capacidad SLO** (ver E4 v2) | No cumplido |
| **C1.5 (nuevo)** | MTTR ≤ 30 s tras `SIGKILL` con política de reinicio | No medible en v1 |
| **C1.6 (nuevo)** | 0 trabajos perdidos ante la caída del worker (async) | — |
| **C1.7 (nuevo)** | Caída de auth-service con `AUTH_MODE=local`: éxito ≥ 95 % en `/transcribe` | 34.7 % en v1 |

## Escalabilidad — E4 v2 (`locustfile.py` + `slo_report.py`)

Cambios de medición:

1. **Validación del cuerpo**: un 200 sin `transcription_id` cuenta como fallo.
2. **Capacidad por SLO**: el mayor escalón con p95 ≤ 10 s y error ≤ 5 %. Reemplaza "usuarios sostenidos", que no indica si esos usuarios estaban siendo atendidos.
3. **Desglose de fallos**: rechazos rápidos (429/503, control de admisión funcionando) frente a timeouts (504) frente a 401.
4. **Ley de Little**: `N_max = X_max × (R_slo + Z)` da el techo analítico de usuarios para el throughput medido. Sirve para discutir C2.2: si 1000 > N_max, ninguna arquitectura lo alcanza con ese hardware en modo síncrono.
5. **Modo async**: `job_e2e` es el tiempo de extremo a extremo de un trabajo (envío → `done`).

Corridas (rampa 10→50→100→200→500→1000, escalones de 180 s; o más corta con `E4_STEPS`):

| Corrida | Config | Objetivo |
|---|---|---|
| S1 | V1-CPU, sync | Réplica local de v1 (referencia) |
| S2 | V2-CPU, sync | Efecto de los cambios de software sin hardware nuevo |
| S3 | V2-GPU, sync | Efecto de la GPU con *batching* |
| S4 | V2-GPU, async | Efecto del modelo asíncrono |
| S5 | Azure (opcional) | v2 con `aca/asr-worker.yaml` + KEDA |

Repetir cada corrida local **3 veces**: es gratis en local y cierra la limitación de "una sola ejecución" de E4 v1.

Criterios:

| Código | Criterio |
|---|---|
| C2.1 | La capacidad SLO de v2 supera a la de V1-CPU (S3 > S1, S4 > S1) |
| C2.2 | 1000 usuarios: en async, ≥ 99 % de los envíos aceptados y el 100 % de los trabajos aceptados completados. En sync, se reporta la comparación con `N_max` de Little |
| C2.3 | La adaptación registra ≥ 1 decisión aplicada bajo presión de carga (E9) |

## Rendimiento — E8 (`experiments/e8_inference_throughput/`) + E3 v2

**E8** mide el throughput de inferencia aislado (directo a `asr-service:8004`) con concurrencia de 1 a 32 en una matriz de configuraciones:

| Etiqueta | `FORCE_DEVICE` | `FORCE_COMPUTE_TYPE` | `FORCE_BATCH_SIZE` |
|---|---|---|---|
| `cpu-fp32-b1` (base) | cpu | fp32 | 1 |
| `cpu-int8-b1` | cpu | int8 | 1 |
| `cuda-fp32-b1` | cuda | fp32 | 1 |
| `cuda-fp16-b1` | cuda | fp16 | 1 |
| `cuda-fp16-b4` | cuda | fp16 | 4 |
| `cuda-fp16-b8` | cuda | fp16 | 8 |
| `cuda-fp16-b16` | cuda | fp16 | 16 |

Todas con `ADAPTIVE_MODE=false`. Métricas: req/s, **segundos de audio por segundo**, p50/p95 por nivel de concurrencia, aceleración frente a la base, histograma de *batch* logrado y control de WER (con `--manifest`).

**E3 v2:** la misma rampa de E3 contra la propuesta y contra el monolito, **ambos con GPU** (`docker-compose.gpu.yml` también aplica al monolito), con la validación de cuerpo activa.

Criterios:

| Código | Criterio |
|---|---|
| C3.1 | RTF mediano < 1 (en GPU se espera un valor muy inferior al 0.149 de CPU) |
| C3.2 | p50 ≤ 10 s con carga baja |
| C3.3 | La propuesta no es significativamente más lenta que el monolito (p50/p95/p99) |
| **C3.4 (nuevo)** | `cuda-fp16-b8` ≥ 5× el throughput de `cpu-fp32-b1`, con WER de control sin diferencia material |

## Adaptación — E9 (`experiments/e9_adaptation/observe.py`)

Perfil: reposo 30 s → ráfaga 120 s (24 concurrentes) → reposo 90 s. Se sondea `/status/adaptation` cada segundo.

| Escenario | Configuración | Comportamiento esperado |
|---|---|---|
| A | GPU, `ADAPTIVE_MODE=true` | En reposo fp32/batch 8; bajo ráfaga fp16/batch 16; vuelve al terminar |
| B | `FORCE_DEVICE=cpu` | fp32 → int8 bajo ráfaga; si int8 no es más rápido en ese host, **reversión** tras el periodo de prueba (decisión `rollback` registrada) |
| C (RQ1) | `DEVICE=cpu`, `ADAPTIVE_MODE=true`, GPU disponible | Migra a cuda en ~15 s sin interrumpir inferencias |

Métricas: decisiones aplicadas por eje, tiempo de reacción, reversión, decisiones de periodo de prueba y reversión, y throughput y latencia antes y después de la primera decisión. Cumple C2.3 si se aplica ≥ 1 decisión.

**C2.4 (nuevo):** ninguna adaptación que empeore el costo por clip permanece activa más allá de su periodo de prueba (toda degradación más lenta termina en `rollback`).

## Ejecución

```bash
cd experiments
python run_v2_suite.py --help        # orquesta E8, E9, E4, E6 por configuración
```

Ver `docs/08-como-correr-experimentos.md` para los prerrequisitos (ffmpeg, usuarios sembrados, pila sana).
