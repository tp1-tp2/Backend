# Fase 2 — Baseline monolítico (`services/monolith-baseline/`)

## Qué problema resuelve

**E3** del protocolo experimental exige comparar la arquitectura propuesta (microservicios + adaptación en tiempo de ejecución) contra "una versión monolítica de control: un único proceso... sin separación de responsabilidades ni conmutación CPU/GPU dinámica (dispositivo fijo)". Sin este control, no hay nada contra qué medir el beneficio arquitectónico — E3 es el experimento que sostiene la afirmación de RQ3 (desempeño arquitectónico) y de aislamiento de fallos.

## Qué se portó de dónde

| Origen | Qué se trajo | Qué se dejó fuera (fuera de alcance para E3/E4/E6) |
|---|---|---|
| `auth-service` | `core/security.py` (PyJWT HS256 + bcrypt, verbatim), modelo `UserCredential` + `TokenBlocklist`, lógica de login/logout | Rate limiting, recuperación de contraseña, SMTP |
| `user-service` | Modelo `UserProfile`, flujo de registro | Cambio de email, verificación de email |
| `audio-processor` | `ffmpeg_service.py` (verbatim), `metadata_service.py` (verbatim), modelo `AudioFile`, validación de formato/tamaño | — |
| `asr-service` | `whisper_service.py` **sin** `device_manager.py` — carga el modelo una sola vez con `settings.device` fijo | Todo el mecanismo de adaptación (deliberado — es justo el contraste que mide E3) |
| `transcription-manager` | Modelos `Transcription`/`WordConfidence`, historial paginado, columnas `device_used`/`compute_type` (siempre el valor fijo del proceso) | Descarga TXT/JSON/SRT |

**Diferencia arquitectónica clave**: los 3 saltos HTTP que hace la arquitectura real (audio-processor → asr-service → transcription-manager) se reemplazan por **llamadas directas de función Python** dentro del mismo request handler (`app/services/pipeline_service.py::process_upload`). Esto es literalmente "sin separación de responsabilidades" — todo vive en el mismo espacio de ejecución, sin red de por medio.

## Por qué `--workers 1`

El modelo Whisper vive en un global a nivel de módulo (`_pipe` en `whisper_service.py`), igual que en `asr-service`. Con múltiples workers Uvicorn se cargaría el modelo N veces (N× memoria, N× tiempo de arranque). **Esto es en sí mismo una desventaja arquitectónica citable para E3**: la arquitectura separada corre auth/audio/persistencia a `--workers 4`; el monolito reduce *todo* a 1 worker porque el ASR comparte proceso con el resto.

## Endpoints expuestos

Mismas rutas públicas que la pila real, para que el script de carga de E4 funcione contra cualquiera de las dos arquitecturas solo cambiando la URL base:

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/transcribe
GET    /api/v1/transcriptions
GET    /api/v1/transcriptions/{id}
GET    /health
```

## Esquema de base de datos

Un solo chain de Alembic fresco (`alembic/versions/0001_initial.py`), no injertado de las 4 cadenas reales (cada una con `down_revision=None`, independientes entre sí) — más simple y correcto para un servicio nuevo. Confirmado sin colisiones de nombres de tabla ni necesidad de resolver conflictos: `user_id` es `String(36)` consistente en todas partes, sin `ForeignKey` cruzados hoy (por diseño, ya que en la pila real viven en bases de datos separadas).

## Cómo correrlo

```bash
docker compose up --build monolith-baseline
```

Para baseline en GPU (comparación simétrica con las corridas adaptativas de `asr-service`):

```bash
MONOLITH_DEVICE=cuda docker compose up --build monolith-baseline
```

Puerto `8006`. Base de datos propia (`monolith-db`, Postgres 16) para no interferir con las 4 bases de la pila real.

## Archivos

Estructura completa bajo `services/monolith-baseline/`: `app/core/` (config, security, exceptions), `app/models/` (credential, user, audio, transcription), `app/schemas/`, `app/services/` (ffmpeg_service, metadata_service, whisper_service, auth_service, pipeline_service), `app/api/routes/` (auth, transcriptions), `app/main.py`, `Dockerfile`, `requirements.txt`, `alembic/`. Ver también `docker-compose.yml` (servicios `monolith-baseline` + `monolith-db`).

## Verificación realizada

Todos los archivos Python pasan `python -m py_compile` sin errores. `docker-compose.yml` validado como YAML sintácticamente correcto con los 2 servicios nuevos presentes.

**Pendiente** (requiere Docker + build del modelo): `docker compose up --build monolith-baseline`, ejercitar register → login → transcribe → list end-to-end, confirmar que no hay llamadas salientes a los otros 5 servicios (revisar logs / `docker network` — no debería haber tráfico hacia `auth-service`, `audio-processor`, etc. porque el monolito no los conoce).
