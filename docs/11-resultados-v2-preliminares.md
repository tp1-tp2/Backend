# Resultados v2 — preliminares (pruebas de humo, 2026-10-03)

Registro de lo medido hasta ahora sobre la arquitectura v2 (`docs/09-arquitectura-v2.md`) con el protocolo v2 (`docs/10-experimentos-v2.md`). **Son pruebas de humo:** validan que la arquitectura y los scripts funcionan y muestran tendencias, pero **no son todavía resultados citables en la tesis**:

- **Audio:** un solo clip sintético (`experiments/results/sample_tts_16k.wav`, voz TTS de Windows leyendo texto en quechua, 24.7 s, 16 kHz mono), no el corpus. Sirve para rendimiento; no para calidad.
- **Duración:** corridas cortas (15–90 s por nivel) y una sola ejecución por condición, sin intervalos de confianza.
- **Hardware:** equipo local con GPU NVIDIA RTX A1000 8 GB (Docker Desktop + WSL2). Gateway publicado en el puerto **8080** (`GATEWAY_PORT=8080`), porque el 8000 lo ocupa un proceso del sistema en este equipo.

Copias de los resúmenes crudos: `experiments/results_v2_smoke/` (los CSV crudos quedan en `experiments/results/`, que está en `.gitignore`).

## 1. Verificación

- Tests unitarios en contenedor (Python 3.11): api-gateway **68**, auth-service **34**, audio-processor **24** y asr-service **42**, todos pasan. Incluyen tests nuevos del scheduler (*batching*, prioridades, admisión, descarte de parciales, OOM), de la política de adaptación y de la reversión de decisiones.
- Prueba de extremo a extremo sobre la pila con GPU:
  - `POST /api/v1/transcribe`: 200 con transcripción.
  - `POST /api/v1/jobs`: **202 en 0.36 s**; el trabajo terminó en **0.68 s** en CUDA (espera en cola 0.006 s, proceso 0.674 s) y quedó persistido en transcription-manager.
  - Tras `logout`, el mismo token recibe **401**: la revocación vía Redis funciona sin consultar a auth-service.
  - `torch 2.4.1+cu121` dentro de la imagen: la GPU funciona sin una imagen especial.

## 2. Rendimiento — E8 (directo a asr-service, sin gateway)

| Configuración | Concurrencia | req/s | Audio procesado (s/s) | p50 | p95 |
|---|---|---|---|---|---|
| CPU fp32, *batch* 1 | 1 | 0.81 | 20.0 | 1.26 s | 1.43 s |
| CPU fp32, *batch* 1 | 4 | 0.71 | 17.5 | 5.16 s | 8.78 s |
| CPU int8, *batch* 1 | 1 | 0.38 | 9.3 | 2.63 s | 2.83 s |
| CPU int8, *batch* 1 | 4 | 0.38 | 9.3 | 10.57 s | 10.75 s |
| CUDA fp16, *batch* 8 | 1 | 1.72 | 42.4 | 0.58 s | 0.63 s |
| CUDA fp16, *batch* 8 | 2 | 2.72 | 67.2 | 0.67 s | 1.19 s |
| CUDA fp16, *batch* 8 | 4 | 4.42 | **109.2** | 0.78 s | 1.49 s |

- **GPU con *batching*: 5.4× el throughput de CPU fp32**, medido solo hasta concurrencia 4. La matriz completa (hasta 32 y todas las combinaciones) está pendiente.
- En CPU la latencia crece linealmente con la concurrencia (el servicio está saturado con 1 cliente). En GPU casi no crece: el scheduler formó lotes de 3–4 de forma automática (histograma `{1: 1, 2: 1, 3: 8, 4: 10}` a concurrencia 4).
- Latencia a concurrencia 1, GPU frente a CPU: mediana 0.58 frente a 1.21 s (Mann-Whitney p < 0.001, Cliff's δ = −1.0).
- **Hallazgo:** en la CPU de evaluación, la cuantización dinámica **int8 es 2× más lenta** que fp32. La regla v1 "bajo presión de CPU, int8" empeoraba el sistema. Ver §3.

## 3. Adaptación — E9 (criterio C2.3)

Perfil: reposo → ráfaga de 24 clientes concurrentes → reposo, sondeando `/status/adaptation` cada segundo.

| Escenario | Decisiones aplicadas | Reacción | Comportamiento |
|---|---|---|---|
| A — GPU adaptativa | 4 (2 de precisión, 2 de *batch*) | **3.2 s** | *batch* 8→16 y fp32→fp16 bajo la ráfaga; **fp16 superó el periodo de prueba** (0.180 frente a 0.217 s/clip); volvió a fp32 y *batch* 8 al terminar |
| B — solo CPU | 2 | 15.3 s | Pasó a int8, midió 2.54 frente a 1.34 s/clip y **revirtió automáticamente**; `cpu/int8` quedó rechazado en este host |
| C — CPU→GPU (RQ1) | 5 (1 de dispositivo) | 4.1 s | Arrancó en CPU y **migró en caliente a CUDA**; terminó en cuda/fp32/*batch* 8 |

- **C2.3 se cumple** en los tres escenarios. En v1 hubo 0 decisiones en cuatro rondas de E4.
- El escenario C es la **primera evidencia empírica de RQ1** (conmutación CPU/GPU), que en v1 quedó pendiente por falta de GPU.
- Cambios al mecanismo motivados por estas pruebas:
  1. Fijar un eje (`FORCE_DEVICE`) ya no congela los otros. La primera corrida de B dio 0 decisiones aplicadas pese a que la política decidió int8 16 veces.
  2. **Adaptación verificada:** el scheduler mide el costo real por clip de cada estado; una degradación de precisión que no resulta más rápida se revierte tras 5 clips y ese estado no se vuelve a intentar en el host (criterio nuevo C2.4).

## 4. Disponibilidad — E6 v2 (50 usuarios concurrentes, carga síncrona)

### 4.1 Con caída real (`crash`: SIGKILL del proceso desde el host de Docker)

| Escenario | Detección | **MTTR** | Éxito antes | Éxito durante | Éxito después |
|---|---|---|---|---|---|
| D1 — asr-service | 1.2 s | **4.9 s** | 100 % (139) | 17.8 % (90; 74 × 503) | 97.7 % (574) |

Con `restart: unless-stopped` el servicio se recupera solo en unos 5 s. En v1 la recuperación no era observable. Sin propagación a vecinos. Los fallos durante el corte son 503 rápidos (control de errores v2), no timeouts.

### 4.2 Primera prueba de humo (`docker kill`; sin MTTR, ventanas por inicio de solicitud)

Esta corrida tenía dos defectos de medición, ya corregidos: `docker kill` es una parada **manual** que Docker no reinicia, y las ventanas se asignaban por inicio de solicitud. Las comparaciones entre escenarios siguen siendo indicativas:

| Escenario | Éxito durante el corte | Lectura |
|---|---|---|
| auth-service caído, `AUTH_MODE=local` (v2) | **100 %** (222) | El punto único de fallo desaparece (v1: 34.7 %) |
| auth-service caído, `AUTH_MODE=remote` (modo v1) | 0.5 % (218 × 502) | Confirma que la causa es la validación remota |
| transcription-manager caído | 100 % (219) | Sigue siendo no crítico |
| Redis caído (ruta síncrona) | 100 % (210) | La validación con *fail-open* funciona |
| asr-service congelado (`pause`) | 37.5 % (16) | Se recupera en 28 s al reanudar |
| asr-service caído (`kill`) | 0 % (30 × 503) | Sin reinicio (parada manual) |
| Monolito caído | 0 % (404) | Línea base |
| asr-service caído, carga async | sin dato válido | Locust cortaba a los usuarios a mitad del *polling* (corregido con `--stop-timeout`) |

### 4.3 Corrección de una amenaza a la validez de v1

En v1, con asr-service detenido, audio-processor respondía **200 con `transcription_id: null`**, y Locust lo contaba como éxito. El **100 % de éxito** reportado en el capítulo 5 para la caída de asr-service **no es confiable**. v2 propaga el error (503 + `Retry-After`) y el cliente de carga valida el cuerpo de la respuesta. El monolito no tenía este defecto, así que la comparación v1 favorecía a la arquitectura propuesta.

## 5. Lo que estos resultados permiten adelantar (con cautela)

| Criterio | Tendencia observada | Falta para afirmarlo |
|---|---|---|
| C1.5 MTTR ≤ 30 s | 4.9 s (asr-service) | Todos los servicios, repeticiones |
| C1.7 auth caído con validación local ≥ 95 % | 100 % | Repetir con `crash` y repeticiones |
| C2.3 adaptación bajo carga | Cumple (A, B, C) | Corridas completas |
| C2.4 sin adaptaciones dañinas activas | Reversión observada en B | Repeticiones |
| C3.1 RTF < 1 | ≈ 0.03 en GPU | Corpus real (E2 en GPU) |
| C3.4 GPU+*batch* ≥ 5× CPU | 5.4× hasta concurrencia 4 | Matriz E8 completa + control de WER con corpus |
| C2.1 / C2.2 escalabilidad | Sin datos | Correr E4 v2 |
