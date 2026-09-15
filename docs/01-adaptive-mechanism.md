# Fase 1 — Mecanismo de adaptación de recursos en tiempo de ejecución

## Qué problema resuelve

La afirmación científica central del trabajo es que la separación de responsabilidades en microservicios, **acoplada a adaptación de recursos en tiempo de ejecución**, permite operacionalizar modelos ASR E2E masivos bajo restricciones de bajos recursos. Antes de esta fase, `asr-service` no tenía ningún mecanismo de adaptación: `DEVICE` era una variable de entorno estática leída una sola vez al arrancar el proceso (`services/asr-service/app/core/config.py`). No existía detección de hardware, no existía reacción a presión de carga, y el `E3` del protocolo experimental exige comparar la arquitectura propuesta —con "conmutación CPU/GPU dinámica"— contra un baseline monolítico de dispositivo fijo. Sin este mecanismo, esa comparación no tendría nada real que medir.

## Diseño

Un monitor en background (`asyncio.Task`, arrancado desde el `lifespan` de `app/main.py`) sondea el hardware cada `adaptation_check_interval_seconds` (default 20s) y decide sobre dos ejes independientes:

- **Dispositivo** (`cpu`/`cuda`) — grueso y poco frecuente. Migra el modelo completo de acelerador cuando cambia la presión de VRAM.
- **Precisión de cómputo** (`fp32`/`fp16`/`int8`) — más frecuente. En CPU, bajo presión de CPU, cuantiza dinámicamente a `int8` (`torch.quantization.quantize_dynamic`, sin dependencia nueva); en GPU, bajo presión de VRAM, castea a `fp16`.

**Por qué existe el eje de precisión y no solo dispositivo**: producción (Azure Container Apps, Consumption plan) no tiene GPU. Si el mecanismo solo pudiera cambiar CPU↔GPU, sería un no-op permanente en el entorno real desplegado — la tesis quedaría sin evidencia empírica de adaptación donde más importa. El eje de precisión garantiza que el sistema sigue tomando decisiones reales de adaptación incluso sin GPU disponible.

**Histéresis y cooldown**: una sola lectura de CPU alta no dispara un swap — se exige que la misma decisión se repita en `adaptation_hysteresis_checks` (default 3) sondeos consecutivos, y además que hayan pasado al menos `adaptation_cooldown_seconds` (default 60) desde el último swap real. Esto evita "thrashing" (cambiar de estado constantemente por ruido de una métrica puntual).

**Construcción antes de intercambiar** (`services/asr-service/app/services/whisper_service.py::reload_model`): el nuevo pipeline se construye completo en un hilo aparte (`run_in_executor`, fuera del camino caliente de requests) y solo cuando termina exitosamente se reemplaza el puntero global `_pipe` bajo un `threading.Lock` de sección crítica mínima (solo la reasignación, nunca la construcción). Cualquier inferencia en curso ya capturó su propia referencia al pipe (`_run_whisper` hace `with _swap_lock: pipe = _pipe` al inicio) y no se ve afectada por un swap concurrente.

## Controlabilidad para experimentos limpios

`adaptive_mode`, `force_device`, `force_compute_type` (config + env vars `ADAPTIVE_MODE`/`FORCE_DEVICE`/`FORCE_COMPUTE_TYPE` en `docker-compose.yml`). Cuando algo está forzado, el monitor sigue corriendo y sigue registrando qué habría decidido la política natural — solo omite aplicarlo. Esto le permite a **E2** recolectar muestras limpias solo-CPU y solo-GPU, mientras la política sigue demostrando que razona correctamente incluso en corridas forzadas.

## Observabilidad (evidencia citable para E2/E3)

- `GET /status/adaptation` — dispositivo/precisión actuales, snapshot de hardware, inferencias en curso, e historial de las últimas 200 decisiones (`timestamp`, `previous_*`, `new_*`, `reason`, `changed`, `forced`).
- Cada decisión también se loguea como una línea JSON estructurada (`{"event": "adaptation_decision", ...}`) — rastro barato y "greppeable" para el apéndice de la tesis.
- `/health` ahora incluye `device`/`compute_type` en su bloque `checks`.
- **Cada transcripción queda marcada** con `device_used`/`compute_type` — tanto en la respuesta HTTP (`TranscribeResponse`, `FinalResultMessage`) como persistida en la fila de `transcriptions` (nuevas columnas en transcription-manager). Esto permite que el reporte de E2 (RTF por dispositivo) consulte directamente la base de datos, sin correlacionar timestamps de logs.

## Bug corregido de paso

`whisper_service.transcribe()` mandaba la clave `word_confidences` al POST hacia transcription-manager, pero `CreateTranscriptionRequest` esperaba `confidence_scores` — pydantic descartaba el campo silenciosamente y las confianzas por palabra nunca se persistían. Corregido en el mismo archivo que ya se estaba tocando.

## Archivos

- `services/asr-service/requirements.txt` — pin de `torch`/`soundfile`, agregado `psutil`.
- `services/asr-service/app/core/config.py` — nuevas variables de adaptación.
- `services/asr-service/app/services/device_manager.py` (nuevo) — `probe_hardware()`, `evaluate_policy()`, `DeviceManager` (loop, histéresis, cooldown, historial).
- `services/asr-service/app/services/whisper_service.py` — `load_model(device, compute_type)`, `reload_model()`, `get_current_device()`/`get_current_compute_type()`, stamping de `device_used`/`compute_type`, fix del bug de `confidence_scores`.
- `services/asr-service/app/schemas/transcription.py` — `device_used`/`compute_type` en `TranscribeResponse` y `FinalResultMessage`.
- `services/asr-service/app/services/streaming_service.py` — propaga los campos nuevos al finalizar streaming.
- `services/asr-service/app/main.py` — arranca/detiene el monitor; nuevo endpoint `/status/adaptation`.
- `services/transcription-manager/app/models/transcription.py` + `app/schemas/transcription.py` + `app/services/transcription_service.py` + `app/db/repositories/transcription_repo.py` — columnas y wiring de `device_used`/`compute_type`.
- `services/transcription-manager/alembic/versions/e5f6a1b2c3d4_add_device_columns.py` (nuevo) — migración.
- `docker-compose.yml`, `aca/asr-service.yaml` — variables de entorno nuevas.

## Verificación realizada

Se corrió un smoke test standalone (fuera de Docker, con `psutil`/`pydantic-settings`/`fastapi`/`httpx` instalados localmente) que ejercita `evaluate_policy()` puro con 6 escenarios (sin GPU/CPU baja, sin GPU/CPU alta, GPU con margen, GPU con presión de VRAM, `force_device`, `force_compute_type`) y el ciclo completo de `DeviceManager._tick()` con un `whisper_service` simulado, confirmando:

- La política pura decide correctamente en los 6 escenarios.
- La histéresis exige exactamente 3 sondeos consecutivos con la misma decisión antes de aplicar un swap (0 llamadas a `reload_model` en los primeros 2 ticks, 1 llamada en el tercero).
- La decisión queda registrada en el historial con `changed=True`.

**Pendiente** (requiere Docker): levantar `asr-service` real, confirmar `GET /status/adaptation` responde con snapshot de hardware real, inducir presión de CPU artificialmente y confirmar un swap real a `int8`, y verificar que `device_used`/`compute_type` llegan a la fila de `transcriptions` en Postgres. Ver sección "Verification" del plan (`C:\Users\DIRORE\.claude\plans\warm-kindling-canyon.md`).
