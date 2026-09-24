# Cómo correr los experimentos (E1-E7)

Guía práctica basada en las corridas reales de este proyecto — no solo el orden teórico del protocolo, sino los comandos exactos y los problemas reales que aparecieron al ejecutarlos. Para el diseño de cada script ver `experiments/README.md` y `docs/03-experiment-tooling.md`; este documento es el "cómo, paso a paso, sin sorpresas".

## 0. Prerrequisitos (una sola vez)

### ffmpeg / ffprobe

E1 (duración de clips) y E5 (codificar a Opus/MP3) necesitan `ffmpeg`/`ffprobe` reales, no solo los que están *dentro* de los contenedores Docker — corren en el host, fuera de Docker.

En Windows, si no están en el PATH (`ffprobe -version` falla), descargar el build portable:

```powershell
$dest = "$env:USERPROFILE\bin"   # o cualquier carpeta que ya esté en tu PATH
Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile "$env:TEMP\ffmpeg.zip"
Expand-Archive -Path "$env:TEMP\ffmpeg.zip" -DestinationPath "$env:TEMP\ffmpeg_extract" -Force
$bin = Get-ChildItem "$env:TEMP\ffmpeg_extract" -Directory | Select-Object -First 1
Copy-Item "$($bin.FullName)\bin\ffmpeg.exe" "$dest\ffmpeg.exe"
Copy-Item "$($bin.FullName)\bin\ffprobe.exe" "$dest\ffprobe.exe"
```

**Gotcha real**: no dejes una carpeta llamada `ffmpeg` (sin extensión) en el mismo directorio que `ffmpeg.exe` — Git Bash's `which ffmpeg` puede resolver el directorio en vez del ejecutable y reportar "not found" aunque el `.exe` sí exista. Si pasa, borrá la carpeta duplicada.

### Dependencias de Python

```bash
cd experiments
pip install -r requirements.txt
```

En Windows con Locust, invocá siempre con `python -m locust`, no `locust` directo — el entry-point a veces no queda en el PATH aunque el paquete sí esté instalado.

### La pila tiene que estar sana

```bash
docker compose ps
```

Los 7 contenedores de app (6 microservicios + `monolith-baseline`) y sus 5 bases de datos deben mostrar `healthy`. **Si la máquina durmió o Docker Desktop se reinició**, las bases de datos se caen pero los contenedores de app pueden seguir mostrando "Up" mientras están realmente desconectados — no confíes solo en el estado, corré `docker compose up -d` de nuevo (es idempotente) antes de cualquier ronda de experimentos.

## 1. Orden de ejecución

```
E1 (caracterizar dataset)
  └─> E2 (WER/CER/RTF, necesita el manifest de E1)
  └─> E5 (PCM vs. Opus, necesita el manifest de E1)
E3 parte A + parte B (monolito vs. propuesta, en paralelo conceptualmente,
                       pero correr las dos cargas SECUENCIALES, nunca a la vez
                       — compiten por el mismo CPU del host y contaminan la
                       comparación)
E6 (fault injection, un servicio a la vez, con carga constante corriendo
    en paralelo — este sí necesita dos procesos simultáneos)
E4 (contra Azure — requiere el despliegue arriba y el autoscaling verificado)
E7 no es un script aparte — cada report.py ya usa common/stats.py
```

## 2. E1 — Caracterización del dataset

```bash
cd experiments/e1_dataset_characterization
python characterize.py --manifest manifest.csv --out ../results/e1_characterization.md
```

Si tus audios son `.wav` planos (la mayoría de corpus de Quechua lo son), no hace falta `ffprobe` — el script puede leer la duración con el módulo `wave` de la librería estándar de Python, evitando la dependencia externa. Si tu manifest mezcla formatos, sí necesitás `ffprobe` en el PATH.

## 3. E2 — WER / CER / RTF

```bash
cd experiments/e2_wer_cer_rtf
python run_transcribe_benchmark.py --manifest ../e1_dataset_characterization/manifest.csv --base-url http://localhost:8000 --out ../results/e2_full_run.csv
python report.py --raw ../results/e2_full_run.csv --out ../results/e2_full_report.md
```

Correrlo contra el corpus completo (miles de clips) puede tardar horas — es aceptable correrlo en background y revisar el CSV (se escribe fila por fila, `f.flush()` después de cada una) en vez de esperar a que termine para ver progreso.

**No hace falta repetir E2 contra un despliegue en la nube** si ya corrió contra el stack local con el mismo modelo/dispositivo — WER/CER es determinístico dado el mismo modelo y compute_type; solo agregaría costo sin nueva información.

## 4. E3 — Monolito vs. arquitectura propuesta

Reusa el mismo `locustfile.py` de E4, apuntado a los dos `--host` distintos, **uno a la vez**:

```bash
# Sembrar usuarios de prueba para CADA target por separado (bases de datos distintas)
cd experiments/e4_load_test
python seed_test_users.py --base-url http://localhost:8000 --count 30 --out users_local_proposed.csv
python seed_test_users.py --base-url http://localhost:8006 --count 30 --out users_local_monolith.csv

# Parte A: arquitectura propuesta
E4_USERS_CSV=users_local_proposed.csv E4_SAMPLE_AUDIO=/ruta/a/un/clip.wav \
  python -m locust -f locustfile.py --host http://localhost:8000 --headless \
  --csv ../results/e3_proposed_run --html ../results/e3_proposed_run.html

# Esperar a que termine (~18 min con los defaults) ANTES de arrancar la parte B
# Parte B: monolito
E4_USERS_CSV=users_local_monolith.csv E4_SAMPLE_AUDIO=/ruta/a/un/clip.wav \
  python -m locust -f locustfile.py --host http://localhost:8006 --headless \
  --csv ../results/e3_monolith_run --html ../results/e3_monolith_run.html

# Comparación con prueba de hipótesis + effect size
python compare_architectures.py --proposed-history ../results/e3_proposed_run_stats_history.csv \
  --monolith-history ../results/e3_monolith_run_stats_history.csv --out ../results/e3_report.md
```

`locust` en modo headless sale con **exit code 1 si hubo algún request fallido** — no es necesariamente un crash. Confirmá viendo si `<prefix>_stats_history.csv` tiene datos de todo el rango de tiempo esperado (18 min ≈ duración de 6 escalones × 180s) antes de asumir que falló.

## 5. E6 — Fault injection

A diferencia de E3/E4, **necesita dos procesos corriendo a la vez**: una carga constante moderada (no la rampa) y el script que apaga el contenedor.

```bash
cd experiments/e4_load_test
# Locustfile sin LoadTestShape, para poder pasar --users directo por CLI
cat locustfile_constant.py   # ya existe: reusa TranscribeUser de locustfile.py

# 1. Lanzar la carga constante EN BACKGROUND (4 min de margen)
E4_USERS_CSV=users_local_proposed.csv E4_SAMPLE_AUDIO=/ruta/a/un/clip.wav \
  python -m locust -f locustfile_constant.py --host http://localhost:8000 \
  --headless --users 50 --spawn-rate 20 --run-time 4m \
  --csv ../results/e6_load_during_X_outage &

# 2. Con la carga ya corriendo, ejecutar el fault injection contra un servicio
cd ../e6_fault_injection
python inject.py --container backend-asr-service-1 --target-url http://localhost:8004 \
  --monitor-health http://localhost:8004/health http://localhost:8001/health \
                    http://localhost:8002/health http://localhost:8000/health \
  --warmup-s 30 --max-wait-s 120 --out ../results/e6_asr_service.csv

# 3. SIEMPRE reiniciar el contenedor después — inject.py hace `docker stop`,
#    y con restart policy `on-failure` NO vuelve solo (un stop limpio no
#    cuenta como "failure")
docker start backend-asr-service-1
```

Repetir para cada servicio crítico (`auth-service`, `transcription-manager`) y para `monolith-baseline` (con sus propios usuarios sembrados vía `seed_test_users.py --base-url http://localhost:8006`).

**Qué mirar para el resultado real**: no la columna "Requests lost" del summary de `inject.py` (eso solo confirma que el contenedor caído no responde a su propio healthcheck — trivial). Lo que importa es el `_stats.csv` de la carga constante que corrió en paralelo — ahí está el failure rate real de `/api/v1/transcribe` durante el apagón.

```bash
python report.py --summaries ../results/e6_*.summary.json --out ../results/e6_report.md
```

## 6. E5 — PCM crudo vs. códec comprimido

**No uses el manifest completo** — cada clip se transmite dos veces (PCM + comprimido) × N repeticiones, y cada transmisión toma varios segundos reales (no es instantáneo). Con miles de clips esto tardaría muchísimas horas. Armá una muestra estratificada:

```python
# Ejemplo: 30 clips proporcionales a las fuentes del corpus
import csv
with open("manifest.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
step = max(1, len(rows) // 30)
sample = rows[::step][:30]
# ... escribir sample a manifest_e5_sample.csv
```

```bash
cd experiments/e5_streaming_codec
python run_pcm_vs_compressed.py --manifest ../e1_dataset_characterization/manifest_e5_sample.csv \
  --base-url http://localhost:8000 --encoding opus --repeats 3 --out ../results/e5_raw.csv
python report.py --raw ../results/e5_raw.csv --out ../results/e5_report.md
```

**Si el streaming Opus se cuelga 300s sin respuesta** (`TimeoutError: No final result received`), revisá los logs de `asr-service` (`docker compose logs asr-service --tail 50`) buscando `torchaudio is required to resample` — es un bug conocido si `codec_service.py` no fuerza `-ar 16000` al decodificar (ya corregido en este repo, pero si volvés a tocar ese archivo, no lo repitas).

## 7. E4 — Escalabilidad (contra Azure)

Este es el único experimento que corre contra el **despliegue real**, no el stack local — cuesta créditos de Azure, así que no se repite sin motivo.

**Antes de correr, verificar el estado del autoscaling** (cualquier `az containerapp update` previo puede haber reseteado la regla — ver `docs/06-horizontal-autoscaling.md`):

```powershell
az containerapp show --name asr-service --resource-group <RG> --query "properties.template.scale" -o json
```

`concurrentRequests` no debe quedar como `""` — si quedó vacío, reaplicar con `--scale-rule-metadata concurrentRequests=<N>`.

```bash
cd experiments/e4_load_test
# Usuarios ya sembrados contra el gateway público de Azure (no localhost)
python seed_test_users.py --base-url https://<tu-gateway>.azurecontainerapps.io --count 30 --out users_azure.csv

E4_USERS_CSV=users_azure.csv E4_SAMPLE_AUDIO=/ruta/a/un/clip.wav \
  python -m locust -f locustfile.py --host https://<tu-gateway>.azurecontainerapps.io \
  --headless --csv ../results/e4_azure_run --html ../results/e4_azure_run.html

python report.py --locust-history ../results/e4_azure_run_stats_history.csv --step-duration 180 --out ../results/e4_azure_report.md
```

**Bug real ya corregido en `report.py`**: la versión anterior calculaba el error rate del escalón con la tasa instantánea (`Failures/s`) de la última fila muestreada en la ventana de 180s, no un conteo acumulado — podía reportar 0% de error aunque hubo un burst de fallas a mitad de la ventana. El script ya usa `Total Request Count`/`Total Failure Count` (diferencia entre escalones). Si copiás este script a otro proyecto, no reviertas ese fix.

## 8. Generar el resumen consolidado

Después de correr lo que necesites, `docs/07-resultados-experimentales.md` es donde se consolidan los números finales por sección (no los CSV crudos de `experiments/results/`, que están gitignored). Actualizalo a mano con los números nuevos, o pedí que se regenere.

## Checklist rápido antes de cualquier ronda

- [ ] `docker compose ps` — todo `healthy`, no solo "Up"
- [ ] `ffmpeg -version` / `ffprobe -version` funcionan desde la terminal que vas a usar
- [ ] Usuarios sembrados para el/los target(s) que vas a usar (`seed_test_users.py`, uno por base de datos distinta)
- [ ] Si es E3/E6: solo una carga pesada corriendo contra el host local a la vez (excepto E6, que necesita la carga constante + el fault injection simultáneos, ambos livianos)
- [ ] Si es E4: autoscaling verificado en Azure, no asumido
- [ ] Corridas largas (>2 min) van en background — revisar el CSV de resultados para progreso, no esperar el stdout
