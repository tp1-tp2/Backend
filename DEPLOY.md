# ASR Quechua — Azure Container Apps Deployment

> **Nota**: `monolith-baseline` (control experimental para E3) y `experiments/`
> (herramientas de medición E1-E7) son **solo para uso local** — corren vía
> `docker compose`, no se despliegan a Azure. Ver `docs/02-monolith-baseline.md`
> y `experiments/README.md`.

## Infrastructure

| Resource | Value |
|---|---|
| Subscription | `cfcab251-b0bf-45d7-8a11-b78b26aa6992` |
| Resource Group | `rg-asr-quechua` |
| ACA Environment | `aca-asr-quechua` (Canada Central) |
| PostgreSQL | `pg-asr-quechua.postgres.database.azure.com` |
| Registry | `ghcr.io/zrodrigochirinos` (public images) |
| Public URL | `https://api-gateway.lemonisland-cf2679ea.canadacentral.azurecontainerapps.io` |
| Swagger UI | `https://api-gateway.lemonisland-cf2679ea.canadacentral.azurecontainerapps.io/api/docs` |

---

## Prerequisites

```powershell
# Install Azure CLI (if not installed)
winget install Microsoft.AzureCLI

# Login
az login --use-device-code

# Set subscription
az account set --subscription cfcab251-b0bf-45d7-8a11-b78b26aa6992
```

---

## Build & Push Images

Run from `Backend/` root. Requires Docker Desktop running and a GitHub token with `write:packages` scope.

```powershell
$GHCR_TOKEN = "your_github_token"
$GHCR_USER  = "zrodrigochirinos"

echo $GHCR_TOKEN | docker login ghcr.io -u $GHCR_USER --password-stdin

$services = @("auth-service","user-service","audio-processor","transcription-manager","asr-service","api-gateway")

foreach ($svc in $services) {
    docker build -t "ghcr.io/$GHCR_USER/${svc}:latest" "services/$svc"
    docker push "ghcr.io/$GHCR_USER/${svc}:latest"
}
```

> Images must be set to **Public** on GitHub (Packages → each package → Settings → Change visibility).

---

## Deploy — Bring Up

### 1. Create resource group (first time only)

```powershell
az group create --name rg-asr-quechua --location canadacentral
```

### 2. Create ACA environment (first time only)

```powershell
az containerapp env create `
  --name aca-asr-quechua `
  --resource-group rg-asr-quechua `
  --location canadacentral
```

### 3. Create PostgreSQL server and databases (first time only)

```powershell
az postgres flexible-server create `
  --name pg-asr-quechua `
  --resource-group rg-asr-quechua `
  --location canadacentral `
  --admin-user pgadmin `
  --admin-password "YOUR_DB_PASSWORD" `
  --sku-name Standard_B1ms `
  --tier Burstable `
  --version 16 `
  --public-access 0.0.0.0

az postgres flexible-server db create --server-name pg-asr-quechua --resource-group rg-asr-quechua --name auth_db
az postgres flexible-server db create --server-name pg-asr-quechua --resource-group rg-asr-quechua --name user_db
az postgres flexible-server db create --server-name pg-asr-quechua --resource-group rg-asr-quechua --name audio_db
az postgres flexible-server db create --server-name pg-asr-quechua --resource-group rg-asr-quechua --name trans_db
```

### 4. Deploy all services

Replace every `CHANGE_ME` with the real value before running.

```powershell
$RG       = "rg-asr-quechua"
$ENV      = "aca-asr-quechua"
$DB_HOST  = "pg-asr-quechua.postgres.database.azure.com"
$DB_PASS  = "YOUR_DB_PASSWORD"
$JWT      = "YOUR_JWT_SECRET"
$SMTP_U   = "YOUR_GMAIL"
$SMTP_P   = "YOUR_APP_PASSWORD"
$SMTP_F   = "YOUR_GMAIL"
$FRONTEND = "https://asr-quechua-frontend-b722a.web.app"

# auth-service (internal)
az containerapp create `
  --name auth-service `
  --resource-group $RG `
  --environment $ENV `
  --image ghcr.io/zrodrigochirinos/auth-service:latest `
  --cpu 0.5 --memory 1Gi `
  --min-replicas 1 --max-replicas 1 `
  --ingress internal --target-port 8000 `
  --env-vars `
    "DATABASE_URL=postgresql+asyncpg://pgadmin:${DB_PASS}@${DB_HOST}/auth_db?ssl=require" `
    "JWT_SECRET_KEY=${JWT}" `
    "JWT_ALGORITHM=HS256" `
    "JWT_EXPIRATION_HOURS=24" `
    "BCRYPT_ROUNDS=12" `
    "RATE_LIMIT_ATTEMPTS=5" `
    "RATE_LIMIT_WINDOW_MINUTES=15" `
    "RECOVERY_TOKEN_EXPIRY_HOURS=1" `
    "SMTP_HOST=smtp.gmail.com" `
    "SMTP_PORT=587" `
    "SMTP_USER=${SMTP_U}" `
    "SMTP_PASSWORD=${SMTP_P}" `
    "SMTP_FROM=${SMTP_F}" `
    "FRONTEND_URL=${FRONTEND}"

# user-service (internal)
az containerapp create `
  --name user-service `
  --resource-group $RG `
  --environment $ENV `
  --image ghcr.io/zrodrigochirinos/user-service:latest `
  --cpu 0.5 --memory 1Gi `
  --min-replicas 1 --max-replicas 1 `
  --ingress internal --target-port 8000 `
  --env-vars `
    "DATABASE_URL=postgresql+asyncpg://pgadmin:${DB_PASS}@${DB_HOST}/user_db?ssl=require" `
    "AUTH_SERVICE_URL=http://auth-service" `
    "EMAIL_CONFIRMATION_TIMEOUT_SECONDS=30" `
    "EMAIL_CHANGE_EXPIRY_HOURS=24" `
    "MIN_AGE_YEARS=13" `
    "SMTP_HOST=smtp.gmail.com" `
    "SMTP_PORT=587" `
    "SMTP_USER=${SMTP_U}" `
    "SMTP_PASSWORD=${SMTP_P}" `
    "SMTP_FROM=${SMTP_F}" `
    "FRONTEND_URL=${FRONTEND}"

# transcription-manager (internal)
az containerapp create `
  --name transcription-manager `
  --resource-group $RG `
  --environment $ENV `
  --image ghcr.io/zrodrigochirinos/transcription-manager:latest `
  --cpu 0.5 --memory 1Gi `
  --min-replicas 1 --max-replicas 1 `
  --ingress internal --target-port 8000 `
  --env-vars `
    "DATABASE_URL=postgresql+asyncpg://pgadmin:${DB_PASS}@${DB_HOST}/trans_db?ssl=require"

# audio-processor (internal)
az containerapp create `
  --name audio-processor `
  --resource-group $RG `
  --environment $ENV `
  --image ghcr.io/zrodrigochirinos/audio-processor:latest `
  --cpu 0.5 --memory 1Gi `
  --min-replicas 1 --max-replicas 1 `
  --ingress internal --target-port 8000 `
  --env-vars `
    "DATABASE_URL=postgresql+asyncpg://pgadmin:${DB_PASS}@${DB_HOST}/audio_db?ssl=require" `
    "ASR_SERVICE_URL=http://asr-service"

# asr-service (internal, high CPU/RAM for model)
az containerapp create `
  --name asr-service `
  --resource-group $RG `
  --environment $ENV `
  --image ghcr.io/zrodrigochirinos/asr-service:latest `
  --cpu 2.0 --memory 4Gi `
  --min-replicas 1 --max-replicas 1 `
  --ingress internal --target-port 8000 `
  --env-vars `
    "MODEL_ID=QuechuaBase/whisper-base-qxp-finetuned" `
    "DEVICE=cpu" `
    "AUTH_SERVICE_URL=http://auth-service" `
    "TRANSCRIPTION_MANAGER_URL=http://transcription-manager" `
    "MAX_CONCURRENT_CONNECTIONS=100" `
    "STREAMING_PARTIAL_INTERVAL_SECONDS=3" `
    "AUDIO_BUFFER_MAX_SECONDS=600" `
    "PARTIAL_WINDOW_SECONDS=10"

# api-gateway (external — public internet)
az containerapp create `
  --name api-gateway `
  --resource-group $RG `
  --environment $ENV `
  --image ghcr.io/zrodrigochirinos/api-gateway:latest `
  --cpu 0.5 --memory 1Gi `
  --min-replicas 1 --max-replicas 1 `
  --ingress external --target-port 8000 `
  --env-vars `
    "AUTH_SERVICE_URL=http://auth-service" `
    "USER_SERVICE_URL=http://user-service" `
    "AUDIO_PROCESSOR_URL=http://audio-processor" `
    "ASR_SERVICE_URL=http://asr-service" `
    "TRANSCRIPTION_MANAGER_URL=http://transcription-manager"
```

---

## Update — Redeploy a single service

Build, push y redesplegar un servicio específico. Usa `--revision-suffix` con un número incremental (`v3`, `v4`, …) para forzar que ACA descargue la nueva imagen — sin esto, ACA cachea el digest de `:latest` y no crea revisión nueva.

```powershell
$SVC = "api-gateway"   # cambia por el servicio que modificaste
$REV = "v5"            # incrementa cada vez que redespliegues

docker build -t "ghcr.io/zrodrigochirinos/${SVC}:latest" "services/$SVC"
docker push "ghcr.io/zrodrigochirinos/${SVC}:latest"
az containerapp update --name $SVC --resource-group rg-asr-quechua --image "ghcr.io/zrodrigochirinos/${SVC}:latest" --revision-suffix $REV
```

Para redesplegar varios a la vez:

```powershell
$REV = "v5"   # incrementa cada vez que redespliegues

foreach ($SVC in @("audio-processor", "asr-service")) {
  docker build -t "ghcr.io/zrodrigochirinos/${SVC}:latest" "services/$SVC"
  docker push "ghcr.io/zrodrigochirinos/${SVC}:latest"
  az containerapp update --name $SVC --resource-group rg-asr-quechua --image "ghcr.io/zrodrigochirinos/${SVC}:latest" --revision-suffix $REV
}
```

Verifica que la nueva revisión está activa:

```powershell
az containerapp revision list --name $SVC --resource-group rg-asr-quechua --output table
```

---

## Status — Check all services

```powershell
az containerapp list --resource-group rg-asr-quechua --output table
```

Check logs for a specific service:

```powershell
az containerapp logs show --name <service-name> --resource-group rg-asr-quechua --follow
```

---

## Bring Down — Pause (keep data, stop billing)

Escala los container apps a cero y detiene PostgreSQL. Los datos se conservan.

```powershell
# 1. Escalar todos los servicios a cero réplicas
foreach ($svc in @("auth-service","user-service","audio-processor","transcription-manager","asr-service","api-gateway")) {
  az containerapp update --name $svc --resource-group rg-asr-quechua --min-replicas 0
}

# 2. Detener PostgreSQL (se puede pausar hasta 7 días; Azure lo reinicia automáticamente después)
az postgres flexible-server stop --name pg-asr-quechua --resource-group rg-asr-quechua
```

## Bring Up — Resume

```powershell
# 1. Iniciar PostgreSQL (esperar ~2 minutos hasta que esté disponible)
az postgres flexible-server start --name pg-asr-quechua --resource-group rg-asr-quechua

# 2. Escalar todos los servicios a 1 réplica
foreach ($svc in @("auth-service","user-service","audio-processor","transcription-manager","asr-service","api-gateway")) {
  az containerapp update --name $svc --resource-group rg-asr-quechua --min-replicas 1
}
```

> **Nota**: mientras PostgreSQL está detenido no cobra cómputo, solo almacenamiento (~$0.10/GB/mes). Los container apps en cero réplicas no cobran nada.

---

## Tear Down — Delete everything

```powershell
az group delete --name rg-asr-quechua --yes --no-wait
```

This deletes the resource group and **all** resources inside it (ACA environment, all container apps, and PostgreSQL server). This action is irreversible.

---

## Notes

- **SMTP stub mode**: if `SMTP_USER` is empty, emails are logged but not sent. Useful for staging.
- **`--no-wait`** flag can be added to any `az containerapp create` to return immediately and deploy in the background.
- **PostgreSQL firewall**: the `--public-access 0.0.0.0` flag allows ACA outbound IPs. ACA uses dynamic IPs, so the wildcard rule is required.
- **GitHub token rotation**: if a GitHub PAT is ever exposed, rotate it immediately at github.com/settings/tokens.
