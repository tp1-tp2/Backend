# experiments/

Herramientas de medición para E1-E7 del Protocolo Experimental. Separado de
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
