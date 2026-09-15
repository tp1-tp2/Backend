# Fase 5 — Log de verificación

Este documento resume qué se verificó realmente durante la implementación (Fases 1-4) y qué queda pendiente de correr en Docker — no reemplaza correr la pila real, pero deja claro qué ya se probó y qué es solo "compila y la lógica es correcta en aislamiento".

## Verificado en esta sesión (sin Docker)

| Fase | Qué se verificó | Cómo |
|---|---|---|
| 1 — Mecanismo adaptativo | Los 6 escenarios de `evaluate_policy()` (sin GPU/CPU baja, sin GPU/CPU alta, GPU con margen, GPU con presión de VRAM, `force_device`, `force_compute_type`) deciden correctamente | Script standalone (`psutil`/`pydantic-settings`/`fastapi`/`httpx` instalados localmente), fuera de Docker |
| 1 — Mecanismo adaptativo | La histéresis exige exactamente `adaptation_hysteresis_checks` sondeos consecutivos antes de aplicar un swap; el cooldown se respeta | Mismo script, con un `whisper_service` simulado (monkeypatch) y `DeviceManager._tick()` real |
| 1, 2, 3, 4 | Todos los archivos `.py` nuevos/modificados compilan sin errores de sintaxis | `python -m py_compile` sobre cada archivo tocado |
| 2 — Monolito | `docker-compose.yml` es YAML válido con los 2 servicios nuevos (`monolith-baseline`, `monolith-db`) presentes | `python -c "import yaml; yaml.safe_load(...)"` |

## Pendiente — requiere Docker (y, para algunos, un dataset real)

Estos pasos **no se ejecutaron** en esta sesión porque requieren levantar contenedores reales (build de imágenes, descarga del modelo Whisper, Postgres corriendo). Ejecutar antes de confiar en los resultados para la tesis:

### Fase 1
```bash
docker compose up --build asr-service
curl http://localhost:8004/status/adaptation   # confirmar snapshot de hardware real
# inducir presión de CPU artificialmente (ej. stress-ng) y confirmar un swap real a int8
# transcribir un audio y confirmar device_used/compute_type en la respuesta y en Postgres:
docker compose exec trans-db psql -U trans_user -d trans_db -c "select device_used, compute_type from transcriptions limit 5;"
```

### Fase 2
```bash
docker compose up --build monolith-baseline
# register -> login -> transcribe -> list, end-to-end, contra localhost:8006
# confirmar (revisando logs / docker network) que NO hay tráfico saliente hacia
# auth-service, audio-processor, asr-service ni transcription-manager
```

### Fase 3 y 4
```bash
cd experiments
pip install -r requirements.txt
# smoke test con 1-2 clips antes de comprometerse a corridas completas N>=10:
python e2_wer_cer_rtf/run_transcribe_benchmark.py --manifest <manifest_pequeño.csv> --repeats 2 --out ../results/smoke.csv
python e5_streaming_codec/run_pcm_vs_compressed.py --manifest <manifest_pequeño.csv> --repeats 2 --out ../results/smoke_e5.csv
```

### Fase 5
```bash
RUN_REAL_STACK_TESTS=1 pytest tests/integration/test_real_stack_smoke.py -v
```

## Qué significa esto para la tesis

El código está completo y la lógica pura (la política de adaptación, las 6 decisiones que puede tomar) está probada. Lo que falta es la verificación de integración real — que Docker efectivamente arme las imágenes, que Postgres persista correctamente, que el modelo Whisper cargue y produzca resultados coherentes bajo carga real. Esa verificación es indispensable antes de usar cualquier número de este trabajo como evidencia empírica en el paper — no se debe citar ningún resultado sin haber corrido los pasos "Pendiente" de arriba primero.
