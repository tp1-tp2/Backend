# Resultados v2 en GPU — consolidado (2026-10-05)

Resultados de la **segunda iteración** de la arquitectura medidos en un **equipo con GPU**, con el **corpus real** y **3 repeticiones** por condición (E8 y E2: una corrida). Completa lo que quedó pendiente en `docs/17-resultados-v2-cpu.md` y sigue el protocolo de `docs/15-pendientes-gpu.md`.

- Evidencia versionada: `experiments/results_v2_gpu/` (ver su `README.md`).
- Datos crudos: `experiments/results/` (no versionado).
- Resultados en CPU, para comparar: `docs/17-resultados-v2-cpu.md`.

**Estado:** verificación, E8, E9, E4 (S3, S3c, S4), E3 y E2 **completos**. Opcionales no ejecutados: E6 con 50 usuarios, E4 S1 en este equipo y topología híbrida / Azure.

---

## 0. Configuración de las corridas

| Atributo | Valor |
|---|---|
| Corpus | IWSLT2026: Huqariq + Siminchik, 2111 clips |
| Clip de carga | `quechua_03068.wav` (Huqariq, 24.05 s), el mismo que en CPU |
| Muestra de E8 | Muestra estratificada de 30 clips (`manifest_e5_sample.csv`) |
| Motor v2 | transformers con planificador de *micro-batching*; adaptación activa (dispositivo, precisión y tamaño de *batch*) |
| Admisión en el borde (S3c, S4, E3) | `--edge-inflight-gpu 73`, calibrado con S3 (§3.1) |
| Generador de carga | Locust en el mismo equipo; espera de 1 a 3 s entre solicitudes |

---

## 1. Rendimiento — E8 (inferencia directa contra asr-service)

Throughput en **segundos de audio procesados por segundo**. Concurrencia 1–32, 60 s por nivel; la referencia de CPU optimizada, 1–16 y 45 s por nivel.

| Configuración | Pico (s de audio/s) | × `cpu-fp32-b1` | p50 con 1 cliente |
|---|---|---|---|
| `cpu-fp32-b1` (base de C3.4) | 11.2 | 1.0× | 1.375 s |
| `cpu-int8-b1` | 16.8 | 1.5× | 1.070 s |
| `ct2-int8-l3t2` (mejor configuración de CPU, `docs/14`) | 28.4 | 2.5× | — |
| `cuda-fp32-b1` | 36.5 | 3.3× | 0.389 s |
| `cuda-fp16-b1` | 58.7 | 5.3× | 0.241 s |
| `cuda-fp16-b4` | 91.3 | 8.2× | 0.273 s |
| **`cuda-fp16-b8`** | **98.4** | **8.8×** | 0.272 s |
| `cuda-fp16-b16` | 100.0 | 8.9× | 0.270 s |

- **C3.4: se cumple.** `cuda-fp16-b8` alcanza 8.8× la base (umbral: 5×) y **3.5×** la mejor configuración de CPU (`ct2-int8-l3t2`).
- Latencia con un cliente frente a la base: todas las configuraciones de GPU son significativamente más rápidas (Mann-Whitney p < 0.001; δ de Cliff entre −0.83 y −0.98, grande).
- El *batching* se satura en *batch* 8: pasar a 16 aporta un 1.6 %.
- Con 32 clientes, `cpu-fp32-b1` supera la capacidad y la admisión de asr-service rechaza el exceso con 503 en ~0.01 s, el comportamiento esperado de v2.

### Control de WER (por clip, 30 clips; `results_v2_gpu/e8_wer_control.md`)

| Configuración | WER medio | WER mediana | Salida idéntica a la base | Wilcoxon frente a la base |
|---|---|---|---|---|
| `cpu-fp32-b1` (base) | 0.735 | 0.750 | 30/30 | — |
| `cpu-int8-b1` | 0.727 | 0.748 | 3/30 | p = 0.78 |
| `cuda-fp32-b1` | 0.736 | 0.750 | 29/30 | p = 0.32 |
| `cuda-fp16` (*batch* 1, 4, 8 y 16) | 0.742 | 0.750 | 25/30 | p = 0.18 |
| `ct2-int8-l3t2` | 0.771 | 0.777 | 12/30 | p = 0.099 |

Ninguna diferencia es significativa. Las salidas en fp16 son idénticas entre tamaños de *batch*, y el WER base (0.735) coincide con el medido en CPU (`docs/17`, §1). El "WER de corpus" de `e8_report.md` se calcula sobre conjuntos distintos de transcripciones en cada configuración; el control válido es el WER por clip.

---

## 2. Adaptación — E9 (ráfaga de 24 clientes durante 120 s, 3 repeticiones por escenario)

Fases: 30 s de reposo, 120 s de ráfaga y 90 s de enfriamiento.

| Escenario | Reacción | Decisiones aplicadas (por eje) | Periodo de prueba | req/s antes → después | Estado final |
|---|---|---|---|---|---|
| A — GPU adaptativa | 3.7–4.0 s | precisión 1–2, *batch* 4–6 | fp16 superado en 3/3 (0.129–0.133 frente a 0.204–0.208 s/clip) | 2.1–4.0 → 9.6–9.7 | cuda/fp32/b8 en r1 y r3; **r2 terminó en cuda/fp16/b8** |
| B — solo CPU | 14.9–15.1 s | precisión 2 | int8 superado en 3/3 (1.21–1.27 frente a 1.68–1.76 s/clip) | 0.53 → 0.86 | cpu/fp32/b1 en 3/3 |
| C — CPU→GPU (RQ1) | 4.1–4.2 s | **dispositivo 1**, precisión 2, *batch* 3–5 | fp16 superado en 3/3 (0.114–0.117 frente a 0.203–0.205 s/clip) | 3.8–3.9 → 9.8 | cuda/fp32/b8 en 3/3 |

- **C2.3: se cumple en 9 de 9 repeticiones.** En GPU la adaptación reacciona en ~4 s: sube el *batch* de 8 a 16 y pasa a fp16 bajo la ráfaga.
- **C2.4:** todas las degradaciones superaron el periodo de prueba, así que no hubo reversiones en este equipo. El mecanismo de reversión ya se verificó en CPU (`docs/17`, §2).
- **RQ1: migración CPU→GPU en tiempo de ejecución en 3 de 3 repeticiones**, sin reiniciar el servicio, a los ~9 s del arranque. Ocurrió durante la fase de reposo, sin inferencias en curso. Demuestra la migración en caliente, pero no que se haga sin interrumpir inferencias, porque no había ninguna en curso en ese momento.
- En A r2 el servicio no volvió a fp32 dentro de los 90 s de enfriamiento: terminó en fp16 con *batch* 8.

---

## 3. Escalabilidad — E4 (rampa 10 → 1000 usuarios, 180 s por escalón, mediana de 3 repeticiones)

**Goodput** = transcripciones completadas con éxito por segundo, la métrica principal. El "éxito %" incluye los reintentos inmediatos del generador después de cada rechazo, por eso es bajo en sobrecarga aunque el sistema atienda a su capacidad.

### 3.1 S3 — v2 en GPU sin admisión en el borde (ablación y calibración)

| Usuarios | Éxito | Goodput req/s [mín–máx] | p50 / p95 de las atendidas | Rechazo 503 (mediana del rechazo) | 5xx |
|---|---|---|---|---|---|
| 10 | 100 % | 3.04 [3.01–3.09] | 1.2 / 1.8 s | 0 % | 0 % |
| 50 | 100 % | 9.28 [9.27–9.37] | 3.2 / 5.3 s | 0 % | 0 % |
| 100 | 79.9 % | 9.51 [9.51–9.60] | 7.7 / 8.5 s | 20.1 % (0.25 s) | 0 % |
| 200 | 15.7 % | 4.71 [4.62–4.80] | 17.8 / 19.6 s | 84.3 % (2.27 s) | 0 % |
| 500 | 11.3 % | 3.64 [3.56–3.73] | 27.0 / 35.3 s | 88.7 % (11.55 s) | 0 % |
| 1000 | 14.1 % | 3.64 [3.47–3.73] | 43.4 / 65.9 s | 77.2 % (24.77 s) | 9.4 % |

**Calibración del límite del borde** (`docs/15`, §4.2): en el escalón de goodput máximo (100 usuarios), N = X_sat × R_sat = 9.51 req/s × 7.7 s ≈ **73** (en CPU fue 10).

### 3.2 S3c — v2 completa en GPU (admisión en el borde, N = 73)

| Usuarios | Éxito | Goodput req/s [mín–máx] | p50 / p95 de las atendidas | Rechazo 503 (mediana del rechazo) | 5xx |
|---|---|---|---|---|---|
| 10 | 100 % | 3.06 [3.04–3.06] | 1.2 / 1.9 s | 0 % | 0 % |
| 50 | 100 % | 9.39 [9.37–9.54] | 3.2 / 4.2 s | 0 % | 0 % |
| 100 | 60.6 % | 9.78 [9.78–9.87] | 7.0 / 7.6 s | 39.4 % (0.00 s) | 0 % |
| 200 | 14.7 % | 9.24 [9.24–9.24] | 8.3 / 8.7 s | 85.3 % (0.00 s) | 0 % |
| 500 | 4.2 % | 8.44 [8.44–8.44] | 9.2 / 9.6 s | 95.8 % (0.00 s) | 0 % |
| 1000 | 1.9 % | 7.91 [7.91–8.00] | 9.7 / 10.6 s | 98.1 % (0.01 s) | 0 % |

### 3.3 S4 — v2 en GPU, asíncrono (`/api/v1/jobs`) con 1000 usuarios

| Repetición | Enviados | Aceptados | Aceptación | Procesados | Fallidos | Duplicados | Completitud |
|---|---|---|---|---|---|---|---|
| r1 | 8543 | 8543 | 100 % | 8543 | 0 | 0 | **100 %** |
| r2 | 8236 | 8236 | 100 % | 8236 | 0 | 0 | **100 %** |
| r3 | 8372 | 8372 | 100 % | 8372 | 0 | 0 | **100 %** |
| **Total** | 25 151 | 25 151 | **100 %** | 25 151 | **0** | **0** | **100 %** |

| Usuarios | Goodput (trabajos/s) | p50 / p95 de extremo a extremo |
|---|---|---|
| 10 | 2.72 | 2.1 / 2.2 s |
| 50 | 8.32 | 4.1 / 8.2 s |
| 100 | 8.73 | 10.2 / 10.2 s |
| 200 | 8.74 | 22.2 / 115.9 s |
| 500 | 8.55 | 60.8 / 121.8 s |
| 1000 | 9.42 | 108.3 / 130.6 s |

La cola quedó vacía al terminar cada repetición, sin tiempo de vaciado adicional.

### Lectura

- **Admisión en el borde (S3c frente a S3):** con 1000 usuarios, el goodput se multiplica por **2.2** (3.64 → 7.91 req/s); el p95 de las solicitudes atendidas baja de **65.9 s a 10.6 s**; los rechazos pasan de 25 s a **0.01 s**, y los **errores 5xx desaparecen** (9.4 % → 0 %).
- **GPU frente a CPU (v2 completa, `docs/17` §4):** goodput máximo de ~9.8 frente a 0.86 req/s (**~11×**); con 1000 usuarios, 7.91 frente a 0.44 req/s (**~18×**). Capacidad por SLO (p95 ≤ 10 s, error ≤ 5 %) de **50 usuarios** frente a 10. Techo de Little con R ≤ 10 s y Z = 2 s: ≈ 9.9 × 12 ≈ **119 usuarios** frente a ≈ 10.
- **Asíncrono:** procesó **~4.6× más trabajos** que en CPU (25 151 frente a 5527 en 3 repeticiones), sin pérdidas. Desde 200 usuarios la demanda supera la capacidad (~9 trabajos/s) y la cola la absorbe a cambio de espera (p95 de ~2 min con 1000 usuarios), sin rechazar nada.
- Ninguna arquitectura atiende 1000 usuarios **síncronos** dentro del SLO en una sola GPU: el techo de Little es ~119. v2 sigue atendiendo cerca de su capacidad y rechaza el exceso de forma explícita.

---

## 4. Rendimiento frente al monolito — E3 (ambas arquitecturas en cuda/fp32)

Misma rampa que E4, 3 repeticiones por arquitectura. Las dos fijadas en **cuda/fp32, sin adaptación**. La propuesta conserva su planificador con *batching* y la admisión en el borde (N = 73), que son parte de la arquitectura. Informe completo en `results_v2_gpu/e3v2_gpu_report.md`.

| Usuarios | Propuesta: goodput · p50 / p95 | Propuesta: fallos | Monolito: goodput · p50 / p95 | Monolito: fallos | Mann-Whitney · δ de Cliff |
|---|---|---|---|---|---|
| 10 | **3.06** · 1.3 / 1.8 s | — | 1.63 · 4.3 / 5.2 s | — | p ≈ 0 · −0.933 (grande) |
| 50 | **4.94** · 7.8 / 9.9 s | — | 1.52 · 25.4 / 32.9 s | — | p ≈ 0 · −0.976 (grande) |
| 100 | **5.07** · 14.5 / 15.3 s | 503 inmediatos | 1.56 · 45.3 / 56.5 s | 48 × 500 | p ≈ 0 · −0.974 (grande) |
| 200 | **4.53** · 16.6 / 17.8 s | 503 inmediatos | 1.28 · 53.5 / 66.0 s | 726 × 500 | p ≈ 0 · −0.963 (grande) |
| 500 | **4.18** · 18.5 / 20.2 s | 503 inmediatos | 0.97 · 53.7 / 68.9 s | 4869 × 500 | p = 8e−180 · −0.784 (grande) |
| 1000 | **3.91** · 19.6 / 22.3 s | 503 inmediatos; 0 % 5xx | 0.30 · 67.9 / 69.5 s | 1161 × 500 + 400 errores de conexión | p = 1e−68 · −0.835 (grande) |

- **C3.3: se cumple.** En GPU la propuesta no solo no es más lenta, sino que es **significativamente más rápida en todos los escalones**, con efecto grande: con 10 usuarios responde en 1.3 frente a 4.3 s (mediana) con 1.9× el goodput; con 1000, atiende 13× más (3.91 frente a 0.30 req/s).
- **Diferencia frente a CPU:** en CPU, con 10 usuarios, el efecto fue despreciable (14.9 frente a 15.6 s, `docs/17` §4b). En GPU, el *micro-batching* del planificador, que el monolito no tiene, marca la diferencia incluso con poca carga.
- **El monolito sí responde con 50–100 usuarios en GPU** (en CPU dejaba de responder desde 50), pero con latencias de 25–68 s. Desde 100 usuarios falla el login con 500: su único proceso agota el *pool* de conexiones a la base de datos (`QueuePool limit of size 5 overflow 10 reached`). En la propuesta, la autenticación vive en su propio servicio y no compite con la inferencia.
- El límite N = 73 se calibró con S3, con la adaptación activa (fp16). En E3 la propuesta queda fijada en fp32, que rinde ~5 req/s, así que desde 100 usuarios su p95 (15–22 s) supera el SLO de 10 s. No afecta a C3.3, que es una comparación relativa con el mismo dispositivo y precisión, pero el límite no está recalibrado para fp32.

---

## 5. Rendimiento sobre el corpus completo — E2 (2111 clips, uno a la vez)

Configuración v2 por defecto (adaptación activa); todas las inferencias se ejecutaron en cuda/fp32.

| Métrica | n | Mediana [IQR] | CPU fp32 (capítulo 5) |
|---|---|---|---|
| **RTF** | 2111 | **0.031** [0.026–0.038] | 0.149 |
| WER | 2111 | 0.697 [0.500–0.852] | 0.697 |
| CER | 2111 | 0.172 [0.089–0.341] | — |

| Fuente | n | WER mediana | WER media | CER mediana | RTF mediana |
|---|---|---|---|---|---|
| Huqariq | 1413 | 0.714 | 0.705 | 0.192 | 0.029 |
| Siminchik | 698 | 0.638 | 0.624 | 0.121 | 0.035 |

| Duración del clip | n | WER medio |
|---|---|---|
| 0–5 s | 386 | 0.574 |
| 5–15 s | 522 | 0.502 |
| 15–30 s | 1202 | 0.789 |
| 30–60 s | 1 | 0.594 |

- **C3.1: se cumple.** RTF mediano de 0.031: ~4.8× más rápido que en CPU fp32; un clip de 24 s se procesa en ~0.75 s.
- **La GPU no altera la calidad:** la mediana de WER (0.697) es idéntica a la de CPU.
- 14 clips con WER > 1.5 (0.7 %, posibles alucinaciones), 46 clips perfectos (2.2 %) y 0 transcripciones vacías.

---

## 6. Criterios de aceptación con GPU

| Código | Resultado | Estado |
|---|---|---|
| C2.1 | Goodput de S3c ~9.8 req/s frente a 0.36 de v1 (S1, CPU) y 0.86 de v2 en CPU; capacidad por SLO de 50 usuarios; techo de Little ≈ 119 | **Cumple** |
| C2.2 | Asíncrono: 100 % de 25 151 trabajos aceptados y completados, 0 pérdidas. Síncrono: exceso rechazado con 503 en ≤ 0.01 s y 0 % de 5xx hasta 1000 usuarios | **Cumple** |
| C2.3 | 9 de 9 repeticiones con decisiones aplicadas; reacción de ~4 s en GPU | **Cumple** |
| C2.4 | Todas las degradaciones superaron el periodo de prueba (sin reversiones en este equipo; la reversión se verificó en CPU) | **Cumple** (verificado en CPU) |
| RQ1 | Migración CPU→GPU en tiempo de ejecución en 3 de 3, sin reinicio; ocurrió en reposo, sin inferencias en curso | **Evidencia parcial** |
| C3.1 | RTF mediano de 0.031 sobre 2111 clips | **Cumple** |
| C3.3 | Propuesta significativamente más rápida que el monolito en los 6 escalones (δ de Cliff de −0.78 a −0.98) | **Cumple** |
| C3.4 | `cuda-fp16-b8` = 8.8× `cpu-fp32-b1` con WER sin diferencia significativa (p = 0.18) | **Cumple** |

---

## 7. Amenazas a la validez

- **Generador de carga en el mismo equipo:** Locust comparte CPU con la plataforma y reenvía cada rechazo de inmediato, ignorando `Retry-After` (~65 000 solicitudes en el escalón de 1000 usuarios de S3c). El goodput de los escalones altos es una **cota inferior**.
- **Un solo clip en las cargas** (E4, E3, E9): la variabilidad de duración se cubre en E8 (muestra estratificada) y en E2 (corpus completo).
- **RQ1:** la migración CPU→GPU se observó en reposo; no se midió con inferencias en curso.
- **E3 con precisión fijada en fp32:** el límite del borde (N = 73) se calibró con la adaptación activa y no se recalibró para fp32.
- **Hardware distinto al de `docs/17`:** las comparaciones con CPU de `docs/17` cruzan equipos. Las razones de C3.4 y la referencia `ct2-int8-l3t2` se midieron en el mismo equipo.
- **CTranslate2 en GPU:** no se evaluó; los resultados de GPU usan el motor transformers.

---

## 8. Pendiente

| Pendiente | Tipo |
|---|---|
| Integrar estos resultados en `cap-5-extracted.md` | Documentación |
| E6 con 50 usuarios en GPU (`docs/15`, §7) | Opcional |
| E4 S1 (v1) en el mismo equipo con GPU, para comparar C2.1 en el mismo hardware | Opcional |
| Topología híbrida / Azure con KEDA (`docs/15`, punto 8) | Opcional (arquitectura) |
| Control de WER de CTranslate2 sobre los 2111 clips (`docs/17`, §8) | Pendiente de CPU |
| Usabilidad (C5.x) | Fuera de este alcance |
