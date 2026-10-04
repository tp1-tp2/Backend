# Pendientes en el equipo con GPU (NVIDIA)

Guía para ejecutar en el equipo con **GPU NVIDIA (RTX A1000, 8 GB)** todo lo que no pudo medirse en el equipo de evaluación sin GPU (i5-10400 + Intel UHD 630, ver `docs/14-optimizacion-cpu.md`). Lo que se hizo en CPU (E6, E9-B, E4 S1/S2/S2b, E3 en CPU, E8 en CPU) **no** se repite aquí.

## Qué queda pendiente y para qué criterio

| # | Experimento | Mide | Criterio / pregunta | Duración aprox. |
|---|---|---|---|---|
| 1 | Verificación GPU | La pila v2 usa CUDA dentro del contenedor | Prerrequisito | 15 min |
| 2 | **E8 GPU** — matriz de throughput | GPU fp16 + *batching* frente a CPU fp32 | **C3.4** (≥ 5× con WER sin diferencia material) | 50–60 min |
| 3 | **E9 A y C** — adaptación con GPU | fp32↔fp16, tamaño de *batch* y **migración en caliente CPU→GPU** | **C2.3**, **C2.4**, **RQ1** | 45 min |
| 4 | **E4 S3 y S4** — escalabilidad con GPU | Capacidad por SLO síncrona en GPU y modo asíncrono con 1000 usuarios | **C2.1**, **C2.2**, **C1.4** | 2 h 15 min |
| 5 | **E3 GPU** — propuesta frente a monolito, ambos con GPU | p50/p95/p99 y throughput | **C3.3** en GPU | 2 h |
| 6 | **E2 GPU** — RTF sobre el corpus completo | RTF mediano en GPU (2111 clips) | **C3.1** en GPU | 20–30 min |
| 7 | (Opcional) E6 con 50 usuarios en GPU | Inyección de fallos con la carga original del protocolo (50 usuarios) | C1.1–C1.7 a 50 usuarios | 2 h |
| 8 | (Opcional) Topología híbrida / Azure | Worker GPU local contra Redis en la nube; `asr-worker` con KEDA | Arquitectura (pendientes 9 y 10 de `docs/12`) | — |

**Total de lo obligatorio (1–6): unas 6 horas de máquina.** Conviene lanzarlo y dejarlo corriendo.

---

## 0. Preparación del equipo

### 0.1 Requisitos

- Driver NVIDIA instalado en Windows. `nvidia-smi` en PowerShell debe listar la GPU.
- Docker Desktop con backend WSL2. Probar que el contenedor ve la GPU:

```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

- Recursos de WSL (`C:\Users\<usuario>\.wslconfig`). Dar todos los núcleos y suficiente RAM, y luego ejecutar `wsl --shutdown` y reiniciar Docker:

```ini
[wsl2]
memory=16GB
swap=4GB
processors=<número de hilos lógicos del equipo>
```

- `ffmpeg` en el PATH y Python 3.11 o superior.
- **El puerto 8000 está ocupado en ese equipo**: el gateway se publica en el **8080** (`GATEWAY_PORT=8080`).

### 0.2 Corpus

Copiar `E:\IWSLT2026_Quechua_data` a **la misma ruta** (`E:\IWSLT2026_Quechua_data`). Los manifiestos usan rutas absolutas y así funcionan sin cambios. Si no hay unidad `E:`, regenerar el manifiesto:

```bash
cd experiments
python e1_dataset_characterization/build_manifest_from_iwslt.py --corpus-root "<ruta>/IWSLT2026_Quechua_data" --out results/manifest_full.csv
```

y ajustar la ruta en `e1_dataset_characterization/manifest_e5_sample.csv`, la muestra estratificada de 30 clips.

Copiar también el clip de carga, `quechua_03068.wav` (Huqariq, 24.05 s, cerca de la mediana del corpus), que es el mismo de las corridas en CPU:

```bash
cp "E:/IWSLT2026_Quechua_data/que_spa_synthetic_translation/train/wav/quechua_03068.wav" experiments/results/load_clip_real.wav
```

### 0.3 Código e imágenes

```bash
git checkout new-implementation && git pull
docker compose -f docker-compose.yml -f docker-compose.gpu.yml build
```

La imagen de asr-service ahora incluye también el modelo convertido a CTranslate2 (`/models/ct2`). La primera construcción tarda.

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
curl http://localhost:8004/health
curl http://localhost:8004/status/adaptation
```

Debe responder `"device": "cuda"` en `/health` y `gpu_available: true` con el nombre de la GPU en `last_hardware_snapshot`. Si sale `cpu`, revisar 0.1 antes de seguir: los resultados no servirían.

Sembrar los usuarios de prueba (la suite lo hace sola si falta el archivo):

```bash
cd experiments/e4_load_test
..\.venv\Scripts\python seed_test_users.py --base-url http://localhost:8080 --count 30 --out ../results/users_v2_proposed.csv
```

---

## 2. E8 GPU — throughput de inferencia (C3.4)

Matriz completa de `run_v2_suite.py` (`E8_MATRIX`): `cpu-fp32-b1`, `cpu-int8-b1`, `cuda-fp32-b1`, `cuda-fp16-b1`, `cuda-fp16-b4`, `cuda-fp16-b8` y `cuda-fp16-b16`. Concurrencia 1–32, 60 s por nivel, con control de WER usando la muestra estratificada:

```bash
cd experiments
run_gpu_suite.cmd e8 --manifest e1_dataset_characterization\manifest_e5_sample.csv
```

Salida: `results/e8_<config>.csv` y `results/e8_report.md`. **C3.4 se cumple** si `cuda-fp16-b8` alcanza ≥ 5× el throughput (segundos de audio por segundo) de `cpu-fp32-b1` **y** el WER de control no cambia de forma material (Wilcoxon por clip frente a fp32).

Notas:
- `cpu-fp32-b1` de este equipo es la base de C3.4 (misma máquina). Como referencia adicional se puede citar la mejor configuración de CPU del otro equipo: CTranslate2 int8 con 3 líneas, 19.4 s de audio por segundo (`docs/14`).
- (Opcional) Probar CTranslate2 en GPU (`ENGINE=ctranslate2`, `FORCE_COMPUTE_TYPE=fp16`). Requiere que la imagen encuentre cuBLAS 12 y cuDNN 9 (los trae la rueda de torch cu121). Si falla al cargar, se descarta y se reporta transformers.

## 3. E9 A y C — adaptación con GPU (C2.3, C2.4, RQ1)

```bash
run_gpu_suite.cmd e9 --repeats 3
```

Ejecuta los tres escenarios de `E9_SCENARIOS` (sin `--cpu-only`):

| Escenario | Configuración | Esperado |
|---|---|---|
| A — GPU adaptativa | `DEVICE=cuda` | fp32 / *batch* 8 en reposo; fp16 / *batch* 16 bajo la ráfaga, con periodo de prueba superado; vuelta al terminar |
| B — solo CPU | `FORCE_DEVICE=cpu` | Ya medido en CPU con ambos motores; aquí sirve como contraste en este host |
| **C — CPU→GPU (RQ1)** | `DEVICE=cpu`, GPU disponible | **Migración en caliente a cuda** sin interrumpir inferencias |

Salida: `results/e9_<escenario>_r<k>.summary.json` y `.decisions.json`. Reportar el tiempo de reacción, las decisiones aplicadas por eje, el resultado del periodo de prueba y el throughput antes y después.

## 4. E4 S3 y S4 — escalabilidad con GPU (C2.1, C2.2)

Solo las corridas con GPU. S1 y S2 (CPU) ya están medidas en el otro equipo; si se quiere la comparación S1 frente a S3 **en el mismo hardware**, añadir también `S1-v1-cpu-sync`:

```bash
run_gpu_suite.cmd e4 --repeats 3 --e4-only S3-v2-gpu-sync S4-v2-gpu-async
```

- Rampa 10 → 50 → 100 → 200 → 500 → 1000 usuarios, 180 s por escalón (igual que en CPU y en el capítulo 5).
- S4 (asíncrono): al terminar la rampa, la suite espera a que la cola se vacíe y escribe `results/e4v2_S4-..._jobs.json` con los trabajos **enviados / aceptados / procesados / fallidos**. Ese archivo es la evidencia de C2.2.
- Reportes: `results/e4v2_<corrida>_r<k>_slo.md`, con la capacidad por SLO (p95 ≤ 10 s y error ≤ 5 %), el desglose de fallos y la cota de Little.

Criterios:
- **C2.1:** capacidad por SLO de S3 > S1.
- **C2.2 (definición sin colapso):**
  - Asíncrono: ≥ 99 % de envíos aceptados y 100 % de trabajos aceptados completados.
  - Síncrono: el exceso se rechaza rápido con 503 + `Retry-After`, sin timeouts y con recuperación al bajar la carga.

## 5. E3 GPU — propuesta frente a monolito (C3.3)

```bash
run_gpu_suite.cmd e3 --repeats 3
```

Ambas arquitecturas con GPU (`docker-compose.gpu.yml` también le da la GPU al monolito) y validación del cuerpo de la respuesta. La suite ya espera a que el monolito esté sano antes de cargar, una corrección del 2026-10-04. Comparar p50/p95/p99 y throughput con Mann-Whitney y delta de Cliff (`e4_load_test/compare_architectures.py`).

## 6. E2 GPU — RTF sobre el corpus completo (C3.1)

Con la pila en GPU levantada:

```bash
cd experiments/e2_wer_cer_rtf
..\.venv\Scripts\python run_transcribe_benchmark.py --manifest ../results/manifest_full.csv --base-url http://localhost:8080 --repeats 1 --out ../results/e2_gpu_raw.csv
..\.venv\Scripts\python report.py --raw ../results/e2_gpu_raw.csv --out ../results/e2_gpu_report.md
```

Reportar el RTF mediano y el IQR en GPU (en CPU fp32 fue 0.149 en el capítulo 5). Sirve también como control de que el WER en GPU coincide con el de CPU (mediana 0.697).

## 7. (Opcional) E6 con 50 usuarios en GPU

El protocolo original usa 50 usuarios. En CPU se redujo a 10 porque 50 superan la capacidad y E6 terminaba midiendo sobrecarga (ver `docs/14`). En GPU la capacidad es mayor, así que vale la pena repetirlo con la carga original:

```bash
run_gpu_suite.cmd e6 --repeats 3 --e6-users 50
```

---

## Orden recomendado y ejecución desatendida

```bash
cd experiments
run_gpu_suite.cmd e8 e9 e4 e3 --repeats 3 --manifest e1_dataset_characterization\manifest_e5_sample.csv --e4-only S3-v2-gpu-sync S4-v2-gpu-async
```

Para que la corrida no dependa de la terminal, lanzarla desde PowerShell como proceso independiente:

```powershell
Start-Process cmd.exe -ArgumentList '/c "<ruta>\experiments\run_gpu_suite.cmd" e8 e9 e4 e3 --repeats 3 --manifest e1_dataset_characterization\manifest_e5_sample.csv --e4-only S3-v2-gpu-sync S4-v2-gpu-async' -WindowStyle Hidden
```

Seguimiento: `results/log_suite_gpu.txt`. Cada fase escribe una línea `=== [hora] <fase>` y al final aparece `SUITE_EXIT`. Después, E2 (paso 6) a mano.

## Al terminar: qué traer de vuelta

Copiar al repositorio, en `experiments/results_v2_gpu/` (los CSV crudos grandes pueden quedarse fuera):

- `e8_*.csv`, `e8_report.md`
- `e9_*_r*.summary.json` y `e9_*_r*.decisions.json`
- `e4v2_S3*`, `e4v2_S4*` (`_slo.md`, `_jobs.json` y los CSV de Locust)
- `e3v2_*_slo.md` y los CSV de E3
- `e2_gpu_report.md`
- `log_suite_gpu.txt`

Con eso se completan en el capítulo 5 C3.4, RQ1 (escenario C de E9), C2.1/C2.2 con GPU y C3.1/C3.3 en GPU.

## Problemas conocidos

- `docker kill`/`docker stop` no activan la política de reinicio; E6 usa el modo `crash` (SIGKILL desde el espacio de PIDs del host).
- Si la pila se recrea entre corridas, el monolito tarda más que el gateway en estar listo. La suite ya lo espera; si se corre algo a mano, comprobar `http://localhost:8006/health` antes de cargar.
- La tarea en segundo plano del agente tiene un límite de 2 h. Las corridas largas deben lanzarse como proceso independiente (ver arriba).
- `ctranslate2==4.4.0` fallaba con el glibc de la imagen (*executable stack*); se usa 4.6.0.
