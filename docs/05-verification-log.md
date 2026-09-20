# Fase 5 — Log de verificación

Verificación completa contra Docker real (`docker compose up --build`), no solo compilación de sintaxis. Todo lo que sigue se corrió de verdad y se confirmó funcionando el 2026-09-20.

## Bugs reales encontrados y corregidos durante la verificación

Ninguno de estos era detectable con `python -m py_compile` — solo aparecieron al correr la pila completa:

1. **`transformers`/`torch` incompatibles** — `transformers>=4.40.0` (sin pinear) resolvía a la 5.17.0, que requiere `torch>=2.5`. Con `torch==2.4.1` pineado (Fase 1), `transformers` desactivaba PyTorch silenciosamente y el modelo Whisper **nunca cargaba** en `asr-service` ni en `monolith-baseline` (`ERROR: Whisper model failed to load: PyTorch should be installed`). Corregido pineando `transformers==4.44.2` / `accelerate==0.33.0` en ambos servicios — versión estable conocida, compatible con `torch==2.4.1`, evitando además el riesgo de que un salto de versión mayor (4.x→5.x) cambie el comportamiento de generación justo en el pipeline cuyo output mide E2.
2. **`experiments/common/asr_client.py::register()`** asumía HTTP 409 para "email ya registrado". El user-service real devuelve 400 + `errorCode: VALIDATION_003`. Corregido para aceptar ambos (409+USER_001 para monolith-baseline, 400+VALIDATION_003 para la pila real).
3. **`experiments/common/asr_client.py::transcribe_file()`** — descubrí que `POST /api/v1/transcribe` devuelve **formas de respuesta distintas** según la arquitectura: `monolith-baseline` devuelve el `TranscriptionResponse` completo (con `processing_time`/`device_used`/`compute_type`), pero la pila real proxea la respuesta de `audio-processor` (`AudioUploadResponse`, con `transcription_text` en vez de `text`, sin `processing_time` ni `device_used`/`compute_type` — esos campos viven en transcription-manager). Sin el fix, E2 calculaba RTF y WER con basura (RTF de miles de millones, WER siempre 1.0). Corregido: cuando la respuesta inicial no trae `processing_time`, se hace un segundo `GET /api/v1/transcriptions/{id}` para obtener el registro enriquecido.
4. **`unique_test_email()`** generaba direcciones `@experiments.local` — `.local` es un TLD reservado (RFC 6761) que `pydantic[email]` rechaza. Cambiado a `@example.com` (RFC 2606, dominio reservado para documentación/ejemplos).

## Verificado end-to-end

### Fase 1 — Mecanismo adaptativo
- `docker compose up --build` — los 11 contenedores (6 servicios reales + monolith-baseline + 4 DBs propias) llegan a `healthy`.
- `GET /status/adaptation` responde con snapshot de hardware real del contenedor (`cpu_count`, `ram_total_gb`, `gpu_available: false`) y `current: {device: cpu, compute_type: fp32}`.
- Logs confirman `"Model loaded successfully (device=cpu, compute_type=fp32)"` y `"Device adaptation monitor started"`.
- Transcripción real de audio quechua (`E:\IWSLT2026_Quechua_data\...\quechua000000.wav`) → texto exacto **"wañuchisunchu kay suwakunata"**, coincide palabra por palabra con la referencia del manifest (WER=0 en esa muestra).
- `device_used`/`compute_type` confirmados en Postgres (`SELECT ... FROM transcriptions`) — el stamping de la Fase 1 llega intacto de punta a punta.

### Fase 2 — Monolito baseline
- Flujo completo register → login → transcribe → list contra `localhost:8006`, sin pasar por ningún otro servicio.
- Mismo audio, misma transcripción exacta que la pila real.
- `confidence_scores` con datos reales por palabra (confirma que el fix del bug `word_confidences`/`confidence_scores` de la Fase 1 también corrige el pipeline propio del monolito).

### Fase 3 — Herramientas de experimentos (E2 smoke test real)
- `experiments/e2_wer_cer_rtf/run_transcribe_benchmark.py` corrido contra 3 clips reales del corpus IWSLT2026: WER/CER/RTF calculados correctamente (RTF 0.3–0.7, más rápido que tiempo real en CPU; errores de WER explicables por variación fonética menor real del modelo, no por fallas de la herramienta).
- `experiments/e2_wer_cer_rtf/report.py` agrega correctamente a media±IC95, con el intervalo ancho esperado para n=3 (E7 exige n≥10 para una corrida real).

### Fase 5 — Smoke test de integración
- `tests/integration/test_real_stack_smoke.py` — 2/2 pasan (`test_health_ok`, `test_register_login_roundtrip`) con `RUN_REAL_STACK_TESTS=1` contra la pila viva.

## Pendiente (fuera de alcance de esta verificación)

- **Fase 4 (E5, códecs comprimidos)**: el soporte de `encoding=opus/mp3` en streaming no se probó todavía en esta sesión — requiere `ffmpeg` local para codificar los clips de prueba antes de enviarlos.
- **E3, E4, E6 completos**: esta verificación confirma que el instrumental *funciona*, no que ya se corrieron los experimentos reales con N≥10 repeticiones que pide el protocolo. Ver `experiments/README.md` para el orden de ejecución.
- **Rama GPU del mecanismo adaptativo**: no se probó en este entorno (Docker Desktop en esta máquina no expone GPU al contenedor); ya validada localmente por separado según lo indicado en la Fase 1.

## Incidente durante la verificación (nota operativa, no técnica)

Docker Desktop se actualizó automáticamente a mitad de la primera verificación (cliente 29.6.2 → 29.8.0) y quedó en un estado roto (Error 500 en cualquier comando, incluso `docker version`). Ni cerrar/reabrir la app ni `wsl --shutdown` lo resolvieron — hizo falta usar el botón **"Restart Docker Desktop"** del menú Troubleshoot (preserva contenedores/imágenes) para que el motor volviera a responder. Después de eso, un `docker compose down && docker compose up --build -d` limpio dejó todo operativo.
