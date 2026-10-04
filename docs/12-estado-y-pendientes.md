# Estado actual y pendientes (2026-10-03)

## Estado actual

### Implementado y verificado

| Dimensión | Cambio | Verificación |
|---|---|---|
| Disponibilidad | Validación local del JWT en el gateway (`AUTH_MODE=local`) + espejo de revocaciones en Redis | Tests unitarios; extremo a extremo (logout → 401); E6 humo: auth caído → 100 % de éxito |
| Disponibilidad | 5xx de auth → 503 + `Retry-After` (antes 401) | Test de regresión |
| Disponibilidad | audio-processor propaga los errores de ASR (antes: 200 sin transcripción) + reintento solo ante errores de conexión | Tests nuevos |
| Disponibilidad | Control de admisión, `/ready` separado de `/health`, presupuesto de timeouts 120 > 110 > 100 s | Tests del scheduler |
| Disponibilidad | `restart: unless-stopped` | E6 D1: MTTR 4.9 s |
| Escalabilidad | API asíncrona `POST/GET /api/v1/jobs` sobre Redis Streams, entrega *at-least-once* (*heartbeat*, `XAUTOCLAIM`, idempotencia) | Extremo a extremo (202 → done en 0.68 s) |
| Escalabilidad | Manifiestos ACA: `aca/redis.yaml`, `aca/asr-worker.yaml` (KEDA por backlog, 0–10 réplicas), sondas en `aca/asr-service.yaml` | **Sin desplegar ni probar en Azure** |
| Escalabilidad | Worker GPU híbrido (`docker-compose.worker.yml`) | **Sin probar** |
| Rendimiento | GPU (`docker-compose.gpu.yml`), scheduler con *micro-batching* y prioridades, persistencia en segundo plano, clientes HTTP compartidos, pools de BD acotados | E8 humo: 5.4× |
| Rendimiento | Remuestreo propio a 16 kHz (sin `torchaudio`) | Extremo a extremo |
| Adaptación | Política guiada por la cola, eje de tamaño de *batch*, *fallback* a CPU por OOM, fijación por eje, **verificación con periodo de prueba y reversión** | Tests + E9 humo (A, B, C) |

### Herramientas de experimentos

- `experiments/run_v2_suite.py`: orquesta E8, E9, E4, E6 y E3 cambiando la configuración por variables de entorno.
- E4 v2: `locustfile.py` (validación de cuerpo, modo async, rampa configurable, CSV crudo) + `slo_report.py` (capacidad por SLO, ley de Little). Probado solo con datos sintéticos.
- E6 v2: `run_scenario.py` (`crash`/`stop`/`kill`/`pause`, MTTR, ventanas por finalización, trabajos perdidos).
- E8: `bench.py` + `report.py`. E9: `observe.py`.

### Entorno de este equipo

- GPU NVIDIA RTX A1000 de 8 GB; Docker 29.8; solo Python 3.14 (entorno en `experiments/.venv` con versiones sin pin).
- Pila levantada con: `GATEWAY_PORT=8080 docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` (el puerto 8000 lo usa un proceso del sistema).
- Antes de usar el orquestador: `export GATEWAY_PORT=8080 GATEWAY_URL=http://localhost:8080`.
- El corpus **no está** en este equipo (los manifiestos apuntan a `E:\IWSLT2026_Quechua_data`).

### Interrumpido

- La segunda corrida de E6 (modo `crash`) se detuvo durante D2. Solo D1 quedó completo (`docs/11`, §4.1).

## Pendientes

### Para cerrar los resultados del capítulo (prioridad alta)

1. **Conseguir el corpus en este equipo** (copiarlo o clonar el repositorio público IWSLT2026) y regenerar el manifiesto con `build_manifest_from_iwslt.py`. Elegir un clip real representativo (~23 s) para las cargas.
2. **E6 v2 completo** (`--phase e6`, sin `--quick`): D1–D7 en modo `crash`, incluidos D4 async (trabajos perdidos) y D5 Redis. 3 repeticiones.
3. **E4 v2** (`--phase e4 --repeats 3`): S1 réplica v1 en CPU, S2 v2 en CPU, S3 v2 en GPU síncrono, S4 v2 en GPU asíncrono. Rampa 10→1000. Reportar capacidad por SLO y la cota de Little (C2.1, C2.2).
4. **E8 completo** (`--phase e8 --manifest <muestra>`): las 7 configuraciones hasta concurrencia 32, con control de WER (C3.4).
5. **E9 completo** (`--phase e9`): con los tiempos por defecto; 3 repeticiones por escenario.
6. **E3 v2** (`--phase e3`): propuesta frente a monolito, ambos con GPU y validación del cuerpo de la respuesta.
7. **Re-medir E6 v1 de asr-service** con la validación de cuerpo, o declarar explícitamente en el capítulo 5 que el 100 % estaba inflado (`docs/09` §1.2).
8. Actualizar `cap-5-extracted.md` con la tabla de criterios nueva (C1.5–C1.7, C2.4, C3.4) y los resultados definitivos.

### Arquitectura (prioridad media)

9. Desplegar v2 en Azure Container Apps: Redis, `asr-worker` con KEDA (verificar soporte de `lagCount` en la versión de KEDA de ACA) y sondas de *readiness*. Correr E4 S5 en la nube.
10. Probar la topología híbrida: worker GPU local contra el Redis de la nube (requiere Redis con TLS y contraseña; nunca exponer Redis sin autenticación).
11. Evaluar `faster-whisper` (CTranslate2) como motor alternativo, con control de WER.
12. Frontend: usar `/api/v1/jobs` para archivos y Opus en el streaming (E5 ya mostró que no degrada la calidad).

### Riesgos y deuda conocidos

- Redis es un punto único de fallo **para la ruta asíncrona** (la síncrona y la autenticación tienen *fail-open*). En producción conviene Azure Cache for Redis gestionado.
- Durante una caída de Redis con `REVOCATION_FAIL_OPEN=true`, un token revocado sigue válido hasta su expiración (compromiso CAP documentado).
- Los manifiestos `k8s/` no se actualizaron a v2 (solo `aca/`).
- `docs/08-como-correr-experimentos.md` describe el flujo v1; el flujo v2 está en `docs/10` y en `experiments/README.md`.
