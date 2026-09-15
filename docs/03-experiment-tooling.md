# Fase 3 — Scaffold de experimentos (`experiments/`)

## Qué problema resuelve

E1, E2, E4, E5, E6 y E7 del protocolo necesitan herramientas de medición real contra la pila desplegada — nada de esto existía antes: confirmado que todo test existente en el repo (`services/api-gateway/tests/e2e/`) corre en memoria con `TestClient` y mockea toda llamada de red, y no hay ni un archivo de audio de prueba en todo el repositorio. `experiments/` es una carpeta nueva, separada de `tests/` a propósito, porque esto es una categoría distinta de trabajo: medición real de varios minutos contra HTTP en vivo, no regresión rápida mockeada.

## Por qué separado de `tests/`

`tests/e2e/` y `tests/integration/` siguen siendo para regresión rápida apta para CI. `experiments/` tiene su propio `requirements.txt` (jiwer, locust, scipy, pandas, httpx, websockets, psutil, tabulate) para no ensuciar las dependencias de ningún servicio en producción.

## Módulos compartidos (`experiments/common/`)

- **`manifest.py`** — carga y valida el CSV de audio+transcripción de referencia (columnas: `audio_path,reference_text[,speaker,sex,age,dialect,source,condition]`), compartido por E1/E2/E5. Falla temprano y con mensaje claro si un archivo de audio referenciado no existe.
- **`asr_client.py`** — cliente HTTP/WebSocket contra `api-gateway` **o** `monolith-baseline` (ambos exponen las mismas rutas relativas, por diseño — ver Fase 2). `login()`/`register()`/`ensure_user()`, `transcribe_file()` (REST), `stream_pcm()`/`stream_encoded()` (WebSocket, con codificación Opus/MP3 vía `ffmpeg` local). Ningún test existente en el repo emite un JWT real contra una pila viva — esto es nuevo.
- **`text_norm.py`** — normalización de texto antes de `jiwer`. Qué tan "quechua-aware" debe ser la tokenización es una decisión de juicio para la tesis, no algo que el código pueda decidir solo — documentado explícitamente como tal.
- **`stats.py`** — el módulo de E7: `summarize()` (media±IC95 + mediana±IQR, con test de normalidad Shapiro-Wilk), `compare()` (t-test+Cohen's d si ambas muestras son normales, si no Mann-Whitney U+Cliff's delta). Todos los `report.py` de abajo lo importan — ningún reporte cuantitativo queda sin dispersión/test de hipótesis.

## Por experimento

| Carpeta | Qué hace | Cómo se conecta con la Fase 1/2/4 |
|---|---|---|
| `e1_dataset_characterization/` | `characterize.py` — cuenta clips, duración total/por-clip, desgloses por hablante/dialecto/condición (del manifest), placeholder de threats-to-validity | Prerequisito de E2/E5 |
| `e2_wer_cer_rtf/` | `run_transcribe_benchmark.py` + `report.py` — WER/CER (`jiwer`) y RTF por clip×repetición | Lee `device_used`/`compute_type` que cada respuesta ya trae estampados (Fase 1) — no hace falta llevar la cuenta manualmente de qué dispositivo sirvió cada request |
| `e4_load_test/` | `seed_test_users.py`, `locustfile.py` (rampa 10→1000, `LoadTestShape`), `docker_stats_sampler.py`, `report.py`, `compare_architectures.py` (esto último ES el experimento E3 — reutiliza esta misma suite contra ambas arquitecturas) | `compare_architectures.py` corre contra `asr-service` real (puerto 8000) y contra `monolith-baseline` (Fase 2, puerto 8006) |
| `e5_streaming_codec/` | `run_pcm_vs_compressed.py` + `report.py` — WER/CER/latencia/tamaño para PCM vs. Opus/MP3 | Ejercita el `encoding` param y `codec_service.py` de la Fase 4 |
| `e6_fault_injection/` | `inject.py` (`docker stop`/monitoreo de `/health` cada 1s/detección de propagación) + `report.py` | Se corre contra ambas arquitecturas — la corrida contra `monolith-baseline` es la otra mitad de la comparación de E3 (aislamiento de fallos) |
| `e7_statistics/` | `aggregate_report.py` — junta todos los `*_report.md` en un documento consolidado | No hay lógica estadística propia aquí; vive en `common/stats.py` y ya la usan todos los `report.py` de arriba |

## Lo que sigue siendo trabajo manual (no automatizable)

- Conseguir/apuntar el manifest a un corpus real con transcripciones de referencia (E1/E2/E5).
- Decidir qué cuenta como "degradación" en E4 (el heurístico de `report.py` es un punto de partida, no un veredicto).
- Elegir un bitrate "estándar" de Opus/MP3 para E5.
- Interpretar los resultados de propagación/aislamiento de E6.
- La redacción de la interpretación estadística en sí — los scripts solo calculan números.

## Verificación realizada

Todos los archivos Python de `experiments/` pasan `python -m py_compile` sin errores.

**Pendiente** (requiere un dataset real + la pila corriendo): correr `characterize.py` contra un manifest de prueba pequeño, correr `run_transcribe_benchmark.py` con `--repeats 2` contra 1-2 clips como smoke test antes de comprometerse a las corridas completas de N≥10 que pide E7.
