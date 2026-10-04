# Fase 9 — Arquitectura v2: cambios guiados por los resultados de E3–E6

Esta fase convierte los hallazgos del capítulo 5 en cambios de diseño. Cada cambio responde a una evidencia concreta, se puede activar o desactivar por configuración (para medir su efecto aislado; ver `docs/10-experimentos-v2.md`) y deja los endpoints v1 intactos, de modo que E3 sigue siendo comparable.

| Hallazgo (v1) | Evidencia | Cambio v2 | Dimensión |
|---|---|---|---|
| `auth-service` es punto único de fallo | E6: su caída tumbó el 65.3 % de `/transcribe`; E4 ronda 3: 2652 errores 401 | Validación local del JWT en el gateway + espejo de revocaciones en Redis | Disponibilidad |
| Un 5xx de auth se reportaba como 401 | E4 ronda 3 | 5xx/429 → `503 + Retry-After`; solo una respuesta definitiva es 401 | Disponibilidad |
| Un fallo de ASR se devolvía como `200` sin transcripción | Revisión de código en esta fase | `audio-processor` propaga 503/504; el cliente de carga valida el cuerpo | Disponibilidad (validez de la medición) |
| "Admitir más y fallar después" | E4 ronda 4: p99 = 149 s | Control de admisión por espera estimada (503 rápido) + `/ready` separado de `/health` | Disponibilidad |
| La política `on-failure` no reinicia tras un `stop` | E6: recuperación no observable | `restart: unless-stopped`; E6 v2 usa `SIGKILL` y mide el MTTR | Disponibilidad |
| Cadena síncrona de 4 saltos con timeouts de 300 s | E4: colapso con error > 85 % | API asíncrona `POST /api/v1/jobs` (202) sobre Redis Streams + workers que extraen trabajos | Escalabilidad |
| Escalado por concurrencia HTTP | E4: 254 → 353 usuarios, con colapso | Escalado KEDA por backlog de la cola (`aca/asr-worker.yaml`), escala a cero | Escalabilidad |
| Inferencia de a una por vez en CPU | RTF 0.149, throughput 2.8 req/s | GPU + *micro-batching* con prioridades en `asr-service` | Rendimiento |
| Persistencia en el camino de respuesta | `await` al POST de transcription-manager | Persistencia en segundo plano con reintentos | Rendimiento |
| Un cliente HTTP nuevo por solicitud y salto | Código del gateway y de audio-processor | Pool *keep-alive* compartido por proceso | Rendimiento |
| La adaptación vertical no reaccionó nunca | E4: 0 decisiones en 4 rondas (C2.3) | La política se guía por la profundidad de la cola; tercer eje: tamaño de *batch*; *fallback* a CPU ante OOM | Adaptación |

## 1. Disponibilidad

### 1.1 Validación local del token (`services/api-gateway/app/core/token_validator.py`)

- `AUTH_MODE=local` (por defecto): el gateway verifica firma HS256 y expiración con la clave compartida y consulta `revoked:<sha256(token)>` en Redis. `auth-service` solo queda en el camino de login y registro.
- `auth-service` escribe cada revocación (logout, blocklist) en la base de datos, que sigue siendo la fuente de verdad, **y** la replica en Redis con TTL igual a la vida restante del token (`app/core/revocation.py`). La escritura en Redis es *best-effort*.
- **Compromiso explícito (CAP):** si Redis no responde, `REVOCATION_FAIL_OPEN=true` (por defecto) acepta tokens firmados y vigentes. Durante esa ventana, un token revocado podría seguir funcionando hasta su `exp`. `false` falla cerrado (503). Se prioriza la disponibilidad del servicio de transcripción; la elección se documenta y se puede medir.
- `AUTH_MODE=remote` reproduce exactamente el comportamiento v1, para el estudio de ablación.
- El WebSocket de `asr-service` también valida el token localmente. Antes repetía la llamada a `auth-service` al abrir cada sesión.

### 1.2 Semántica de errores

| Situación | v1 | v2 |
|---|---|---|
| auth-service sobrecargado (5xx) | 401 | 503 + `Retry-After` |
| asr-service caído o sobrecargado | **200 con `transcription_id: null`** | 503 + `Retry-After` |
| Inferencia que excede el presupuesto | 504 tras ~300 s | 504 a los 100 s |
| Cola síncrona saturada | espera hasta el timeout | 503 inmediato (control de admisión) |
| Backlog de trabajos lleno | — | 429 + `Retry-After` |

**Amenaza a la validez de E6 v1:** con `asr-service` detenido, `audio-processor` atrapaba la excepción y respondía 200 sin transcripción, y Locust contaba esas respuestas como éxitos. Por eso el 100 % de éxito reportado para la caída de `asr-service` no es confiable y debe re-medirse con E6 v2. El monolito no tenía este problema (propaga el error), así que la comparación v1 favorecía a la arquitectura propuesta.

### 1.3 Presupuesto de timeouts

`gateway 120 s > audio-processor 110 s > asr-service 100 s`. El salto más interno vence primero, de modo que el error llega como un 504 limpio en lugar de que cada capa espere 300 s.

### 1.4 Vida, disponibilidad para tráfico y reinicio

- `/health` = *liveness*: el proceso vive. Nunca depende de la carga, para que una réplica ocupada no se reinicie por estar ocupada.
- `/ready` = *readiness*: modelo cargado y cola no saturada. En ACA se configura como sonda de *readiness* (`aca/asr-service.yaml`), así que una réplica saturada deja de recibir tráfico sin reiniciarse.
- `restart: unless-stopped` en todos los contenedores (`RESTART_POLICY` para reproducir v1).
- `audio-processor` reintenta solo los **errores de conexión** hacia ASR (2 reintentos con *backoff*). Esos fallos ocurren antes de llegar a una réplica, por lo que reintentarlos no duplica trabajo. Los timeouts no se reintentan.

## 2. Escalabilidad

### 2.1 API asíncrona (`POST /api/v1/jobs`, `GET /api/v1/jobs/{id}`)

```
cliente ──POST /jobs──▶ gateway ──▶ audio-processor ──XADD──▶ Redis Stream asr:jobs
   ▲                                   (valida, ffmpeg,          │  consumer group
   │ 202 {job_id}                       registra, encola)        ▼  asr-workers
   │                                                      asr-service (job_worker)
   └──GET /jobs/{id}── gateway ──HGETALL job:{id}◀── HSET done ── batching en GPU/CPU
```

- La respuesta `202` tarda lo que tarda ffmpeg, no lo que tarda la inferencia. Aceptar trabajo y procesarlo quedan desacoplados.
- **Pull, no push:** los workers extraen trabajos con `XREADGROUP`. Una réplica puede vivir en cualquier máquina que alcance Redis, por ejemplo una PC con GPU (`docker-compose.worker.yml`) sumada a un despliegue en la nube sin abrirle puertos de entrada (topología híbrida).
- El audio viaja en Redis (`job:{id}:audio`, con TTL), no en un volumen compartido. Eso es lo que permite workers en otra máquina.
- La lectura de estado la hace el gateway directamente en Redis (ruta de lectura estilo CQRS). El *polling* frecuente no toca `audio-processor` ni `asr-service`.

### 2.2 Entrega *at-least-once* (también es disponibilidad)

- El `XACK` se hace solo después de guardar el resultado y persistirlo.
- *Heartbeat*: mientras procesa, el worker reclama su propia entrada (`XCLAIM` a sí mismo), lo que reinicia su tiempo inactivo. Si el worker muere, la entrada queda inactiva y otro worker la reclama tras `JOB_CLAIM_IDLE_MS` (30 s) con `XAUTOCLAIM`.
- Idempotencia: un trabajo ya `done`/`failed` solo se confirma, y el `transcription_id` es el `job_id`, así que repersistir no duplica.
- Los fallos transitorios se reencolan hasta `JOB_MAX_ATTEMPTS` (3).

### 2.3 Escalado por cola (`aca/asr-worker.yaml`)

Escalador KEDA `redis-streams` sobre el *lag* del grupo de consumidores: una réplica por cada 8 trabajos sin entregar, de 0 a 10 réplicas. La señal mide directamente la demanda no atendida; la concurrencia HTTP (v1) no la ve en un worker basado en cola. Las réplicas `asr-service` síncronas quedan con `JOB_WORKER_ENABLED=false` y un máximo de 5 réplicas.

## 3. Rendimiento

### 3.1 Scheduler de inferencia (`services/asr-service/app/services/inference_scheduler.py`)

Una cola con prioridad delante del modelo y un único hilo de ejecución:

- **Micro-batching:** las solicitudes que llegan dentro de `BATCH_WINDOW_MS` (25 ms) se ejecutan en una sola pasada de hasta `max_batch_size` clips. Whisper rellena cada entrada corta a 30 s, así que en GPU un *batch* de N cuesta mucho menos que N pasadas. Los clips de más de 30 s se procesan solos (decodificación larga secuencial).
- **Prioridades:** final de streaming > REST > trabajo en cola > parcial. Los parciales se descartan si la cola tiene ≥ `PARTIAL_SHED_DEPTH`. E5 mostró que retrasaban el final PCM (11.56 s frente a 5.34 s con Opus).
- **Control de admisión:** rechaza con 503 si `profundidad ≥ MAX_QUEUE_DEPTH` o si la espera estimada (`(profundidad + en curso) × EWMA del costo por clip`) supera `ADMISSION_MAX_WAIT_SECONDS`. Los trabajos y los finales de streaming no pasan por admisión: la cola es su control.
- **OOM de CUDA:** el *batch* se divide en mitades y se reintenta; el evento alimenta la política de adaptación.
- Un caller que vence su timeout mientras espera nunca consume tiempo del modelo: su entrada se descarta al salir de la cola.

### 3.2 GPU

`docker-compose.gpu.yml` expone la GPU a `asr-service` y al monolito (comparación simétrica). No hace falta una imagen distinta: `torch==2.4.1` desde PyPI en linux/x86_64 ya incluye el runtime CUDA 12.1.

### 3.3 Remuestreo propio

`_load_audio` remuestrea a 16 kHz con `scipy.signal.resample_poly`. El pipeline de transformers exige `torchaudio` para remuestrear, que era la causa del cuelgue de E5 con Opus a 48 kHz y también afectaba a cualquier streaming PCM a 48 kHz.

## 4. Adaptación en tiempo de ejecución (C2.3)

`device_manager.evaluate_policy` ahora decide sobre tres ejes con señal de cola:

| Condición | CPU | GPU |
|---|---|---|
| Sin presión | fp32, batch 1 | fp32, batch `BATCH_SIZE_GPU` (8) |
| Profundidad de cola ≥ `QUEUE_PRESSURE_DEPTH` (4) | int8 | fp16, batch `MAX_BATCH_SIZE` (16) |
| CPU% ≥ 85 | int8 | — |
| VRAM libre < 2 × reserva | — | fp16 |
| VRAM libre < reserva | migra a CPU | — |
| OOM reciente | — | batch ÷ 2ⁿ |
| ≥ 3 OOM en 120 s | migra a CPU | — |

- Dispositivo y precisión requieren reconstruir el modelo, así que pasan por histéresis (3 sondeos) y *cooldown*. Ambos se acortaron de 20 s/60 s a 5 s/30 s porque con escalones de 180 s el mecanismo v1 tardaba unos 2 minutos en poder reaccionar.
- El tamaño de *batch* no reconstruye nada: se aplica en cada sondeo.
- **Adaptación verificada (con periodo de prueba y reversión).** El scheduler mide el costo real del modelo por clip en cada estado `dispositivo/precisión`. Una degradación de precisión hecha para ganar velocidad (fp32 → fp16/int8) entra en un periodo de prueba de `ADAPTATION_PROBATION_ITEMS` (5) clips. Si no resulta al menos `ADAPTATION_MIN_GAIN` (5 %) más barata que el estado anterior, se **revierte** y ese estado queda rechazado en ese host (`rejected_states` en `/status/adaptation`). Si ya hay mediciones de ambos estados, la degradación ni se intenta. Motivo: en la CPU de evaluación, la cuantización dinámica int8 resultó **2× más lenta** que fp32 (E8: 9.3 frente a 20.0 s de audio/s). La regla v1 "bajo presión, int8" empeoraba el sistema. En la prueba de humo de E9, el mecanismo pasó a int8, midió 2.54 s/clip frente a 1.34 s/clip y revirtió a los 15.7 s. En GPU, fp16 superó la prueba (0.180 frente a 0.217 s/clip) y se mantuvo.
- Toda decisión queda en `GET /status/adaptation`, con el tamaño de *batch* y la profundidad de cola que la motivaron.
- `FORCE_DEVICE`, `FORCE_COMPUTE_TYPE` y `FORCE_BATCH_SIZE` fijan **un eje cada uno**; los demás siguen adaptándose (con `FORCE_DEVICE=cpu`, la precisión aún puede pasar a int8). Solo con dispositivo y precisión fijados a la vez el monitor queda en modo observación. En E8 además se usa `ADAPTIVE_MODE=false`. En v1, fijar cualquier eje congelaba todo el mecanismo; la prueba de humo de E9 lo detectó (escenario B: 0 decisiones aplicadas pese a 16 decisiones de int8 tomadas por la política).

## 5. Observabilidad nueva

- `GET /status/scheduler` (asr-service): profundidad, en curso, histograma de tamaños de *batch*, rechazos, parciales descartados, eventos OOM, EWMA del costo por clip y de la espera, y contadores del worker (procesados, reintentos, reclamados, duplicados).
- `GET /ready` en gateway y asr-service.
- Campos de cada trabajo: `queue_wait_s`, `processing_s`, `total_s`, `worker`, `attempts`.

## 6. Interruptores de configuración (para la ablación)

| Variable | v1 | v2 (por defecto) |
|---|---|---|
| `AUTH_MODE` | `remote` | `local` |
| `RESTART_POLICY` | `on-failure` | `unless-stopped` |
| `FORCE_BATCH_SIZE` | `1` | vacío (adaptativo) |
| `DEVICE` / override GPU | `cpu` | `cuda` con `docker-compose.gpu.yml` |
| `MAX_QUEUE_DEPTH` / `ADMISSION_MAX_WAIT_SECONDS` | sin límite (valores muy altos) | 64 / 60 s |
| `JOB_WORKER_ENABLED` | — | `true` |
| `ADAPTIVE_MODE` | `true` (señal CPU%) | `true` (señal de cola) |

## 7. Limitaciones y riesgos introducidos

- **Redis es una dependencia nueva.** No es fuente de verdad de nada durable, pero su caída detiene la ruta asíncrona (los `POST /jobs` reciben 503). Con *fail-open* no afecta la ruta síncrona ni la autenticación. Se mide explícitamente en E6 v2. Para producción conviene Azure Cache for Redis gestionado.
- Revocación con consistencia eventual durante una caída de Redis (ver 1.1).
- *Batching* y fp16 pueden cambiar levemente la salida numérica. E8 incluye un control de WER por configuración para demostrar que la salida se preserva; no es una evaluación de calidad.
- KEDA `redis-streams` con `lagCount` requiere Redis ≥ 7 y una versión de KEDA compatible en ACA. Hay que verificarlo en el despliegue real.
