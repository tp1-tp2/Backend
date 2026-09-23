# Fase 6 — Autoscaling horizontal (complemento del mecanismo adaptativo)

## Qué problema resuelve

**E4** (Fase 5, corrido contra el despliegue de verificación en Azure) mostró que la arquitectura desplegada hoy —fija en 1 réplica por servicio, sin autoscaling— colapsa rápido: latencia mediana de 4.7s ya con 10 usuarios concurrentes, 100% de error alrededor de 250 usuarios reales sostenidos. `asr-service` es el cuello de botella: corre `--workers 1` (el modelo Whisper vive en un global a nivel de módulo, Fase 1) y cada transcripción real ocupa ese único worker por 1-3s o más — cualquier concurrencia más allá de un puñado de requests empieza a encolar.

Esto es una limitación real y distinta de la que resuelve la Fase 1. El mecanismo adaptativo (`device_manager.py`) es **vertical**: decide cómo una réplica usa *su propio* hardware (dispositivo, precisión). No dice nada sobre *cuántas* réplicas existen. Esta fase agrega la dimensión **horizontal** — cuántas instancias de `asr-service` corren según la carga entrante — como complemento, no reemplazo.

## Diseño

- **Trigger: concurrencia HTTP, no CPU%.** Con `--workers 1`, el contenedor puede mostrar CPU% moderado mientras ya tiene requests encolados esperando el único worker libre — CPU% reaccionaría tarde. ACA soporta una regla nativa de tipo `http` que escala según requests concurrentes *por réplica*, que es la señal correcta aquí: con el umbral en 2, la segunda transcripción concurrente ya dispara una réplica nueva.
- **`min-replicas: 1, max-replicas: 3`** — no se dejó sin techo. Acotado por costo (créditos de Azure for Students) y porque no hay evidencia todavía de que hagan falta más de 3 réplicas para el volumen de tráfico real esperado; subir el techo es un cambio de una línea si E4 vuelve a mostrar saturación con este límite.
- **Sin cambios de código.** `device_manager.py` y `whisper_service.py` ya funcionan correctamente por proceso/contenedor — cada réplica nueva trae su propia instancia del mecanismo adaptativo, monitoreando su propio hardware local vía `psutil`. Esto es exactamente lo que se quiere: cada réplica se adapta a su propia presión de recursos, independientemente de cuántas réplicas hermanas existan.

## Arranque en frío — resuelto: modelo horneado en la imagen

**Actualizado (2026-09-21).** El primer E4 con autoscaling activo (`experiments/results/e4_azure_autoscale_report.md`) mostró mejora parcial pero no dramática — la sospecha era que las réplicas nuevas no llegaban a "calentar" (descargar + cargar el modelo desde HuggingFace Hub) dentro de la ventana de cada escalón de carga (180s). El `VOLUME ["/root/.cache/huggingface"]` que tenía el Dockerfile no resolvía esto: en ACA cada réplica nueva recibe un volumen anónimo vacío, así que **cada** arranque (incluidos los disparados por autoscaling) pagaba la descarga completa.

**Fix**: `services/asr-service/Dockerfile` ahora descarga y cachea el modelo+tokenizer **en tiempo de build**, no en tiempo de arranque — un `RUN python -c "..."` que construye el pipeline una vez durante el build, dejando los ~279MB del modelo horneados en la capa de la imagen. Se quitó el `VOLUME` (ya no hace falta, y evita el riesgo de que una plataforma monte un volumen vacío encima del caché horneado).

Medido localmente: **arranque a "listo" (`Application startup complete`) en ~4.8 segundos**, con **cero** llamadas HTTP a `huggingface.co` en el log de arranque (antes eran ~20+ requests de red antes de siquiera empezar a construir el pipeline). Solo se hornea la variante fp32 — fp16 e int8 (las otras variantes que usa `device_manager.py`) se derivan en tiempo de carga de estos mismos archivos cacheados, no son descargas separadas.

**Costo del tradeoff**: build más lento (ahora descarga el modelo en cada build de imagen, no solo la primera vez que corre un contenedor) e imagen ~500MB más grande (9.36GB → 9.87GB). Aceptable: el build pasa una vez por despliegue; el arranque pasa en cada evento de autoscaling, que es el lado sensible al tiempo.

**Resultado (2026-09-21)**: se corrió E4 con esta imagen (`e4_azure_baked_report.md`) y el resultado fue **peor**, no mejor, que el run de autoscaling-solo — se estancó en 244 usuarios con 100% de error desde el step 4, contra 307 usuarios sostenidos al 12.8% de error del run anterior. Esto llevó a investigar la causa raíz (ver siguiente sección) en vez de asumir que el horneado del modelo no sirvió: el problema real estaba en otro lado.

## El cuello de botella real: `auth-service`, no `asr-service`

**Hallazgo (2026-09-21)**. El run con el modelo horneado mostró un salto a **2652 errores 401 Unauthorized** en `/api/v1/transcribe` que no existían en el run anterior (0 errores 401). Investigando [`services/api-gateway/app/api/dependencies.py`](../services/api-gateway/app/api/dependencies.py) (`get_current_user`, líneas 16-36): **cada** request autenticado — incluida cada transcripción — hace un round-trip síncrono a `auth-service` (`POST /internal/auth/validate-token`). Si esa respuesta no es exactamente `200` con `valid: true` — incluyendo cuando `auth-service` responde `500`/`502`/`504` por estar sobrecargado — el código cae al mismo `raise AuthenticationError()`, devolviendo **401** al cliente sin distinguir "token inválido" de "auth-service caído por carga". Los failures.csv de ambos runs muestran errores 500/502/504 directos en `/auth/login` también, confirmando que `auth-service` ya estaba bajo presión.

`auth-service` nunca se autoescaló — la Fase 6 original solo tocó `asr-service` (razonable en su momento: era el servicio computacionalmente pesado, candidato obvio a cuello de botella). Pero como `auth-service` está en el *critical path* de absolutamente todo el tráfico autenticado (no solo `/auth/*`), un único replica fijo lo convierte en un techo duro para todo el sistema — independientemente de cuánto escale `asr-service` o cuán rápido arranque. Esto explica por qué tanto el run sin autoscaling como el run con autoscaling-solo mostraron saturación temprana similar (~40-42 usuarios): `auth-service` ya era el límite en ambos casos.

### Fix aplicado

Mismo patrón de autoscaling HTTP-concurrency que `asr-service`, aplicado a `auth-service`:

```yaml
scale:
  minReplicas: 1
  maxReplicas: 3
  rules:
    - name: http-concurrency
      http:
        metadata:
          concurrentRequests: "10"
```

**Umbral distinto (10, no 2)**: a diferencia de `asr-service` (`--workers 1`, cada transcripción real ocupa el único worker 1-3s+), `auth-service` corre `--workers 4` y `validate-token` no hace bcrypt (eso es solo login/register) — es un decode+verify de JWT, sub-100ms. Un replica puede sostener más concurrencia real antes de encolar de verdad, así que un umbral tan bajo como 2 habría escalado de más por requests baratos.

Archivos actualizados: `aca/auth-service.yaml`, `DEPLOY.md`, `VERIFY-AZURE.md` (comando `az containerapp create` de `auth-service`).

**Pendiente**: volver a correr E4 con `auth-service` también autoescalado, para confirmar si esto destraba la saturación más allá de lo que logró el autoscaling de `asr-service` solo.

## Observabilidad — queda por-réplica

`GET /status/adaptation` sigue siendo por-instancia: con 3 réplicas hay 3 respuestas distintas posibles, una por contenedor. No se construyó una vista consolidada (requeriría que cada réplica reporte a un store compartido, ej. Postgres) — para el alcance de esta fase, la visibilidad por réplica es suficiente. Si hace falta una vista global más adelante, ese es el punto de extensión natural.

## Archivos

- `aca/asr-service.yaml` — sección `scale` con `maxReplicas: 3` y la regla `http-concurrency`.
- `DEPLOY.md` — comando `az containerapp create` de `asr-service` actualizado con `--min/max-replicas` y `--scale-rule-*` (despliegue de producción nuevo).
- `VERIFY-AZURE.md` — mismo cambio para el flujo de verificación (Parte 2, paso 2.5).

## Cómo aplicarlo a un despliegue ya existente

Los despliegues que ya están arriba (producción, o el de verificación de tu amigo) no se actualizan solos al cambiar estos archivos — hace falta correr:

```powershell
az containerapp update `
  --name asr-service --resource-group <RG> `
  --min-replicas 1 --max-replicas 3 `
  --scale-rule-name http-concurrency `
  --scale-rule-type http `
  --scale-rule-metadata concurrentRequests=2
```

> **Gotcha confirmado (2026-09-20)**: el flag corto `--scale-rule-http-concurrency 2` creó la regla pero con `concurrentRequests` **vacío** en vez de `"2"` — en una versión de la extensión `containerapp` de Azure CLI, al menos. La forma explícita `--scale-rule-metadata concurrentRequests=2` sí aplicó el valor correctamente.
>
> **Segundo gotcha confirmado (2026-09-21)**: un `az containerapp update` posterior que solo tocaba `--image` (sin mencionar nada de `scale-rule-*`) **volvió a vaciar** `concurrentRequests` — pasó de `"2"` a `""` otra vez, sin que el comando tocara esa parte de la config explícitamente. Conclusión práctica: **verificar la regla de escalado después de CUALQUIER `az containerapp update` a este servicio**, no solo la primera vez que se configura — no asumir que persiste entre actualizaciones no relacionadas. Verificar siempre con:
> ```powershell
> az containerapp show --name asr-service --resource-group <RG> --query "properties.template.scale" -o json
> ```
> y confirmar que `concurrentRequests` no quede como cadena vacía; si quedó vacío, reaplicar con `--scale-rule-metadata concurrentRequests=2`.

## `auth-service` también autoescalado

**Fix aplicado (2026-09-21)**, mismo patrón de HTTP-concurrency que `asr-service`, con umbral distinto:

```yaml
scale:
  minReplicas: 1
  maxReplicas: 3
  rules:
    - name: http-concurrency
      http:
        metadata:
          concurrentRequests: "10"
```

**Umbral 10, no 2**: `auth-service` corre `--workers 4` (no tiene el modelo global que fuerza `--workers 1` en `asr-service`) y `validate-token` no hace bcrypt (eso es solo login/register) — es un decode+verify de JWT, sub-100ms. Un replica aguanta más concurrencia real antes de encolar de verdad.

Archivos: `aca/auth-service.yaml`, `DEPLOY.md`, `VERIFY-AZURE.md` (comando `az containerapp create` de `auth-service`). Aplicado al despliegue de verificación con:

```powershell
az containerapp update `
  --name auth-service --resource-group <RG> `
  --min-replicas 1 --max-replicas 3 `
  --scale-rule-name http-concurrency --scale-rule-type http --scale-rule-metadata concurrentRequests=10
```

## Resultado final — 4 corridas de E4 comparadas (2026-09-21, corregido 2026-09-21)

**Corrección metodológica (2026-09-21)**: la primera versión de esta tabla usaba `Requests/s`/`Failures/s` — la tasa *instantánea* de la última fila muestreada dentro de cada ventana de 180s — para calcular el error rate por escalón. Eso es una sola muestra de 1 segundo, no un agregado real de la ventana: si el burst de errores caía a mitad del escalón y no justo en el segundo final muestreado, el escalón podía reportar 0% de error aunque sí hubo fallos reales dentro de esa ventana. `experiments/e4_load_test/report.py` fue corregido para usar las columnas acumulativas `Total Request Count`/`Total Failure Count` (diferencia entre el fin de un escalón y el anterior), que sí reflejan el conteo real. Los cuatro reportes de esta sección fueron **regenerados** con el fix; los números de abajo son los correctos. El hallazgo de `auth-service` como cuello de botella (la cuenta de errores 401 por tipo, sacada directo de `failures.csv`) no estaba afectado por este bug y se mantiene igual.

| Corrida | Config | Usuarios alcanzados (escalón sostenido) | Error rate (escalón final) | p99 |
|---|---|---|---|---|
| `e4_azure_run` | sin autoscaling | 254 | 96.9-100% | ~68-81s |
| `e4_azure_autoscale_run` | + autoscale `asr-service` | 307 | 85.6% | ~81s |
| `e4_azure_baked_run` | + modelo horneado en la imagen | 244 | 97.1-100% | ~67s |
| `e4_azure_authscale_run` | + autoscale `auth-service` también | **353** | 85.9-100% | **149s** |

La mejora real es más modesta de lo que se reportó inicialmente (antes se citaba erróneamente "12.8%" para la segunda corrida): **ninguna configuración baja el error rate del escalón final por debajo de ~85%** — todas terminan colapsando a carga extrema. Lo que sí mejora de forma consistente y medible entre corridas es el **número de usuarios concurrentes sostenidos antes del colapso** (254 → 307 → 353, excluyendo el retroceso del run con modelo horneado sin `auth-service` autoescalado). Esa es la métrica defendible para el paper, no el error rate en el peor escalón.

El run con modelo horneado salió **peor**, no mejor — llevó a investigar la causa (ver arriba): `auth-service`, fijo en 1 réplica, está en el *critical path* de todo el tráfico autenticado porque `api-gateway` valida el token contra él en cada request (`services/api-gateway/app/api/dependencies.py`), y cualquier respuesta que no sea `200`+`valid:true` —incluyendo un 500/502/504 de `auth-service` sobrecargado— se traduce en 401 al cliente. Ese run tuvo 2652 errores 401 en `/transcribe` (conteo directo de `failures.csv`, no afectado por el bug de arriba).

Autoescalar `auth-service` validó la hipótesis: los 401 bajaron a 235 (-91%) y el sistema sostuvo el mayor número de usuarios de las 4 corridas (353). El error rate del escalón final sigue alto en las cuatro configuraciones y el p99 se disparó a 149s en la última — el sistema ahora admite más tráfico pero lo hace esperar mucho más antes de fallar, en vez de fallar rápido. El cuello de botella se movió de nuevo, probablemente a uno de:

- **Capacidad real de cómputo de Whisper en `asr-service`** — el límite que estuvo enmascarado todo este tiempo detrás del problema de `auth-service`; con 3 réplicas de 2 CPU cada una, puede simplemente ser el techo real de cuánto CPU (sin GPU) alcanza a transcribir por segundo.
- **Pool de conexiones de Postgres** (`pg-asr-verify`, SKU `Standard_B1ms`, burstable) — con hasta 3 réplicas × 4 workers de `auth-service` más las demás réplicas de `asr-service`, el server único de Postgres podría estar limitando conexiones concurrentes.
- **`audio-processor`** — sigue fijo en `--min-replicas 1 --max-replicas 1`, no se tocó en ninguna de las dos fases de autoscaling; hace la conversión ffmpeg antes de reenviar a `asr-service`.

## Autoscaling extendido a los servicios restantes del critical path

**Aplicado (2026-09-21)**, mismo patrón, a los tres servicios que quedaban fijos en 1 réplica y están en el camino de cada `/transcribe`:

| Servicio | Rol en el critical path | `--workers` | Umbral |
|---|---|---|---|
| `audio-processor` | conversión ffmpeg antes de reenviar a `asr-service` | 4 | `concurrentRequests=10` |
| `transcription-manager` | `asr-service` espera (`await`) este POST sincrónicamente antes de responder al cliente — no falla la request si esto falla, pero sí le suma latencia mientras espera | 4 | `concurrentRequests=10` |
| `api-gateway` | único punto de ingress público — el 100% del tráfico pasa por acá | 4 | `concurrentRequests=10` |

Umbral `10` para los tres, igual que `auth-service`: los cuatro corren `--workers 4` (sin el global de modelo que fuerza `--workers 1` en `asr-service`) y ninguno hace trabajo bloqueante de varios segundos por request — es un umbral de partida razonable, no calibrado con datos propios todavía; la siguiente corrida de E4 es la que valida si hace falta ajustarlo.

**`user-service` queda afuera, deliberadamente**: no está en el critical path que ejercita E4 (login → transcribe en loop) — solo maneja registro/perfil, y el registro de los 30 usuarios de prueba ocurre una sola vez antes del run, no repetidamente durante la carga. Autoescalarlo sin evidencia de que sea un cuello de botella real contradice el enfoque de esta fase (medir antes de asumir).

Archivos: `aca/audio-processor.yaml`, `aca/transcription-manager.yaml`, `aca/api-gateway.yaml`, `DEPLOY.md`, `VERIFY-AZURE.md`.

**Pendiente**: correr una quinta ronda de E4 con los 5 servicios autoescalados (`asr-service`, `auth-service`, `audio-processor`, `transcription-manager`, `api-gateway`) para ver si esto termina de cerrar la brecha de error rate/p99 que quedó abierta en la cuarta corrida, o si el cuello de botella se corre de nuevo hacia Postgres (el server único `pg-asr-verify` compartido por las 4 bases de datos, o el compute real de Whisper en CPU sin GPU).

No se investigó más allá de este punto — es una decisión de alcance/costo (créditos de Azure for Students), documentada aquí como limitación abierta en vez de asumida como resuelta. La serie de corridas de E4 ya es evidencia empírica sustancial para el paper: muestra que la adaptación vertical sola no reacciona bajo esta carga (ver más arriba), que el autoscaling horizontal ayuda pero solo del servicio correcto, y que identificar el cuello de botella real requirió instrumentación y no solo intuición sobre qué servicio "debería" ser el más pesado.
