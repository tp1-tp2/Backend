# Resumen de la sesión del 2026-10-03 (arquitectura v2)

Registro compacto de la conversación de trabajo que dio origen a la arquitectura v2. El detalle de cada tema está en los documentos enlazados.

## 1. Pedido inicial y diagnóstico

**Pedido:** evaluar los experimentos del capítulo 5 (`cap-5-extracted.md`, `docs/07`) y proponer mejoras de arquitectura y backend por dimensión, excepto calidad de reconocimiento (WER/CER) y usabilidad. Prioridad: escalabilidad, rendimiento y disponibilidad. Ahora hay una GPU de 8 GB.

**Diagnóstico:**
- El colapso en E4 no se debe solo a la capacidad de cómputo: la cadena de cuatro servicios era **síncrona** (timeouts de 300 s) y **no tenía control de admisión**. El sistema "admitía más y fallaba después" (p99 de 149 s en la ronda 4).
- C2.2 (1000 usuarios) es inalcanzable en modo síncrono para una sola GPU. Por la ley de Little, `N = X·(R+Z)` exige unas 83 req/s con R ≤ 10 s y Z ≈ 2 s.
- `auth-service` era un punto único de fallo (validación remota del token en cada solicitud), y sus 5xx se reportaban como 401.
- La adaptación vertical no reaccionaba nunca porque su señal era el % de CPU, mientras que la saturación se manifestaba como encolamiento.

**Propuestas presentadas** (resumen): JWT local en el gateway; 503 en lugar de 401; control de admisión y `/ready`; modelo asíncrono con cola; escalado por longitud de cola (KEDA); worker GPU híbrido; GPU con *batching*; prioridades en el streaming; Opus por defecto; persistencia fuera del camino de respuesta; adaptación guiada por la cola; ajustes de metodología (capacidad por SLO, repeticiones, ablación).

## 2. Implementación ("actualiza los experimentos según cada dimensión e impleméntalos")

Diseño completo en `docs/09-arquitectura-v2.md`. Resumen:

| Dimensión | Cambios |
|---|---|
| Disponibilidad | `AUTH_MODE=local` (JWT verificado en el gateway + revocaciones en Redis, *fail-open* configurable); 5xx de auth → 503 + `Retry-After`; audio-processor propaga los errores de ASR; reintento solo ante errores de conexión; presupuesto de timeouts 120 > 110 > 100 s; `/ready` separado de `/health`; `restart: unless-stopped` |
| Escalabilidad | `POST/GET /api/v1/jobs` sobre Redis Streams con entrega *at-least-once* (*heartbeat*, `XAUTOCLAIM`, idempotencia); manifiestos ACA `redis.yaml` y `asr-worker.yaml` (KEDA por backlog, 0–10 réplicas); `docker-compose.worker.yml` (worker GPU híbrido) |
| Rendimiento | `docker-compose.gpu.yml`; scheduler de inferencia con *micro-batching*, prioridades (final de streaming > REST > trabajo > parcial), control de admisión y división del *batch* ante OOM; persistencia en segundo plano; clientes HTTP compartidos; pools de BD acotados; remuestreo propio a 16 kHz |
| Adaptación | Política guiada por la profundidad de la cola; tercer eje (tamaño de *batch*); *fallback* a CPU ante OOM; fijación por eje; **verificación con periodo de prueba y reversión** |

**Experimentos v2** (protocolo en `docs/10-experimentos-v2.md`):
- E4 v2: locustfile con validación del cuerpo, modo async y CSV crudo, más `slo_report.py` (capacidad por SLO y cota de Little).
- E6 v2: `run_scenario.py`, con modos `crash`/`stop`/`kill`/`pause`, MTTR y trabajos perdidos.
- E8: throughput de inferencia por dispositivo × precisión × *batch* × concurrencia, con control de WER.
- E9: adaptación ante una ráfaga de carga.
- `run_v2_suite.py` orquesta todas las fases.

**Tests:** gateway 68, auth 34, audio-processor 24 y asr-service 42; todos pasan en contenedor con Python 3.11.

## 3. Problemas encontrados durante la sesión

- **Amenaza a la validez de v1:** con asr-service caído, audio-processor respondía `200` sin transcripción y Locust lo contaba como éxito. El 100 % reportado en E6 v1 estaba inflado. Corregido en el backend y en el cliente de carga.
- **int8 es 2× más lento que fp32** en la CPU de evaluación. Esto motivó la adaptación verificada: una degradación que no acelera se revierte y queda rechazada en ese host.
- Fijar `FORCE_DEVICE` congelaba todo el mecanismo de adaptación. Ahora la fijación es por eje.
- `docker kill` y `docker stop` cuentan como paradas manuales y Docker no aplica la política de reinicio. Por eso E6 usa el modo `crash`: SIGKILL del proceso desde el espacio de PIDs del host.
- Las ventanas de E6 pasaron a asignarse por finalización de la solicitud. En modo async se añadió `--stop-timeout` para no cortar trabajos en curso.
- En este equipo el puerto 8000 está ocupado por un proceso del sistema, así que el gateway se publica en el 8080 (`GATEWAY_PORT`).
- El equipo solo tiene Python 3.14; el entorno de experimentos usa versiones sin pin.
- El corpus no está en este equipo. Las pruebas usaron un clip TTS de 24.7 s.

## 4. Resultados preliminares (pruebas de humo)

Detalle en `docs/11-resultados-v2-preliminares.md`. Evidencia en `experiments/results_v2_smoke/`.

- **Extremo a extremo:** `/jobs` respondió 202 en 0.36 s y el trabajo terminó en 0.68 s en CUDA (RTF ≈ 0.03). La revocación por Redis funciona.
- **E8:** CUDA fp16 con *batch* 8 da **5.4×** el throughput de CPU fp32 (109 frente a 20 s de audio/s, hasta concurrencia 4).
- **E9:** C2.3 se cumple. A (GPU): fp16 superó el periodo de prueba. B (CPU): int8 revertido de forma automática. C: **migración CPU→GPU en caliente (primera evidencia de RQ1)**.
- **E6:** asr-service con caída real tuvo un **MTTR de 4.9 s**. Con auth-service caído y validación local, el éxito fue 100 %, frente a 0.5 % en modo remoto (v1).

## 5. Estado y siguientes pasos

Ver `docs/12-estado-y-pendientes.md`. Lo principal: traer el corpus, correr E6/E4/E8/E9/E3 completos con 3 repeticiones, desplegar v2 en Azure y actualizar el capítulo 5 con los criterios nuevos (C1.5–C1.7, C2.4, C3.4).

## 6. Commits de la sesión (rama `new-implementation`)

- `9ac7c61` feat: arquitectura v2 (disponibilidad, escalabilidad, rendimiento, adaptación)
- `ce99f21` feat(experiments): protocolo v2 por dimensión y pruebas de humo
- `9224def` docs: arquitectura v2, protocolo v2, resultados preliminares y pendientes
