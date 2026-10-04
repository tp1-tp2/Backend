# experiments/

Herramientas de medición para E1-E7 del Protocolo Experimental y, desde la
arquitectura v2, para E8 (throughput de inferencia), E9 (adaptación) y las
versiones v2 de E4/E6 — ver `docs/10-experimentos-v2.md`. Separado de
`tests/` a propósito: esto no es una suite de regresión rápida/mockeada, es
medición real contra una pila multi-servicio corriendo de verdad (Docker
Compose local o Azure), con corridas de varios minutos.

## Setup

```bash
cd experiments
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Necesitas `ffmpeg` en el PATH (para E1's probing de duración y E5's
codificación a Opus/MP3) y la pila real corriendo (`docker compose up` desde
`Backend/`, o apuntar `--base-url` a la URL pública de Azure).

## Orden de ejecución sugerido (según el protocolo)

1. **E1** — `python e1_dataset_characterization/characterize.py --manifest <tu_manifest.csv>` (prerequisito de todo lo demás)
2. **E3** (construir el baseline monolítico) — Fase 2, en paralelo a E1
3. **E2** y **E5** (necesitan el dataset de E1 listo)
4. **E4** (necesita ambas arquitecturas desplegadas)
5. **E6** (necesita E4 corriendo establemente primero)
6. **E7** se aplica transversalmente — cada `report.py` ya usa `common/stats.py`

## Formato del manifest (E1/E2/E5)

CSV con columnas: `audio_path,reference_text[,speaker,sex,age,dialect,source,condition]`.
Ver `e1_dataset_characterization/manifest.example.csv`. `audio_path` es
relativo al CSV o absoluto.

## Resultados

Cada script escribe CSV crudo timestampeado a `results/` (gitignored) y un
reporte agregado (markdown) al lado. `e7_statistics/aggregate_report.py`
puede releer todos los CSVs de `results/` y re-emitir tablas consolidadas.

## Experimentos v2 (por dimensión de la arquitectura)

| Dimensión | Script | Qué mide |
|---|---|---|
| Disponibilidad | `e6_fault_injection/run_scenario.py` | Carga + fallo (`kill`/`stop`/`pause`) en un comando: éxito antes/durante/después, detección, **MTTR**, propagación, trabajos perdidos |
| Escalabilidad | `e4_load_test/locustfile.py` (`E4_MODE=sync\|async`, `E4_RAW_CSV`) + `e4_load_test/slo_report.py` | Capacidad por SLO (p95 ≤ 10 s, error ≤ 5 %), desglose de fallos, cota de Little |
| Rendimiento | `e8_inference_throughput/bench.py` + `report.py` | Throughput (s de audio/s) y latencia por dispositivo × precisión × *batch* × concurrencia; control de WER |
| Adaptación | `e9_adaptation/observe.py` | Decisiones aplicadas, tiempo de reacción y reversión ante una ráfaga (C2.3, RQ1) |

Todo se puede orquestar con `run_v2_suite.py` (cambia la configuración de la
pila con variables de entorno y `docker compose up --force-recreate`):

```bash
python run_v2_suite.py --phase e8 e9 --audio results/sample_tts_16k.wav --quick   # humo
python run_v2_suite.py --phase e8 e9 e6 e4 --audio <clip_real.wav> --repeats 3     # completo
```

**Cambio de validez en v2:** el locustfile ahora valida el cuerpo de la
respuesta. Un `200` sin `transcription_id` cuenta como fallo. Antes no se
validaba, y `audio-processor` devolvía exactamente eso cuando asr-service
fallaba (ver `docs/09-arquitectura-v2.md` §1.2).

**Python:** los pines de `requirements.txt` son para 3.11. Con Python 3.14
instalar las versiones actuales sin pin:
`pip install locust pandas scipy numpy jiwer httpx tabulate websockets psutil`.
