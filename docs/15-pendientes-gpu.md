# Pendientes en el equipo con GPU (NVIDIA)

Guía para ejecutar en el equipo con **GPU NVIDIA (RTX A1000, 8 GB)** lo que no pudo medirse en el equipo de evaluación sin GPU (i5-10400 + Intel UHD 630).

**Actualizado el 2026-10-05**, después de completar toda la validación en CPU. Los resultados de CPU (`docs/17-resultados-v2-cpu.md`) ya están en el capítulo 5 y **no se repiten aquí**: E6, E8 en CPU, E9-B, E4 S1/S2/S2b/S2c y E3 en CPU.

## Qué queda pendiente y para qué criterio

| # | Experimento | Mide | Criterio / pregunta | Duración aprox. |
|---|---|---|---|---|
| 1 | Verificación GPU | La pila v2 usa CUDA dentro del contenedor | Prerrequisito | 15 min |
| 2 | **E8 GPU**: matriz de throughput | GPU fp16 + *batching* frente a CPU (transformers fp32 y la mejor configuración de CPU) | **C3.4** (≥ 5× con WER sin diferencia material) | ~1 h 10 min |
| 3 | **E9 A y C**: adaptación con GPU | fp32↔fp16, tamaño de *batch* y **migración en caliente CPU→GPU** | **C2.3, C2.4, RQ1** | 45 min |
| 4 | **E4 S3 → calibración → S3c, y S4** | Capacidad síncrona en GPU sin y con admisión en el borde; modo asíncrono con 1000 usuarios | **C2.1, C2.2, C1.4** con GPU | ~3 h 30 min |
| 5 | **E3 GPU**: propuesta frente a monolito, ambos en cuda/fp32 | p50/p95/p99 y goodput | **C3.3** en GPU | ~2 h |
| 6 | **E2 GPU**: RTF sobre el corpus completo | RTF mediano en GPU (2111 clips) | **C3.1** en GPU | 20–30 min |
| 7 | (Opcional) E6 con 50 usuarios en GPU | Inyección de fallos con la carga original (50 usuarios) | C1.1–C1.7 a 50 usuarios | ~2 h 30 min |
| 8 | (Opcional) Topología híbrida / Azure | Worker GPU local contra Redis en la nube; `asr-worker` con KEDA | Arquitectura (pendientes 9 y 10 de `docs/12`) | — |

**Total de lo obligatorio (1–6): unas 8 horas de máquina.** Conviene dejarlo corriendo de noche, como proceso independiente.

---

## Lecciones de la corrida en CPU que aplican aquí

Ya están incorporadas en el código; se listan para no repetir errores al correr a mano:

1. **Usar `127.0.0.1`, nunca `localhost`.** En Windows, `localhost` resuelve a IPv6 (`::1`) y el relay IPv6 de Docker Desktop (`wslrelay`) **se cuelga** después de una carga de 1000 usuarios. Los scripts y los `.cmd` ya usan `127.0.0.1`.
2. **Lanzar las corridas como proceso independiente** (`Start-Process ... -WindowStyle Hidden`), no desde una terminal o tarea con límite de tiempo.
3. **El proxy de puertos de Docker Desktop retiene conexiones** tras un escalón de 1000 usuarios y las entrega a la corrida siguiente. La suite espera a que se vacíe (`quiesce()`) y limpia los cupos de admisión antes de cada carga. Si se corre Locust a mano, esperar a que `netstat -ano | findstr :8080` no muestre conexiones `ESTABLISHED` antes de empezar.
4. **El monolito arranca más lento** que el gateway. La suite ya lo espera; a mano, comprobar `http://127.0.0.1:8006/health`.
5. **El generador de carga en el mismo equipo** compite por la CPU con la plataforma: con 500–1000 usuarios reenvía ~200 solicitudes/s, cada una con el audio completo. En GPU la plataforma es más rápida y esto pesa más. **Si es posible, correr Locust desde otra máquina** de la red local (`--host http://<IP-del-equipo-GPU>:8080`, con el puerto abierto en el firewall). Si no, declararlo como amenaza a la validez, como en CPU.
6. **No fiarse de `XINFO lag` de Redis.** Ya corregido: la cola y el vaciado se miden con un conteo exacto y con los contadores del worker.

---

## 0. Preparación del equipo

### 0.1 Requisitos

- Driver NVIDIA instalado: `nvidia-smi` en PowerShell lista la GPU.
- Docker Desktop con backend WSL2. Probar que el contenedor ve la GPU:

```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

- `.wslconfig` (`C:\Users\<usuario>\.wslconfig`): dar todos los hilos y suficiente RAM; luego `wsl --shutdown` y reiniciar Docker.

```ini
[wsl2]
memory=16GB
swap=4GB
processors=<número de hilos lógicos del equipo>
```

- `ffmpeg` en el PATH y Python 3.11 o superior.
- En ese equipo **el puerto 8000 está ocupado**: el gateway se publica en el **8080** (`GATEWAY_PORT=8080`).

### 0.2 Corpus y clip de carga

Copiar `E:\IWSLT2026_Quechua_data` a la **misma ruta**: los manifiestos usan rutas absolutas. Si no hay unidad `E:`, regenerar el manifiesto:

```bash
cd experiments
python e1_dataset_characterization/build_manifest_from_iwslt.py --corpus-root "<ruta>/IWSLT2026_Quechua_data" --out results/manifest_full.csv
```

y ajustar las rutas de `e1_dataset_characterization/manifest_e5_sample.csv` (la muestra estratificada de 30 clips).

Clip de carga (el mismo que en CPU, para comparar): `quechua_03068.wav` (Huqariq, 24.05 s).

```bash
cp "E:/IWSLT2026_Quechua_data/que_spa_synthetic_translation/train/wav/quechua_03068.wav" experiments/results/load_clip_real.wav
```

### 0.3 Código e imágenes

```bash
git checkout new-implementation && git pull
docker compose -f docker-compose.yml -f docker-compose.gpu.yml build
```

La imagen de asr-service incluye el modelo convertido a CTranslate2 (`/models/ct2`) y la del gateway la admisión en el borde. La primera construcción tarda.

### 0.4 Entorno de experimentos

```bash
cd experiments
python -m venv .venv
.venv\Scripts\pip install locust pandas scipy numpy jiwer httpx tabulate websockets psutil soundfile pyyaml
```

---

## 1. Verificación GPU (prerrequisito)

```bash
set GATEWAY_PORT=8080
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --force-recreate
curl http://127.0.0.1:8004/health
curl http://127.0.0.1:8004/status/adaptation
```

Debe responder `"device": "cuda"` en `/health` y `gpu_available: true` con el nombre de la GPU en `last_hardware_snapshot`. Si sale `cpu`, revisar 0.1 antes de seguir: los resultados no servirían.

Usuarios de prueba (la suite los crea sola si falta el archivo):

```bash
cd experiments/e4_load_test
..\.venv\Scripts\python seed_test_users.py --base-url http://127.0.0.1:8080 --count 30 --out ../results/users_v2_proposed.csv
```

---

## 2. E8 GPU — throughput de inferencia (C3.4)

Matriz de GPU (`E8_MATRIX`): `cpu-fp32-b1`, `cpu-int8-b1`, `cuda-fp32-b1`, `cuda-fp16-b1`, `cuda-fp16-b4`, `cuda-fp16-b8` y `cuda-fp16-b16`. Concurrencia 1–32, 60 s por nivel, con control de WER sobre la muestra:

```bash
cd experiments
run_gpu_suite.cmd e8 --manifest e1_dataset_characterization\manifest_e5_sample.csv
```

**Referencia de CPU optimizada en el mismo equipo (recomendado).** C3.4 se define frente a `cpu-fp32-b1`, pero en CPU se demostró que la mejor configuración (CTranslate2 int8, 3 líneas × 2 hilos) da 2.7× esa base. Para una comparación honesta GPU frente a CPU optimizada, medirla también en este equipo:

```bash
.venv\Scripts\python run_v2_suite.py --cpu-only --phase e8 --e8-only ct2-int8-l3t2 --audio results\load_clip_real.wav --manifest e1_dataset_characterization\manifest_e5_sample.csv --e8-seconds 45
```

Ajustar los hilos al número de núcleos **físicos** de ese CPU: en el i5-10400, usar los 12 hilos lógicos en una sola línea fue 5× más lento.

Salida: `results/e8_<config>.csv` y `results/e8_report.md`; resumen rápido con `e8_inference_throughput/summarize_cpu.py`.

**C3.4 se cumple** si `cuda-fp16-b8` alcanza ≥ 5× el throughput (segundos de audio por segundo) de `cpu-fp32-b1` **y** el WER de control no cambia de forma material. Reportar también la razón frente a `ct2-int8-l3t2`.

(Opcional) CTranslate2 en GPU (`ENGINE=ctranslate2`, `FORCE_COMPUTE_TYPE=fp16`). Requiere cuBLAS 12 y cuDNN 9, que la rueda de torch cu121 debería aportar. Si falla al cargar, se descarta y se reporta transformers.

## 3. E9 A y C — adaptación con GPU (C2.3, C2.4, RQ1)

```bash
run_gpu_suite.cmd e9 --repeats 3
```

| Escenario | Configuración | Esperado |
|---|---|---|
| A — GPU adaptativa | `DEVICE=cuda` | fp32 / *batch* 8 en reposo; fp16 / *batch* 16 bajo la ráfaga, con periodo de prueba superado; vuelta al terminar |
| B — solo CPU | `FORCE_DEVICE=cpu` (transformers) | Contraste en este host (en CPU ya se midió con ambos motores) |
| **C — CPU→GPU (RQ1)** | `DEVICE=cpu`, GPU disponible | **Migración en caliente a cuda** sin interrumpir inferencias |

Salida: `results/e9_<escenario>_r<k>.summary.json` y `.decisions.json`. Reportar el tiempo de reacción, las decisiones aplicadas por eje, el resultado del periodo de prueba y el throughput antes y después.

## 4. E4 con GPU — escalabilidad (C2.1, C2.2)

Rampa 10 → 50 → 100 → 200 → 500 → 1000 usuarios con 180 s por escalón, igual que en CPU. Tres pasos:

**4.1 S3: v2 en GPU sin admisión en el borde** (sirve de ablación y para calibrar el límite):

```bash
run_gpu_suite.cmd e4 --repeats 3 --e4-only S3-v2-gpu-sync
```

**4.2 Calibrar el límite del borde** con el agregador:

```bash
.venv\Scripts\python e4_load_test\aggregate_v2.py --labels S3-v2-gpu-sync --out results\e4v2_S3_aggregate.md
```

Tomar el escalón donde S3 alcanza su **goodput máximo** (X_sat, en transcripciones/s) y su tiempo de respuesta mediano en ese escalón (R_sat, en s). El límite es **N = X_sat × R_sat**, redondeado. En CPU fue 0.84 × 12 ≈ 10. Un límite demasiado bajo rechaza incluso con poca carga: con 6 en CPU, se rechazó el 76 % con 10 usuarios.

**4.3 S3c (v2 completo en GPU) y S4 (asíncrono)**, con el límite calibrado:

```bash
run_gpu_suite.cmd e4 --repeats 3 --e4-only S3c-v2-gpu-sync-edge S4-v2-gpu-async --edge-inflight-gpu <N>
```

Salidas:
- `results/e4v2_<corrida>_r<k>_raw.csv` y `_slo.md`.
- Para S4, `results/e4v2_S4-..._jobs.json`, con los trabajos **enviados / aceptados / procesados / fallidos**: es la evidencia de C2.2.
- Tabla final: `aggregate_v2.py --labels S3-v2-gpu-sync S3c-v2-gpu-sync-edge S4-v2-gpu-async`.

Criterios:
- **C2.1:** goodput y techo de Little de S3c frente a S1 (v1). S1 puede tomarse de CPU, o correrse también aquí con `--e4-only S1-v1-cpu-sync` para comparar en el mismo hardware.
- **C2.2 (sin colapso):**
  - Asíncrono: ≥ 99 % de envíos aceptados y 100 % de trabajos aceptados completados.
  - Síncrono: el exceso se rechaza rápido con 503 + `Retry-After` y sin errores 5xx.

## 5. E3 GPU — propuesta frente a monolito (C3.3)

```bash
run_gpu_suite.cmd e3 --repeats 3 --edge-inflight-gpu <N>
```

La suite fija **ambas arquitecturas en cuda/fp32** (el monolito no tiene adaptación) y les da la GPU a las dos (`docker-compose.gpu.yml`). La propuesta conserva su planificador con *batching* y la admisión en el borde, que son parte de la arquitectura. Analizar con:

```bash
.venv\Scripts\python e4_load_test\compare_e3_v2.py --out results\e3v2_gpu_report.md
```

Mover antes los `e3v2_*` de CPU a otra carpeta para no mezclarlos. Se espera que el monolito vuelva a bloquearse con la llegada de usuarios: su login con bcrypt síncrono en el único *worker* detiene también las transcripciones, como ocurrió en CPU.

## 6. E2 GPU — RTF sobre el corpus completo (C3.1)

Con la pila en GPU levantada:

```bash
cd experiments/e2_wer_cer_rtf
..\.venv\Scripts\python run_transcribe_benchmark.py --manifest ../results/manifest_full.csv --base-url http://127.0.0.1:8080 --repeats 1 --out ../results/e2_gpu_raw.csv
..\.venv\Scripts\python report.py --raw ../results/e2_gpu_raw.csv --out ../results/e2_gpu_report.md
```

Reportar el RTF mediano y el IQR en GPU (CPU fp32: 0.149; CPU con CTranslate2 int8: 0.069 en la muestra). Sirve también como control de que el WER en GPU coincide con el de CPU (mediana 0.697).

## 7. (Opcional) E6 con 50 usuarios en GPU

En CPU se usaron 10 usuarios porque 50 superaban la capacidad: solo el 57.5 % tenía éxito antes del fallo. En GPU la capacidad debería permitir la carga original del protocolo:

```bash
run_gpu_suite.cmd e6 --repeats 3 --e6-users 50 --edge-inflight-gpu <N>
```

Comprobar primero que con 50 usuarios el éxito **antes** del fallo sea ≈ 100 %; si no, usar la capacidad medida en 4.2.

---

## Orden recomendado y ejecución desatendida

1. Pasos 0 y 1 a mano (preparación y verificación).
2. Primera noche: `e8 e9` y `e4 --e4-only S3-v2-gpu-sync`. Calibrar N (4.2).
3. Segunda noche: `e4 --e4-only S3c-v2-gpu-sync-edge S4-v2-gpu-async --edge-inflight-gpu <N>` y `e3 --edge-inflight-gpu <N>`.
4. E2 (paso 6) a mano.

Lanzar cada tramo como proceso independiente desde PowerShell. Ejemplo para el primer tramo:

```powershell
Start-Process cmd.exe -ArgumentList '/c "<ruta>\experiments\run_gpu_suite.cmd" e8 e9 --repeats 3 --manifest e1_dataset_characterization\manifest_e5_sample.csv' -WindowStyle Hidden
```

Seguimiento: `results/log_suite_gpu.txt`. Cada fase escribe `=== [hora] <fase>` y al final `SUITE_EXIT`. Las trazas de Locust con "connection refused" en el escalón de 1000 usuarios son esperables (saturación del *proxy* de Docker) y **no** indican que la suite haya fallado; la suite falla solo si aparece `RuntimeError`.

## Al terminar: qué traer de vuelta

Copiar al repositorio, en `experiments/results_v2_gpu/` (los CSV crudos grandes pueden quedarse fuera):

- `e8_*.csv`, `e8_report.md`
- `e9_*_r*.summary.json` y `e9_*_r*.decisions.json`
- `e4v2_S3*`, `e4v2_S3c*`, `e4v2_S4*` (`_slo.md`, `_jobs.json` y `aggregate`)
- `e3v2_gpu_report.md`
- `e2_gpu_report.md`
- `log_suite_gpu.txt`

Con eso se completan en el capítulo 5 C3.4, RQ1 (escenario C de E9), C2.1/C2.2 con GPU y C3.1/C3.3 en GPU. El capítulo ya tiene los resultados de CPU; los de GPU se agregan como una evaluación adicional del mismo artefacto en otro hardware.

## Problemas conocidos

- `docker kill`/`docker stop` no activan la política de reinicio; E6 usa el modo `crash` (SIGKILL desde el espacio de PIDs del host).
- `ctranslate2==4.4.0` fallaba con el glibc de la imagen (*executable stack*); se usa 4.6.0.
- Python 3.12+: `run_scenario.py` usaba un atributo `_stop` que choca con `threading.Thread` (corregido).
