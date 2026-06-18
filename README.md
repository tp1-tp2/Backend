# 🎙️ Plataforma ASR Quechua — Backend

> Sistema de reconocimiento automático de voz (ASR) para el idioma **quechua**, construido como arquitectura de microservicios con Python/FastAPI y un modelo Whisper fine-tuneado para quechua.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Whisper](https://img.shields.io/badge/Whisper-Quechua_finetuned-412991?logo=huggingface&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)

---

## 📐 Arquitectura

### Arquitectura Lógica

```mermaid
graph TD
    subgraph PRESENTACION["🖥️ CAPA DE PRESENTACIÓN"]
        WEB["Angular Web App<br/>(Dashboard · Subir Audio · Streaming<br/>Historial · API Docs · Configuración)"]
        SWAGGER["Swagger UI<br/>/api/docs"]
        LANDING["Landing Page<br/>(HTML · CSS · JS)"]
    end

    subgraph SERVICIOS["⚙️ CAPA DE SERVICIOS"]
        GW["🔀 API Gateway<br/>Punto de entrada único · JWT · CORS"]

        subgraph AUTH_GROUP["Identidad"]
            AUTH["🔐 Auth Service<br/>JWT HS256 · bcrypt · rate limiting"]
        end

        subgraph USER_GROUP["Usuarios"]
            USER["👤 User Service<br/>Registro · Perfil"]
        end

        subgraph AUDIO_GROUP["Procesamiento de Audio"]
            AUDIO["🎵 Audio Processor<br/>Validación · ffmpeg → WAV 16kHz mono"]
            ASR["🤖 ASR Service<br/>Whisper fine-tuned Quechua<br/>REST + WebSocket streaming"]
        end

        subgraph TRANS_GROUP["Transcripciones"]
            TRANS["📄 Transcription Manager<br/>Historial · Descarga TXT/JSON/SRT"]
        end
    end

    subgraph DATOS["🗄️ CAPA DE DATOS"]
        DB1[("auth-db\nPostgreSQL")]
        DB2[("user-db\nPostgreSQL")]
        DB3[("audio-db\nPostgreSQL")]
        DB4[("trans-db\nPostgreSQL")]
    end

    WEB -->|HTTP REST · WebSocket| GW
    SWAGGER --> GW
    LANDING -.->|enlace externo| WEB

    GW --> AUTH
    GW --> USER
    GW --> AUDIO
    GW --> TRANS
    GW -->|WS proxy| ASR
    AUDIO -->|WAV + metadata| ASR
    ASR -->|persiste resultado| TRANS

    AUTH --- DB1
    USER --- DB2
    AUDIO --- DB3
    TRANS --- DB4

    style GW fill:#1a73e8,color:#fff
    style ASR fill:#412991,color:#fff
    style PRESENTACION fill:#e8f5e9,stroke:#2e7d32
    style SERVICIOS fill:#e3f2fd,stroke:#1565c0
    style DATOS fill:#fff3e0,stroke:#e65100
```

---

### Arquitectura Física

```mermaid
graph TD
    USER_BROWSER(["👤 Usuario\nNavegador"])

    subgraph FIREBASE["🔥 Firebase Hosting"]
        FE["Angular App\n(SPA estática)"]
        LP["Landing Page\n(HTML estático)"]
    end

    subgraph AZURE["☁️ Azure Container Apps"]
        direction TB

        subgraph INGRESS["Ingress público"]
            GW_C["🔀 api-gateway\nContainer · :8000\nIngress habilitado"]
        end

        subgraph INTERNAL["Red interna (sin ingress)"]
            AUTH_C["🔐 auth-service\nContainer · :8001"]
            USER_C["👤 user-service\nContainer · :8002"]
            AUDIO_C["🎵 audio-processor\nContainer · :8003"]
            ASR_C["🤖 asr-service\nContainer · :8004\nWhisper fine-tuned"]
            TRANS_C["📄 transcription-manager\nContainer · :8005"]
        end

        subgraph VOLUME["Volumen compartido"]
            VOL[("asr_audio/\nWAV procesados")]
        end

        subgraph DATABASES["Azure Database for PostgreSQL"]
            DB1_P[("auth-db")]
            DB2_P[("user-db")]
            DB3_P[("audio-db")]
            DB4_P[("trans-db")]
        end
    end

    USER_BROWSER -->|HTTPS| FE
    USER_BROWSER -->|HTTPS| LP
    FE -->|API REST · WSS| GW_C

    GW_C --> AUTH_C
    GW_C --> USER_C
    GW_C --> AUDIO_C
    GW_C --> TRANS_C
    GW_C -->|WSS proxy| ASR_C

    AUDIO_C -->|escribe WAV| VOL
    ASR_C -->|lee WAV| VOL
    ASR_C --> TRANS_C

    AUTH_C --- DB1_P
    USER_C --- DB2_P
    AUDIO_C --- DB3_P
    TRANS_C --- DB4_P

    style GW_C fill:#1a73e8,color:#fff
    style ASR_C fill:#412991,color:#fff
    style FIREBASE fill:#fff8e1,stroke:#f9a825
    style AZURE fill:#e3f2fd,stroke:#1565c0
    style INGRESS fill:#bbdefb,stroke:#1976d2
    style INTERNAL fill:#e8eaf6,stroke:#3949ab
    style VOLUME fill:#f3e5f5,stroke:#7b1fa2
    style DATABASES fill:#e8f5e9,stroke:#388e3c
```

---

### Responsabilidades por servicio

| Servicio | Puerto | Responsabilidad |
|---|---|---|
| **api-gateway** | 8000 | Punto de entrada único; enruta, autentica con JWT, agrega el dashboard |
| **auth-service** | 8001 | Emisión de JWT (HS256), bcrypt, rate limiting, recuperación de contraseña |
| **user-service** | 8002 | Registro, perfil de usuario, cambio de email |
| **audio-processor** | 8003 | Validación de formato/tamaño, conversión con ffmpeg, reenvío a ASR |
| **asr-service** | 8004 | Transcripción con `QuechuaBase/whisper-base-qxp-finetuned` (Puno Quechua), streaming WebSocket |
| **transcription-manager** | 8005 | Historial paginado, descarga en TXT / JSON / SRT |

---

## ✅ Requisitos previos

| Herramienta | Versión | Notas |
|---|---|---|
| **Docker Desktop** | 24 + | Modo **Linux containers** en Windows |
| **Git** | 2.x | — |
| **RAM disponible** | 4 GB | Whisper-base fine-tuned usa ~1 GB en inferencia CPU |
| **Espacio en disco** | 4 GB | Imágenes Docker + modelo HuggingFace (~300 MB) |

> **Windows**: verificar que Docker Desktop esté en modo Linux containers antes de continuar.

---

## 🚀 Inicio rápido

### 1 · Clonar el repositorio

```bash
git clone <url-del-repo>
cd tp1-tp2/Backend
```

### 2 · Crear el archivo `.env`

Crear un archivo `.env` en la **raíz del proyecto** (`Backend/.env`):

```env
JWT_SECRET_KEY=reemplaza_esto_con_una_clave_de_al_menos_32_caracteres
```

Para generar una clave segura:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> Si no se define `JWT_SECRET_KEY`, se usará `changeme_in_production`. **No apto para ningún entorno compartido.**

### 3 · Build e inicio

```bash
docker compose up --build
```

La primera ejecución realiza automáticamente:

1. Construye las 6 imágenes Docker
2. Descarga el modelo **[QuechuaBase/whisper-base-qxp-finetuned](https://huggingface.co/QuechuaBase/whisper-base-qxp-finetuned)** desde HuggingFace — puede tardar varios minutos
3. Levanta las 4 bases de datos PostgreSQL y espera a que estén listas (`pg_isready`)
4. Ejecuta las migraciones **Alembic** (`alembic upgrade head`) en cada servicio
5. Inicia todos los servicios; el gateway espera a que los 4 pasen su healthcheck

### 4 · Verificar que todo está healthy

```bash
docker compose ps
```

Todos los contenedores deben mostrar `(healthy)`:

```
backend-api-gateway-1             Up (healthy)   0.0.0.0:8000->8000/tcp
backend-auth-service-1            Up (healthy)   0.0.0.0:8001->8000/tcp
backend-user-service-1            Up (healthy)   0.0.0.0:8002->8000/tcp
backend-audio-processor-1         Up (healthy)   0.0.0.0:8003->8000/tcp
backend-asr-service-1             Up (healthy)   0.0.0.0:8004->8000/tcp
backend-transcription-manager-1   Up (healthy)   0.0.0.0:8005->8000/tcp
```

### 5 · Probar el API

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "service": "api-gateway",
  "version": "1.0.0"
}
```

📖 Swagger UI interactivo: **http://localhost:8000/api/docs**

---

## 🔌 URLs de los servicios

| Servicio | URL (host) | Swagger UI |
|---|---|---|
| **API Gateway** *(público)* | http://localhost:8000 | http://localhost:8000/api/docs |
| Auth Service | http://localhost:8001 | http://localhost:8001/docs |
| User Service | http://localhost:8002 | http://localhost:8002/docs |
| Audio Processor | http://localhost:8003 | http://localhost:8003/docs |
| ASR Service | http://localhost:8004 | http://localhost:8004/docs |
| Transcription Manager | http://localhost:8005 | http://localhost:8005/docs |

> En producción, **solo el API Gateway** tiene ingress público. El resto son servicios internos.

### Endpoints principales (vía Gateway)

```
# Autenticación
POST   /api/v1/auth/register          Registro de usuario
POST   /api/v1/auth/login             Login → JWT
POST   /api/v1/auth/logout            Logout (invalida el token)
POST   /api/v1/auth/password-recovery Solicitar recuperación
POST   /api/v1/auth/password-reset    Resetear contraseña con token

# Perfil
GET    /api/v1/users/profile          Ver perfil  [JWT requerido]
PUT    /api/v1/users/profile          Actualizar perfil

# Dashboard
GET    /api/v1/dashboard              Perfil + resumen + estado de servicios

# Transcripción
POST   /api/v1/transcribe             Subir audio → transcripción ASR
GET    /api/v1/transcriptions         Historial paginado
GET    /api/v1/transcriptions/{id}    Detalle con word confidences
GET    /api/v1/transcriptions/{id}/download?format=txt|json|srt

# Streaming
WS     /ws/stream?token=<jwt>         Streaming en tiempo real (WebSocket)
```

---

## ⚙️ Variables de entorno

### `.env` en la raíz del proyecto

| Variable | Requerida | Default | Descripción |
|---|---|---|---|
| `JWT_SECRET_KEY` | **Sí** | `changeme_in_production` | Clave HMAC-SHA256 para firmar JWT (≥ 32 chars) |
| `STORAGE_URL` | No | `local` | URL de almacenamiento de audio |

### Configuración avanzada por servicio

Cada servicio acepta variables de entorno propias que se pueden sobreescribir en `docker-compose.yml` o en un `.env` local:

<details>
<summary>Ver variables completas por servicio</summary>

**auth-service**
| Variable | Default |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://auth_user:auth_pass@auth-db:5432/auth_db` |
| `JWT_SECRET_KEY` | `changeme_in_production` |
| `JWT_EXPIRATION_HOURS` | `24` |
| `BCRYPT_ROUNDS` | `12` |
| `RATE_LIMIT_ATTEMPTS` | `5` |
| `RATE_LIMIT_WINDOW_MINUTES` | `15` |

**asr-service**
| Variable | Default |
|---|---|
| `MODEL_ID` | `QuechuaBase/whisper-base-qxp-finetuned` |
| `DEVICE` | `cpu` (`cuda` para GPU) |
| `AUTH_SERVICE_URL` | `http://auth-service:8000` |
| `TRANSCRIPTION_MANAGER_URL` | `http://transcription-manager:8000` |

Para cambiar el modelo HuggingFace:
```bash
# En docker-compose.yml, cambiar:
MODEL_ID=QuechuaBase/whisper-base-qxp-finetuned
```
</details>

---

## 🧪 Ejecutar tests

Cada servicio tiene su propio conjunto de tests con pytest. Requiere **Python 3.11+** instalado localmente.

### Tests de un servicio

```bash
cd services/auth-service
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing -v
```

### Todos los servicios (script)

```bash
for svc in auth-service user-service audio-processor asr-service transcription-manager api-gateway; do
  echo "=== $svc ==="
  (cd services/$svc && pip install -r requirements.txt -r requirements-dev.txt -q && pytest --tb=short -q)
done
```

### Tests E2E (gateway)

```bash
cd services/api-gateway
pytest tests/e2e/ -v
```

### Tests de propiedades con Hypothesis

```bash
# Audio Processor — metadatos de audio
cd services/audio-processor && pytest tests/property/ -v

# API Gateway — payloads de registro
cd services/api-gateway && pytest tests/property/ -v
```

---

## 💻 Desarrollo local sin Docker

Para modificar un servicio sin reconstruir la imagen completa:

### 1 · Levantar solo las bases de datos

```bash
docker compose up auth-db user-db audio-db trans-db -d
```

### 2 · Crear entorno virtual e instalar dependencias

```bash
cd services/auth-service
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 3 · Configurar variables de entorno

```bash
export DATABASE_URL="postgresql+asyncpg://auth_user:auth_pass@localhost:5432/auth_db"
export JWT_SECRET_KEY="dev_secret_al_menos_32_chars_aqui"
```

### 4 · Ejecutar migraciones y arrancar

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

---

## 🗂️ Estructura del proyecto

```
Backend/
├── docker-compose.yml              # Orquestación local completa
├── .env                            # Variables de entorno (no commitear)
│
├── services/
│   ├── api-gateway/                # 🔀 Punto de entrada único (puerto 8000)
│   │   ├── app/
│   │   │   ├── api/routes/         # auth, users, dashboard, transcriptions, streaming
│   │   │   └── core/               # config, exceptions, response envelope
│   │   └── tests/
│   │       ├── e2e/                # Tests de integración E2E (11 flows)
│   │       └── property/           # Tests de propiedades Hypothesis
│   │
│   ├── auth-service/               # 🔐 JWT, bcrypt, blocklist (puerto 8001)
│   │   ├── app/
│   │   │   ├── models/             # UserCredential, TokenBlocklist, PasswordRecoveryToken
│   │   │   ├── services/           # AuthService, RateLimiter
│   │   │   └── core/security.py   # JWT, bcrypt, SHA-256
│   │   └── alembic/                # Migraciones DB
│   │
│   ├── user-service/               # 👤 Registro y perfiles (puerto 8002)
│   │   ├── app/
│   │   │   ├── models/             # UserProfile, EmailChangeRequest
│   │   │   └── services/           # UserService
│   │   └── alembic/
│   │
│   ├── audio-processor/            # 🎵 Validación y conversión de audio (puerto 8003)
│   │   ├── app/
│   │   │   ├── models/             # AudioFile
│   │   │   └── services/           # AudioService, FfmpegService, MetadataService
│   │   └── alembic/
│   │
│   ├── asr-service/                # 🤖 Whisper + WebSocket streaming (puerto 8004)
│   │   └── app/services/           # WhisperService, StreamingService
│   │
│   └── transcription-manager/      # 📄 Historial y descarga (puerto 8005)
│       ├── app/
│       │   ├── models/             # Transcription, WordConfidence
│       │   └── services/           # TranscriptionService, DownloadService
│       └── alembic/
│
└── contexto/
    └── tasks.md                    # Backlog y trazabilidad de historias de usuario
```

---

## 🛠️ Comandos útiles

```bash
# Ver logs de un servicio
docker compose logs -f auth-service

# Reiniciar un servicio sin reconstruir
docker compose restart user-service

# Reconstruir y reiniciar un servicio específico
docker compose up --build auth-service -d

# Parar todo (conserva los datos de las DBs)
docker compose down

# Parar todo y borrar datos (reset completo)
docker compose down -v

# Conectarse a una base de datos
docker compose exec auth-db psql -U auth_user -d auth_db

# Ver estado de migraciones
docker compose exec auth-service alembic current
docker compose exec auth-service alembic history
```

---

## ⚠️ Notas importantes

<details>
<summary><strong>Primera ejecución — modelo ASR Quechua</strong></summary>

El servicio `asr-service` descarga **[QuechuaBase/whisper-base-qxp-finetuned](https://huggingface.co/QuechuaBase/whisper-base-qxp-finetuned)** desde HuggingFace durante la primera construcción de la imagen. Este proceso puede tardar entre 2 y 10 minutos dependiendo de la conexión a internet.

El modelo es un **Whisper-base fine-tuneado para Puno Quechua (qxp)** usando datos de Mozilla Common Voice. Usa la librería `transformers` (no `openai-whisper`).

Las siguientes ejecuciones son instantáneas porque el modelo queda cacheado en el volumen Docker `/root/.cache/huggingface`.

Para cambiar el modelo (por ejemplo a otro fine-tune de quechua):
```bash
# En docker-compose.yml, bajo asr-service > environment:
- MODEL_ID=otro-usuario/otro-modelo-quechua
```

</details>

<details>
<summary><strong>Migraciones automáticas al iniciar</strong></summary>

Todos los servicios con base de datos ejecutan `alembic upgrade head` automáticamente antes de arrancar uvicorn. El `CMD` del Dockerfile es:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Si la base de datos no está lista, el contenedor falla y Docker lo reinicia gracias a `restart: on-failure`. Los healthchecks de PostgreSQL con `pg_isready` garantizan el orden correcto de arranque.

</details>

<details>
<summary><strong>Streaming WebSocket — ejemplo con wscat</strong></summary>

```bash
# Instalar wscat
npm install -g wscat

# 1. Obtener JWT
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"password123"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 2. Conectar al stream
wscat -c "ws://localhost:8000/ws/stream?token=$TOKEN"

# 3. Enviar chunks de audio (base64) y recibir transcripciones parciales en tiempo real
```

</details>
