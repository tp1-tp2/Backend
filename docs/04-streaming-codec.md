# Fase 4 — Soporte de códecs comprimidos en streaming (para E5)

## Qué problema resuelve

El README del proyecto afirma que enviar audio comprimido (Opus/WebM vía `MediaRecorder`) en vez de PCM crudo "produce ruido/alucinaciones en la transcripción" — pero esa afirmación nunca se validó cuantitativamente. **E5** del protocolo experimental pide exactamente eso: transmitir el mismo clip dos veces (PCM crudo vs. comprimido) y medir WER/CER, latencia y tamaño transmitido para ambas condiciones. Antes de esta fase, `asr-service` no tenía **ningún** soporte para decodificar audio comprimido — el pipeline entero asumía PCM 16-bit crudo de forma hardcodeada.

## Diseño

- **`encoding` como query param** en `/ws/stream` (`pcm` por default — el único valor que usa el frontend real; `opus`/`mp3` solo para el experimento E5). Se propaga: cliente → `api-gateway` (proxy WS) → `asr-service`.
- **`ConnectionManager` ahora sabe el encoding de cada sesión** (`StreamingSession.encoding`). En `append_chunk()`, cuando el encoding no es PCM, el buffer completo acumula bytes sin el recorte basado en `sample_rate` (esa cuenta no aplica a bytes comprimidos) — usa en su lugar un tope plano de seguridad (`_MAX_COMPRESSED_BYTES`, 50MB).
- **`finalize()` gana una rama consciente del encoding**: para `encoding != "pcm"`, escribe los bytes acumulados a un archivo temporal (`.opus`/`.mp3`) y llama a `codec_service.decode_to_wav()` (nuevo módulo, mismo patrón de subprocess `ffmpeg` que `audio-processor/app/services/ffmpeg_service.py::convert_to_wav()`) antes de pasarlo a `whisper_service.transcribe()`.

## Limitación de alcance, documentada a propósito

**Las transcripciones parciales (en vivo) siguen siendo solo-PCM.** Cortar un stream Opus/MP3 en medio (para re-transcribir la ventana corta de `get_partial()` cada pocos segundos) no es decodificable de forma confiable — el formato comprimido necesita el stream completo o al menos un punto de corte válido, no bytes arbitrarios a mitad de trama. El protocolo de E5 solo pide la comparación final (WER/CER/latencia/tamaño), no partials en vivo para el path comprimido, así que esto no bloquea el experimento.

## Archivos

- `services/asr-service/Dockerfile` — agregado `ffmpeg` a ambos stages (antes solo tenía `libsndfile1`).
- `services/asr-service/app/services/codec_service.py` (nuevo) — `decode_to_wav()`.
- `services/asr-service/app/schemas/transcription.py` — `StreamingSession.encoding`.
- `services/asr-service/app/services/streaming_service.py` — `connect()` acepta `encoding`; `append_chunk()` y `finalize()` tienen ramas conscientes del encoding.
- `services/asr-service/app/api/routes/streaming.py` — nuevo query param `encoding`.
- `services/api-gateway/app/api/routes/streaming.py` — el proxy WS reenvía `encoding` hacia asr-service.

## Verificación realizada

Todos los archivos modificados pasan `python -m py_compile` sin errores.

**Pendiente** (requiere Docker + un clip de audio real): levantar la pila, conectar dos veces al mismo `/ws/stream` — una con `encoding=pcm` y otra con `encoding=opus` — para el mismo clip codificado con `ffmpeg` localmente, confirmar que ambos flujos devuelven un resultado final válido, y que el flujo comprimido efectivamente pasa por `codec_service.decode_to_wav()` (revisar logs). La comparación cuantitativa de WER/CER en sí es tarea de `experiments/e5_streaming_codec/` (Fase 3).
