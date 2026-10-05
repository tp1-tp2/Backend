# Resultados v2 en CPU — parciales (2026-10-04, 18:40)

Resultados medidos hoy en el equipo de evaluación **sin GPU** (i5-10400, 6 núcleos y 12 hilos, Docker/WSL2 con 12 CPU y 16 GB) con el **corpus real** (IWSLT2026: Huqariq + Siminchik). Contexto y cambios de arquitectura en `docs/14-optimizacion-cpu.md`; lo pendiente en GPU, en `docs/15-pendientes-gpu.md`.

**Estado:** E8, E9 y E6 están completos (salvo D7 r2/r3). E4 S1 y S2 están completos; S2b (asíncrono) está en curso, y E3 y el control de WER sobre el corpus completo, pendientes. Datos crudos en `experiments/results/` (no versionado).

Configuración v2 de este equipo: `ENGINE=ctranslate2`, `INFERENCE_LANES=3`, `CT2_CPU_THREADS=2`, `FORCE_DEVICE=cpu`, adaptación activa. Clip de carga: `quechua_03068.wav` (Huqariq, 24.05 s; mediana del corpus: 23.04 s).

---

## 1. Rendimiento — E8 en CPU (directo a asr-service, 30 clips reales, 45 s por nivel)

Throughput en **segundos de audio procesados por segundo** (entre paréntesis, la latencia por solicitud p50/p95 en segundos):

| Configuración | c = 1 | c = 4 | c = 16 | Pico | × base |
|---|---|---|---|---|---|
| transformers fp32 (base, v1) | 7.1 (2.06/4.95) | 6.1 (10.9/14.9) | 5.0 (38.4/47.7) | 7.1 | 1.00 |
| transformers int8 | 9.8 (1.72/3.75) | 8.8 (6.9/10.0) | 8.1 (25.9/32.7) | 9.8 | 1.39 |
| CTranslate2 int8, 1 línea × 6 hilos | 13.5 (1.14/2.21) | 12.2 (5.3/6.7) | 10.3 (20.8/23.5) | 13.8 | 1.95 |
| **CTranslate2 int8, 3 líneas × 2 hilos (v2)** | 11.9 (1.49/2.42) | **19.4** (3.50/5.01) | 16.3 (14.2/17.5) | **19.4** | **2.74** |
| CTranslate2 int8, 6 × 1 | 8.0 (2.11/3.62) | 19.6 (3.24/6.23) | 17.3 (13.3/19.2) | 19.6 | 2.76 |

- **2.7× el throughput de inferencia sin GPU.** Con 16 clientes, el p95 baja de 47.7 s a 17.5 s.
- Usar los 12 hilos lógicos en una sola línea de CTranslate2 fue 5× más lento (RTF 0.67): el *hyperthreading* perjudica. Por eso se usan 3 líneas × 2 hilos.

### Control de WER (paridad de motores, 30 clips, una solicitud a la vez)

| Motor / precisión | RTF mediano | WER medio | Salida idéntica a la base | Wilcoxon frente a la base |
|---|---|---|---|---|
| transformers fp32 (base) | 0.135 | 0.735 | 30/30 | — |
| transformers int8 | 0.102 | 0.732 | 2/30 | p = 0.65 |
| CTranslate2 fp32 | 0.110 | 0.763 | 27/30 | p = 0.11 |
| CTranslate2 int8 | **0.069** | 0.766 | 10/30 | p = 0.22 |

Ninguna diferencia es significativa y la mediana de WER es igual (0.75). **Pendiente:** confirmarlo sobre los 2111 clips.

---

## 2. Adaptación — E9-B en CPU (ráfaga de 24 clientes, 3 repeticiones por motor)

| Motor | Decisiones aplicadas | Tiempo de reacción | req/s antes → después de la 1.ª decisión | Periodo de prueba de int8 | Vuelta a fp32 al terminar |
|---|---|---|---|---|---|
| CTranslate2 | 2 por repetición | 12.8 / 13.0 / 13.4 s | 0.47→0.91 / 0.46→0.86 / 0.45→0.89 | **superado 3/3** (4.48 frente a 6.15 s/clip) | Sí, 3/3 |
| transformers | 2 por repetición | 16.8 / 16.4 / 16.2 s | 0.24→0.50 / 0.25→0.33 / 0.25→0.50 | superado 2/3; **revertido 1/3** (2.98 frente a 3.03 s/clip, ganancia < 5 %) | Sí, 3/3 |

- **C2.3 se cumple en 6 de 6 repeticiones**, frente a 0 decisiones en las cuatro rondas de v1.
- **C2.4 se cumple:** la reversión en la r2 de transformers muestra que una degradación que no rinde lo suficiente no se mantiene.
- La misma política llega a resultados distintos según el host: en el equipo de ayer int8 era 2× más lento y se revirtió; aquí acelera y se conserva. Esto justifica la adaptación **verificada por medición**.

---

## 3. Disponibilidad — E6 v2 (caída real con `crash`, 10 usuarios constantes, 3 repeticiones)

La carga es de **10 usuarios** porque es la capacidad por SLO del CPU según la ley de Little (X ≈ 0.86 req/s × (10 s + 2 s) ≈ 10). Con 50 usuarios, solo el 57.5 % tenía éxito **antes** de la caída, así que E6 medía sobrecarga y no tolerancia a fallos. Esa corrida se conserva aparte en `results/e6_overload_50users/`.

| Escenario | Detección | MTTR | Éxito antes | Éxito durante | Éxito después | Éxito global | Propagación | Trabajos perdidos |
|---|---|---|---|---|---|---|---|---|
| D1 asr-service cae | 1.3 s | **4.9 s** (4.0–6.0) | 100 % | 0 % (45 × 503 rápidos) | 100 % | 93.6 % | No | — |
| D2 auth-service cae, validación local (v2) | 1.3 s | 5.5 s | 100 % | **100 %** | 100 % | **100 %** | No | — |
| D2b auth-service cae, validación remota (como v1) | 1.4 s | 4.9 s | 100 % | 42.9 % (16 × 502) | 100 % | 97.8 % | No | — |
| D3 transcription-manager cae | 1.8 s | 6.0 s | 100 % | **100 %** | 100 % | **100 %** | No | — |
| D4 asr-service cae, carga asíncrona | 1.9 s | 4.9 s | 100 % | 100 % | 100 % | **100 %** | No | **0** |
| D5 Redis cae | 1.1 s | 8.7 s | 100 % | **100 %** | 100 % | **100 %** | No | — |
| D6 asr-service congelado 60 s (`pause`) | 1.1 s | (60 s, reanudado por el script) | 100 % | — | 96.0 % | 96.9 % | No | — |
| **D7 monolito cae (línea base)** | 0.5 s | 5.6 s | 100 % | **7.7 %** (12 errores de conexión) | 92.3 % | 85.6 % | n/a | — |

Notas:
- **D7:** solo la r1 es válida. En r2 y r3 la carga empezó con el monolito todavía arrancando, porque el orquestador no lo esperaba (ya corregido). Se repetirán.
- **D6:** el "MTTR" es la duración de la pausa (60 s). El script reanuda el contenedor. Durante la pausa, las solicitudes quedan en espera y no fallan rápido; al reanudar, el 96 % se completa.

Lectura frente a los criterios:
- **C1.1:** ninguna caída afecta al 100 % del tráfico, y la propuesta supera al monolito en todos los escenarios de servicio individual (93.6–100 % de éxito global frente a 85.6 %; durante la caída del monolito, 7.7 %).
- **C1.2 (detección ≤ 5 s) y C1.3 (sin propagación):** se cumplen.
- **C1.5 (MTTR ≤ 30 s ante `crash`), C1.6 (0 trabajos perdidos) y C1.7 (auth caído con validación local ≥ 95 %):** se cumplen.
- La caída de auth pasó de **34.7 % de éxito en v1** a 100 % con validación local. El contraste con la validación remota (42.9 % durante la caída) aísla la causa.

---

## 4. Escalabilidad — E4 síncrono en CPU (rampa 10→1000, 180 s por escalón, 3 repeticiones)

Agrupado por número de usuarios activos, con las 3 repeticiones juntas. Latencias en segundos.

**S1: réplica de v1** (transformers fp32, validación remota, sin control de admisión)

| Usuarios | Solicitudes | Éxito | Goodput (req/s) | p50 OK | p95 OK | Rechazos 503 | Timeouts | 5xx |
|---|---|---|---|---|---|---|---|---|
| 10 | 196 | 100 % | 0.36 | 25.2 | 27.5 | 0 % | 0 % | 0 % |
| 50 | 237 | 71.7 % | 0.31 | 78.1 | 99.9 | 0 % | 28.3 % | 0 % |
| 100 | 421 | 20.4 % | 0.16 | 98.9 | 100.3 | 0 % | 79.6 % | 0 % |
| 200 | 873 | 5.4 % | 0.09 | 99.7 | 100.3 | 0 % | 94.6 % | 0 % |
| 500 | 2024 | 1.8 % | 0.07 | 99.5 | 100.3 | 0 % | 98.2 % | 0 % |
| 1000 | 9195 | 0.1 % | 0.01 | 103.8 | 119.6 | 0 % | 40.8 % | 59.1 % (502) |

**S2: v2** (CTranslate2 con 3 líneas, validación local, control de admisión)

| Usuarios | Solicitudes | Éxito | Goodput (req/s) | p50 OK | p95 OK | Rechazos 503 (mediana del tiempo) | Timeouts | 5xx |
|---|---|---|---|---|---|---|---|---|
| 10 | 441 | 100 % | **0.82** | **9.4** | 13.7 | 0 % | 0 % | 0 % |
| 50 | 596 | 76.3 % | **0.84** | 54.6 | 60.8 | 23.7 % (0.46 s) | 0 % | 0 % |
| 100 | 7761 | 2.3 % | 0.34 | 64.6 | 96.7 | 96.9 % (2.9 s) | 0.7 % | 0 % |
| 200 | 7891 | 2.1 % | 0.31 | 73.3 | 83.0 | 97.9 % (9.6 s) | 0 % | 0 % |
| 500 | 7380 | 2.5 % | 0.35 | 80.7 | 101.9 | 90.1 % (26.1 s) | 0 % | 7.3 % (500) |
| 1000 | 7226 | 2.1 % | 0.28 | 103.1 | 122.1 | 26.2 % (49.0 s) | 0.4 % | 71.4 % (500) |

### Lectura

**Mejoras de v2 frente a v1 en el mismo hardware:**
- **Carga baja (10 usuarios):** p50 de 25.2 s a **9.4 s** (2.7× más rápido) y goodput de 0.36 a **0.82 req/s** (2.3×).
- **50 usuarios:** goodput de 0.31 a **0.84 req/s** (2.7×). Ningún timeout, frente al 28 % de v1. El exceso se rechaza en **0.46 s** con 503 + `Retry-After`, en lugar de esperar 100 s y fallar.
- **Desde 100 usuarios:** v1 colapsa en timeouts de 100 s (80–98 %). v2 sigue respondiendo, sobre todo con rechazos controlados.
- **Cota de Little:** X_max = 0.86 req/s con R ≤ 10 s y Z = 2 s da **N_max ≈ 10 usuarios** para v2 en CPU (en v1, 0.34 req/s da ≈ 4). 1000 usuarios síncronos no son alcanzables en CPU para ninguna arquitectura. C2.2 se evalúa con el modo asíncrono (S2b, en curso) y con el criterio de "sin colapso".

**Hallazgo nuevo (debilidad de v2 con sobrecarga extrema):** desde 100 usuarios, el **goodput cae de 0.84 a ≈ 0.3 req/s**. Los rechazos se vuelven lentos (mediana de 9.6 s con 200 usuarios y de 49 s con 1000) y aparecen **errores 500** (7 % con 500 usuarios y 71 % con 1000).

Causa probable: el control de admisión vive en asr-service, **al final** de la cadena. Antes de que una solicitud sea rechazada, el gateway y audio-processor ya recibieron el archivo, lo convirtieron con ffmpeg y lo registraron en la base de datos. Con miles de solicitudes que de todas formas se rechazarán, ese trabajo le **quita CPU a la inferencia**, satura audio-processor (500) y alarga los rechazos.

**Mejora propuesta (arquitectura):** control de admisión **en el borde** (api-gateway). Consiste en un límite de transcripciones síncronas en curso, derivado de la capacidad, que rechace con 503 + `Retry-After` **antes** de reenviar el archivo, y en ajustar la espera máxima de admisión al SLO (10 s en lugar de 60 s). Se espera:
- Goodput estable cerca de 0.8 req/s en todos los escalones.
- Rechazos en menos de 1 s.
- Cero errores 500.
- p95 de las solicitudes admitidas cerca del SLO.

Validarlo requiere repetir S2 (≈ 1 h).

---

## 5. Pendiente

| Pendiente | Estado |
|---|---|
| E4 S2b (asíncrono, 1000 usuarios, aceptados frente a completados) | En curso |
| E3 CPU: propuesta frente a monolito, mismo motor | Tras E4 |
| E6 D7 r2/r3 | Tras E4 |
| Control de WER de CTranslate2 sobre los 2111 clips + RTF del corpus | Tras E3 |
| Admisión en el borde + repetir S2 | Propuesta, por decidir |
| Todo lo de GPU | `docs/15-pendientes-gpu.md` |
