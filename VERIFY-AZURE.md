# Verificación en Azure — Stack actualizado (Fases 1-4)

Este documento tiene dos partes:

- **Parte 1** — la corres **tú** (dueño de `ghcr.io/zrodrigochirinos`): build + push de las 6 imágenes actualizadas con los cambios de las Fases 1-4 (mecanismo adaptativo, columnas `device_used`/`compute_type`, soporte de códecs en streaming).
- **Parte 2** — se la pasas **a tu amigo**: despliegue completo en Azure Container Apps usando sus propios créditos, puro Azure CLI, listo para copiar y pegar. Solo necesita reemplazar 3 valores marcados `<CAMBIAR>`.

**Costo estimado para tu amigo**: ~$40-50/mes mientras esté arriba (ver `DEPLOY.md` de este mismo repo para cómo pausar/apagar sin perder datos). Azure Container Apps Consumption plan **no tiene GPU** — esto verifica que el mecanismo adaptativo funciona (arranca, expone `/status/adaptation`, persiste `device_used`/`compute_type`, y la rama de precisión CPU fp32↔int8 reacciona a presión de CPU), pero **no** la rama de conmutación CPU↔GPU (necesita hardware con GPU, que ya probaste localmente).

---

## Parte 1 — Build & push (tu terminal, PowerShell)

```powershell
cd .....\GitHub\tp1-tp2\Backend

$GHCR_TOKEN = "...."
$GHCR_USER  = "zrodrigochirinos"
echo $GHCR_TOKEN | docker login ghcr.io -u $GHCR_USER --password-stdin

$services = @("auth-service","user-service","audio-processor","transcription-manager","asr-service","api-gateway")
foreach ($svc in $services) {
    docker build -t "ghcr.io/$GHCR_USER/${svc}:latest" "services/$svc"
    docker push "ghcr.io/$GHCR_USER/${svc}:latest"
}
```

> `asr-service` ahora instala `ffmpeg` además de `libsndfile1` (Fase 4) y pesa un poco más — el build va a tardar más que antes por eso, no es un error.

Confirma que las 6 imágenes siguen **públicas** en github.com/zrodrigochirinos → Packages (deberían seguirlo estando de la vez anterior, pero revisa por si acaso).

---

## Parte 2 — Deploy en Azure (PowerShell)

### 2.1 · Prerequisitos

```powershell
# Instalar Azure CLI si no lo tiene
winget install Microsoft.AzureCLI

# Login (usa su propia cuenta con créditos de estudiante)
az login --use-device-code
```

Después del login, confirmar la suscripción correcta:

```powershell
az account list --output table
az account set --subscription "<CAMBIAR: su Subscription ID de Azure for Students>"
```

### 2.2 · Variables (definir una sola vez, se reutilizan en todos los pasos siguientes)

```powershell
$RG        = "rg-asr-verify"
$ENV_NAME  = "aca-asr-verify"
$LOCATION  = "canadacentral"   # Azure for Students suele bloquear ACR/AKS/ACA en la mayoría de regiones — canadacentral funcionó en la cuenta original. Si falla, probar westus2, eastus2, northeurope.
$DB_HOST   = "pg-asr-verify"   # debe ser único globalmente en Azure — si "pg-asr-verify" ya existe, agregar sufijo (ej. pg-asr-verify-01)
$DB_PASS   = "<CAMBIAR: una contraseña fuerte para Postgres>"
$JWT_SECRET = "<CAMBIAR: genera con: python -c 'import secrets; print(secrets.token_hex(32))'>"
$GHCR_USER = "CAMBIAR"
```

### 2.3 · Resource group + ACA environment

```powershell
az group create --name $RG --location $LOCATION

az containerapp env create `
  --name $ENV_NAME `
  --resource-group $RG `
  --location $LOCATION
```

### 2.4 · PostgreSQL (un solo servidor, 4 bases de datos)

```powershell
az postgres flexible-server create `
  --name $DB_HOST `
  --resource-group $RG `
  --location $LOCATION `
  --admin-user pgadmin `
  --admin-password $DB_PASS `
  --sku-name Standard_B1ms `
  --tier Burstable `
  --version 16 `
  --public-access 0.0.0.0

az postgres flexible-server db create --server-name $DB_HOST --resource-group $RG --name auth_db
az postgres flexible-server db create --server-name $DB_HOST --resource-group $RG --name user_db
az postgres flexible-server db create --server-name $DB_HOST --resource-group $RG --name audio_db
az postgres flexible-server db create --server-name $DB_HOST --resource-group $RG --name trans_db
```

### 2.5 · Desplegar los 6 servicios

```powershell
$DB_FQDN = "$DB_HOST.postgres.database.azure.com"

# auth-service (interno)
az containerapp create `
  --name auth-service --resource-group $RG --environment $ENV_NAME `
  --image "ghcr.io/$GHCR_USER/auth-service:latest" `
  --cpu 0.5 --memory 1Gi --min-replicas 1 --max-replicas 1 `
  --ingress internal --target-port 8000 `
  --env-vars `
    "DATABASE_URL=postgresql+asyncpg://pgadmin:${DB_PASS}@${DB_FQDN}/auth_db?ssl=require" `
    "JWT_SECRET_KEY=${JWT_SECRET}" `
    "JWT_ALGORITHM=HS256" "JWT_EXPIRATION_HOURS=24" "BCRYPT_ROUNDS=12" `
    "RATE_LIMIT_ATTEMPTS=5" "RATE_LIMIT_WINDOW_MINUTES=15" "RECOVERY_TOKEN_EXPIRY_HOURS=1" `
    "SMTP_HOST=smtp.gmail.com" "SMTP_PORT=587" "SMTP_USER=" "SMTP_PASSWORD=" `
    "SMTP_FROM=noreply@asr-quechua.com" "FRONTEND_URL=http://localhost:4200"

# user-service (interno)
az containerapp create `
  --name user-service --resource-group $RG --environment $ENV_NAME `
  --image "ghcr.io/$GHCR_USER/user-service:latest" `
  --cpu 0.5 --memory 1Gi --min-replicas 1 --max-replicas 1 `
  --ingress internal --target-port 8000 `
  --env-vars `
    "DATABASE_URL=postgresql+asyncpg://pgadmin:${DB_PASS}@${DB_FQDN}/user_db?ssl=require" `
    "AUTH_SERVICE_URL=http://auth-service" `
    "EMAIL_CONFIRMATION_TIMEOUT_SECONDS=30" "EMAIL_CHANGE_EXPIRY_HOURS=24" "MIN_AGE_YEARS=13" `
    "SMTP_HOST=smtp.gmail.com" "SMTP_PORT=587" "SMTP_USER=" "SMTP_PASSWORD=" `
    "SMTP_FROM=noreply@asr-quechua.com" "FRONTEND_URL=http://localhost:4200"

# transcription-manager (interno) — tiene las columnas nuevas device_used/compute_type (Fase 1)
az containerapp create `
  --name transcription-manager --resource-group $RG --environment $ENV_NAME `
  --image "ghcr.io/$GHCR_USER/transcription-manager:latest" `
  --cpu 0.5 --memory 1Gi --min-replicas 1 --max-replicas 1 `
  --ingress internal --target-port 8000 `
  --env-vars `
    "DATABASE_URL=postgresql+asyncpg://pgadmin:${DB_PASS}@${DB_FQDN}/trans_db?ssl=require"

# audio-processor (interno)
az containerapp create `
  --name audio-processor --resource-group $RG --environment $ENV_NAME `
  --image "ghcr.io/$GHCR_USER/audio-processor:latest" `
  --cpu 0.5 --memory 1Gi --min-replicas 1 --max-replicas 1 `
  --ingress internal --target-port 8000 `
  --env-vars `
    "DATABASE_URL=postgresql+asyncpg://pgadmin:${DB_PASS}@${DB_FQDN}/audio_db?ssl=require" `
    "ASR_SERVICE_URL=http://asr-service"

# asr-service (interno, 2 CPU / 4GB — Whisper) — mecanismo adaptativo de la Fase 1
az containerapp create `
  --name asr-service --resource-group $RG --environment $ENV_NAME `
  --image "ghcr.io/$GHCR_USER/asr-service:latest" `
  --cpu 2.0 --memory 4Gi --min-replicas 1 --max-replicas 1 `
  --ingress internal --target-port 8000 `
  --env-vars `
    "MODEL_ID=QuechuaBase/whisper-base-qxp-finetuned" `
    "DEVICE=cpu" "ADAPTIVE_MODE=true" `
    "AUTH_SERVICE_URL=http://auth-service" `
    "TRANSCRIPTION_MANAGER_URL=http://transcription-manager" `
    "MAX_CONCURRENT_CONNECTIONS=100" "STREAMING_PARTIAL_INTERVAL_SECONDS=3" `
    "AUDIO_BUFFER_MAX_SECONDS=600" "PARTIAL_WINDOW_SECONDS=10"

# api-gateway (externo — único con ingress público)
az containerapp create `
  --name api-gateway --resource-group $RG --environment $ENV_NAME `
  --image "ghcr.io/$GHCR_USER/api-gateway:latest" `
  --cpu 0.5 --memory 1Gi --min-replicas 1 --max-replicas 1 `
  --ingress external --target-port 8000 `
  --env-vars `
    "AUTH_SERVICE_URL=http://auth-service" `
    "USER_SERVICE_URL=http://user-service" `
    "AUDIO_PROCESSOR_URL=http://audio-processor" `
    "ASR_SERVICE_URL=http://asr-service" `
    "TRANSCRIPTION_MANAGER_URL=http://transcription-manager"
```

### 2.6 · Obtener la URL pública y probar

```powershell
az containerapp show --name api-gateway --resource-group $RG --query "properties.configuration.ingress.fqdn" --output tsv
```

```powershell
$GATEWAY_URL = "https://" + (az containerapp show --name api-gateway --resource-group $RG --query "properties.configuration.ingress.fqdn" --output tsv)

# 1. Health check
curl "$GATEWAY_URL/health"

# 2. Registro + login
curl -X POST "$GATEWAY_URL/api/v1/auth/register" -H "Content-Type: application/json" -d '{"email":"verify@test.com","password":"VerifyPass123!","full_name":"Verify Test"}'
curl -X POST "$GATEWAY_URL/api/v1/auth/login" -H "Content-Type: application/json" -d '{"email":"verify@test.com","password":"VerifyPass123!"}'
# guardar el "token" de la respuesta
```

### 2.7 · Verificar el mecanismo adaptativo (Fase 1) — lo específico de esta verificación

`asr-service` no tiene ingress público, así que se revisa vía logs (no se puede hacer `curl` directo desde afuera):

```powershell
az containerapp logs show --name asr-service --resource-group $RG --tail 30
# buscar: "Model loaded successfully (device=cpu, compute_type=fp32)"
# y: "Device adaptation monitor started"
```

Para ver `/status/adaptation` en vivo, usar `az containerapp exec` para correr un comando dentro del contenedor. **Nota**: la imagen de `asr-service` no tiene `curl` instalado (solo `ffmpeg`/`libsndfile1`) — usar Python, que sí está garantizado:

```powershell
az containerapp exec --name asr-service --resource-group $RG --command "python -c `"import urllib.request; print(urllib.request.urlopen('http://localhost:8000/status/adaptation').read().decode())`""
```

Debe devolver JSON con `current.device: "cpu"`, un `last_hardware_snapshot` con datos reales de CPU/RAM del contenedor, y `recent_decisions: []` (vacío al principio, se va llenando si hay presión de CPU sostenida).

### 2.8 · Transcribir un audio y confirmar `device_used`/`compute_type`

```powershell
$TOKEN = "<pegar el token del paso 2.6>"
curl -X POST "$GATEWAY_URL/api/v1/transcribe" -H "Authorization: Bearer $TOKEN" -F "file=@C:\ruta\a\un\audio.wav"
```

La respuesta debe incluir `"device_used": "cpu"` y `"compute_type": "fp32"` — confirma que el stamping de la Fase 1 llega hasta el cliente y (revisando la base de datos) hasta Postgres.

```powershell
# az postgres flexible-server execute requiere la extensión rdbms-connect (una sola vez):
az extension add --name rdbms-connect

az postgres flexible-server execute `
  --name $DB_HOST --admin-user pgadmin --admin-password $DB_PASS `
  --database-name trans_db `
  --querytext "SELECT transcription_id, device_used, compute_type FROM transcriptions LIMIT 5;"
```

---

## Parte 3 (opcional) — `monolith-baseline`

`monolith-baseline` es el control experimental de E3 (Fase 2) — está pensado para correr **localmente** vía `docker compose` (necesita comparar dispositivo fijo vs. adaptativo con GPU real, que Azure Container Apps no tiene). No es necesario desplegarlo en Azure para esta verificación. Si igual quieren probar que arma y arranca correctamente en contenedor, avísenme y agrego los pasos — no están en este doc porque no aporta a lo que ACA puede verificar (no hay GPU para el contraste real).

---

## Apagar / limpiar cuando terminen

```powershell
# Pausar (conserva datos, corta el gasto de cómputo):
foreach ($svc in @("auth-service","user-service","audio-processor","transcription-manager","asr-service","api-gateway")) {
  az containerapp update --name $svc --resource-group $RG --min-replicas 0
}
az postgres flexible-server stop --name $DB_HOST --resource-group $RG

# Borrar todo (irreversible):
az group delete --name $RG --yes --no-wait
```
