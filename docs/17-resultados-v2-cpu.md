# Resultados v2 en CPU — consolidado (actualizado 2026-10-05, 01:55)

Resultados de la **segunda iteración** de la arquitectura, medidos en el equipo de evaluación **sin GPU** con el **corpus real** y **3 repeticiones** por condición. Reemplaza a `docs/16-resultados-cpu-parciales.md`.

- Cambios de arquitectura: `docs/09-arquitectura-v2.md` y `docs/14-optimizacion-cpu.md`.
- Pendientes en GPU: `docs/15-pendientes-gpu.md`.
- Datos crudos: `experiments/results/` (no versionado).

**Estado:** E6, E8, E9, E4 y E3 **completos**. Pendiente: control de WER sobre los 2111 clips (mañana) y lo de GPU.

---

## 0. Entorno y configuración

| Atributo | Valor |
|---|---|
| Equipo | Intel Core i5-10400 (6 núcleos / 12 hilos, 2.9 GHz), 23.8 GB de RAM |
| GPU | Intel UHD 630 integrada, no utilizable para inferencia |
| Contenedores | Docker Desktop + WSL2, 12 CPU y 16 GB asignados |
| Corpus | IWSLT2026: Huqariq + Siminchik, 2111 clips |
| Clip de carga | `quechua_03068.wav` (Huqariq, 24.05 s; mediana del corpus: 23.04 s) |
| Generador de carga | Locust en el mismo equipo; tiempo de espera de 1 a 3 s entre solicitudes |

**Configuración v2 de este equipo:**
- Motor `ENGINE=ctranslate2` con `INFERENCE_LANES=3` y `CT2_CPU_THREADS=2`.
- Adaptación activa (fp32 ↔ int8 con periodo de prueba).
- Validación local del token.
- Admisión en el borde con `EDGE_MAX_INFLIGHT_TRANSCRIBE=10`.
- API asíncrona sobre Redis Streams.

**Referencia v1 (S1):** transformers fp32, una línea, validación remota y sin control de admisión.

---

## 1. Rendimiento — E8 (inferencia directa contra asr-service, 30 clips reales, 45 s por nivel)

Throughput en **segundos de audio procesados por segundo**; entre paréntesis, la latencia p50/p95 en segundos.

| Configuración | 1 cliente | 4 clientes | 16 clientes | Pico | × base |
|---|---|---|---|---|---|
| transformers fp32 (v1) | 7.1 (2.06/4.95) | 6.1 (10.9/14.9) | 5.0 (38.4/47.7) | 7.1 | 1.00 |
| transformers int8 | 9.8 (1.72/3.75) | 8.8 (6.9/10.0) | 8.1 (25.9/32.7) | 9.8 | 1.39 |
| CTranslate2 fp32, 1 × 6 hilos | 8.3 (2.01/3.93) | 7.4 (7.7/11.7) | 6.2 (33.3/37.1) | 8.3 | 1.17 |
| CTranslate2 int8, 1 × 6 | 13.5 (1.14/2.21) | 12.2 (5.3/6.7) | 10.3 (20.8/23.5) | 13.8 | 1.95 |
| CTranslate2 int8, 2 × 3 | 12.5 | 15.8 | 14.5 | 17.4 | 2.45 |
| **CTranslate2 int8, 3 × 2 (v2)** | 11.9 (1.49/2.42) | **19.4** (3.50/5.01) | 16.3 (14.2/17.5) | **19.4** | **2.74** |
| CTranslate2 int8, 4 × 3 | 13.6 | 18.5 | 16.1 | 18.5 | 2.60 |
| CTranslate2 int8, 6 × 1 | 8.0 | 19.6 | 17.3 | 19.6 | 2.76 |

- **2.7× el throughput de inferencia sin hardware nuevo.** Con 16 clientes, el p95 baja de 47.7 s a 17.5 s.
- Usar los 12 hilos lógicos en una sola línea fue 5× más lento (RTF 0.67): el *hyperthreading* perjudica a CTranslate2.

### Control de WER (una solicitud a la vez, 30 clips)

| Motor / precisión | RTF mediano | WER medio | Salida idéntica a la base | Wilcoxon frente a la base |
|---|---|---|---|---|
| transformers fp32 (base) | 0.135 | 0.735 | 30/30 | — |
| transformers int8 | 0.102 | 0.732 | 2/30 | p = 0.65 |
| CTranslate2 fp32 | 0.110 | 0.763 | 27/30 | p = 0.11 |
| CTranslate2 int8 | **0.069** | 0.766 | 10/30 | p = 0.22 |

Ninguna diferencia es significativa y la mediana de WER es igual (0.75). **Pendiente:** confirmarlo sobre los 2111 clips.

---

## 2. Adaptación — E9-B (ráfaga de 24 clientes durante 120 s, 3 repeticiones por motor)

| Motor | Rep. | Decisiones aplicadas | Reacción | req/s antes → después | Periodo de prueba de int8 | Vuelta a fp32 |
|---|---|---|---|---|---|---|
| CTranslate2 | r1 | 2 | 12.8 s | 0.47 → 0.91 | Superado (4.48 frente a 6.15 s/clip) | Sí |
| CTranslate2 | r2 | 2 | 13.0 s | 0.46 → 0.86 | Superado | Sí |
| CTranslate2 | r3 | 2 | 13.4 s | 0.45 → 0.89 | Superado | Sí |
| transformers | r1 | 2 | 16.8 s | 0.24 → 0.50 | Superado (2.91 frente a 3.13) | Sí |
| transformers | r2 | 2 | 16.4 s | 0.25 → 0.33 | **Revertido** (2.98 frente a 3.03: ganancia < 5 %) | Sí |
| transformers | r3 | 2 | 16.2 s | 0.25 → 0.50 | Superado (2.93 frente a 3.17) | Sí |

- **C2.3:** 6 de 6 repeticiones con decisiones aplicadas; en v1 hubo 0 decisiones en 4 rondas.
- **C2.4:** la degradación que no rindió se revirtió sola y su estado quedó rechazado en el host.
- La misma política llega a resultados distintos según el equipo: en el equipo de ayer, int8 era 2× más lento y se revirtió; aquí acelera. Esto justifica la adaptación verificada por medición.

---

## 3. Disponibilidad — E6 v2 (caída real con SIGKILL, 10 usuarios constantes, 3 repeticiones)

La carga es de 10 usuarios porque es la capacidad por SLO del CPU según la ley de Little (≈ 0.86 × 12). Con 50 usuarios, solo el 57.5 % tenía éxito **antes** del fallo, así que la prueba medía saturación y no tolerancia a fallos. Esa corrida se conserva aparte en `results/e6_overload_50users/`.

| Escenario | Detección (s) | MTTR (s) | Éxito antes | Éxito durante | Éxito después | Éxito global | Fallos durante | Propagación | Trabajos perdidos |
|---|---|---|---|---|---|---|---|---|---|
| D1 asr-service | 1.3 (0.6–2.2) | **4.9** (4.0–6.0) | 100 % | 0 % | 100 % | 93.6 % | 45 × 503 rápidos | No | — |
| D2 auth-service, validación local | 1.3 (1.1–1.6) | 5.5 (4.2–6.2) | 100 % | **100 %** | 100 % | **100 %** | — | No | — |
| D2b auth-service, validación remota (v1) | 1.4 (0.3–2.1) | 4.9 (4.5–5.4) | 100 % | 42.9 % | 100 % | 97.8 % | 16 × 502 | No | — |
| D3 transcription-manager | 1.8 (1.3–2.4) | 6.0 (4.9–6.9) | 100 % | **100 %** | 100 % | **100 %** | — | No | — |
| D4 asr-service, carga asíncrona | 1.9 (0.8–2.6) | 4.9 (4.5–5.4) | 100 % | 100 % | 100 % | **100 %** | — | No | **0** |
| D5 Redis | 1.1 (0.9–1.5) | 8.7 (8.6–8.7) | 100 % | **100 %** | 100 % | **100 %** | — | No | — |
| D6 asr-service congelado 60 s | 1.1 (0.4–1.8) | (60 s; el script lo reanuda) | 100 % | — | 96.0 % | 96.9 % | — | No | — |
| **D7 monolito (línea base)** | 1.2 (0.4–2.1) | 5.6 (5.1–6.1) | 100 % | **0 %** | 81.3 % | **60.5 %** | 83 errores de conexión | n/a | — |

**Criterios C1.1, C1.2, C1.3, C1.5, C1.6 y C1.7: se cumplen.** La caída de auth-service pasó de **34.7 % de éxito en v1** a 100 % con validación local. El contraste con la validación remota aísla la causa.

---

## 4. Escalabilidad — E4 síncrono (rampa 10 → 1000 usuarios, 180 s por escalón, mediana de 3 repeticiones)

**Goodput** = transcripciones completadas con éxito por segundo, y es la métrica principal. El "éxito %" incluye los reintentos inmediatos del generador después de cada rechazo, por eso es bajo en sobrecarga aunque el sistema esté atendiendo a su capacidad.

### Comparación (goodput req/s | p50 / p95 de las solicitudes atendidas | tipo de fallo)

| Usuarios | **S1: v1** | **S2: v2 sin borde** | **S2c: v2 completa** |
|---|---|---|---|
| 10 | 0.36 · 25.6 / 26.8 s · — | 0.82 · 9.4 / 13.3 s · — | **0.82 · 9.5 / 13.8 s · —** |
| 50 | 0.33 · 84.7 / 99.9 s · 24 % timeout | 0.86 · 54.6 / 56.9 s · 9 % 503 | **0.77 · 13.1 / 14.3 s · 503 en 0.01 s** |
| 100 | 0.12 · 98.6 / 100.3 s · 84 % timeout | 0.34 · 64.0 / 96.4 s · 503 en 3.0 s | **0.68 · 14.2 / 17.2 s · 503 en 0.01 s** |
| 200 | 0.11 · 99.7 / 100.3 s · 93 % timeout | 0.31 · 72.6 / 79.9 s · 503 en 9.6 s | **0.48 · 20.4 / 22.6 s · 503 en 0.06 s** |
| 500 | 0.06 · 99.9 / 100.3 s · 99 % timeout | 0.34 · 80.1 / 100.5 s · 503 en 25.8 s + 7 % 500 | **0.48 · 22.9 / 27.4 s · 503 en 2.9 s · 0 % 5xx** |
| 1000 | 0.01 · 105 / 110 s · 40 % timeout + **60 % 5xx** | 0.22 · 105 / 121 s · **72 % 500** | **0.44 · 26.5 / 33.5 s · 0 % 5xx** |

Rango de goodput entre repeticiones de S2c: 0.81–0.84 (10), 0.74–0.85 (50), 0.66–0.82 (100), 0.47–0.73 (200), 0.46–0.48 (500) y 0.42–0.48 (1000).

### Lectura

- **v2 frente a v1, mismo CPU:** con 10 usuarios, el goodput se multiplica por **2.3** (0.36 → 0.82) y la latencia p50 baja de **25.6 s a 9.5 s**. v1 colapsa desde 50 usuarios con timeouts de 100 s; v2 nunca colapsa.
- **Admisión en el borde (S2c frente a S2):** con 100 usuarios, el goodput se multiplica por **2** (0.34 → 0.68); las solicitudes atendidas pasan de un p95 de 96 s a **17 s**; los rechazos pasan de 3 s a **0.01 s**, y los **errores 500 desaparecen** (72 % → 0 % con 1000 usuarios).
- **Ley de Little:** el techo de usuarios síncronos con R ≤ 10 s y Z = 2 s es de **≈ 10 usuarios en v2** (0.86 × 12), frente a ≈ 4 en v1 (0.36 × 12). Ninguna arquitectura atiende 1000 usuarios síncronos en este CPU; v2 sigue atendiendo a su capacidad y rechaza el exceso de forma explícita.
- La caída del goodput con 200 usuarios o más en S2c (0.48) se atribuye al generador de carga en el mismo CPU: reenvía cada rechazo de inmediato con el audio completo (≈ 200 solicitudes/s con 1000 usuarios) e ignora `Retry-After`. Ver §7.

### Asíncrono — S2b (1000 usuarios con `/api/v1/jobs`)

| Repetición | Enviados | Aceptados | Aceptación | Procesados | Fallidos | Completitud |
|---|---|---|---|---|---|---|
| r1 | 1905 | 1905 | 100.00 % | 1905 | 0 | **100 %** |
| r2 | 1757 | 1756 | 99.94 % | 1756 | 0 | **100 %** |
| r3 | 1865 | 1865 | 100.00 % | 1865 | 0 | **100 %** |
| **Total** | 5527 | 5526 | **99.98 %** | 5526 | **0** | **100 %** |

Sin pérdidas ni duplicados. El único envío no aceptado fue un 500 en el pico de 1000 usuarios. La cola absorbe la demanda que supera la capacidad y la procesa a ≈ 0.85 trabajos/s, a cambio de tiempo de espera. Durante la carga, la adaptación pasó a int8 (3.9 frente a 5.0 s por clip).

---

## 4b. Rendimiento frente al monolito — E3 v2

Misma rampa que E4 (10 → 1000 usuarios, 180 s por escalón), 3 repeticiones por arquitectura. **Ambas arquitecturas con el mismo motor (CTranslate2), la misma precisión fijada (fp32, sin adaptación) y las mismas 3 líneas de inferencia**, para aislar el estilo arquitectónico. El monolito no tiene admisión en el borde, ni cola asíncrona ni adaptación. Informe completo en `experiments/results/e3v2_report.md`.

| Usuarios | Propuesta: goodput | Propuesta: p50 / p95 (s) | Propuesta: fallos | Monolito: goodput | Monolito: p50 / p95 (s) | Monolito: fallos |
|---|---|---|---|---|---|---|
| 10 | **0.56** [0.53–0.57] | **14.9 / 19.8** | — | 0.48 [0.31–0.50] | 15.6 / 24.5 | — |
| 50 | **0.56** | 17.7 / 21.7 | Exceso con 503 | 0.01 | 22.3 / 23.0 (2 solicitudes) | Sin respuesta |
| 100 | **0.45** | 21.0 / 26.5 | Exceso con 503 | **0** | — | 100 % sin respuesta (300 s) |
| 200 | **0.33** | 27.9 / 34.5 | Exceso con 503 | **0** | — | 100 % sin respuesta |
| 500 | **0.35** | 30.4 / 37.1 | Exceso con 503 | **0** | — | 100 % sin respuesta |
| 1000 | **0.37** | 32.1 / 41.2 | Exceso con 503; 0 % 5xx | **0** | — | 100 % sin respuesta |

**Prueba estadística (10 usuarios, el único escalón donde ambas completan solicitudes):** U de Mann-Whitney, p = 0.034, delta de Cliff = −0.107 (**despreciable**). Mediana de 14.9 s (propuesta) frente a 15.6 s (monolito). En carga baja ambas responden en tiempos equivalentes; la propuesta tiene un p95 menor (19.8 frente a 24.5 s) y un goodput 17 % mayor. Las tres llamadas HTTP extra entre servicios no penalizan.

**Por qué colapsa el monolito desde 50 usuarios** (verificado: el contenedor no se reinició ni sufrió OOM, y siguió procesando solicitudes ya abandonadas): su único *worker* ejecuta el login con **bcrypt síncrono** en el mismo proceso que la transcripción. Cada usuario nuevo de la rampa bloquea el bucle de eventos unos 0.25 s, y con unos 10 logins por segundo el proceso deja de atender todo, transcripciones incluidas. En la propuesta, el mismo código vive en auth-service con 4 *workers* propios y la inferencia sigue sin interferencias. Es aislamiento de fallos **y de competencia por recursos** entre componentes.

**C3.3: se cumple.** La propuesta no es más lenta que el monolito: el efecto es despreciable en carga baja, y bajo carga la propuesta sigue atendiendo mientras el monolito deja de responder.

---

## 5. Criterios de aceptación (segunda iteración)

| Código | Resultado | Estado |
|---|---|---|
| C1.1 | Propuesta: 93.6–100 % de éxito global ante cada caída individual. Monolito: 60.5 % (0 % durante su caída) | **Cumple** |
| C1.2 | Detección media de 1.1–1.9 s | **Cumple** |
| C1.3 | Sin propagación en ningún escenario | **Cumple** |
| C1.4 | 100 % de éxito dentro de la capacidad (10 usuarios) en todas las configuraciones v2 | **Cumple** |
| C1.5 | MTTR de 4.9–8.7 s (≤ 30 s) | **Cumple** |
| C1.6 | 0 trabajos perdidos (D4) | **Cumple** |
| C1.7 | 100 % con auth caído y validación local (42.9 % con validación remota) | **Cumple** |
| C2.1 | Goodput máximo 2.4× el de v1 (0.86 frente a 0.36); techo de Little de 10 frente a 4 usuarios | **Cumple** |
| C2.2 | Asíncrono: 99.98 % aceptados y 100 % completados. Síncrono: 0 % de errores 5xx y exceso rechazado con 503 + `Retry-After` | **Cumple** |
| C2.3 | 6 de 6 repeticiones con decisiones aplicadas | **Cumple** |
| C2.4 | La adaptación que no rindió se revirtió sola | **Cumple** |
| C3.1 | RTF mediano de 0.149 sobre el corpus (v1) y 0.069 con CTranslate2 int8 (muestra) | **Cumple** |
| C3.2 | p50 de 9.5 s con 10 usuarios y un clip de 24 s (local); 4.7 s en la nube (v1) | **Cumple** |
| C3.3 | Con 10 usuarios: 14.9 frente a 15.6 s (p = 0.034, δ = −0.107, despreciable). Desde 50 usuarios el monolito deja de responder y la propuesta mantiene 0.33–0.56 req/s | **Cumple** |
| C3.4 | Requiere GPU. Medido en GPU: `cuda-fp16-b8` = 8.8× `cpu-fp32-b1` con WER sin diferencia significativa (`docs/18`, §1) | **Cumple (GPU)** |
| C4.x | Sin cambios respecto del capítulo 5 v1 | — |
| C5.x | Usabilidad | Pendiente |

---

## 6. Defectos encontrados y corregidos durante la validación

| Defecto | Dónde | Efecto | Corrección |
|---|---|---|---|
| 200 sin transcripción con asr-service caído | v1 (audio-processor) | El 100 % de E6 v1 para asr-service estaba inflado | Propaga 503; el cliente valida el cuerpo |
| CTranslate2 volvía a decodificar la cola de la ventana | Motor nuevo | Alucinaciones (un clip pasó de WER 0.13 a 2.67) | Decodificación de una sola ventana, como transformers |
| `lag` de Redis Streams desactualizado | audio-processor (`job_queue.backlog`) | La cola parecía tener 1197 trabajos estando vacía (afecta la admisión y a KEDA) | Conteo exacto de los mensajes no entregados (2 tests) |
| Cupo de admisión no liberado al desconectarse el cliente | api-gateway (nuevo) | Rechazos espurios con poca carga | `asyncio.shield` en la liberación (test con *cancel scope* de anyio) |
| Límite de admisión de 6, demasiado estricto | Configuración | 76 % de rechazos con 10 usuarios y goodput de 0.52 | Límite de 10, derivado de Little con la saturación medida (ablación en `results/e4_S2c_cap6_ablation/`) |

Tests: api-gateway **75**, asr-service **44**, audio-processor **26**; todos pasan.

---

## 7. Amenazas a la validez

- **Generador de carga en el mismo equipo:** con 500–1000 usuarios, sus reintentos inmediatos compiten por la CPU. El goodput de esos escalones es una **cota inferior**.
- **Proxy de Docker Desktop:** con 1000 usuarios se satura y retiene conexiones que entrega a la corrida siguiente. Se añadió una espera de vaciado (`quiesce()`) entre corridas y se descartaron y repitieron las repeticiones contaminadas (`results/e4_S2c_r3_proxy_backlog/`, `results/e4_S2c_cap10_slotleak/`). Los experimentos usan `127.0.0.1`, porque el relay IPv6 de `localhost` se cuelga.
- **Sin GPU:** C3.4 y la conmutación CPU↔GPU (RQ1) no se pudieron medir en este equipo; se evaluaron en un equipo con GPU (`docs/18-resultados-v2-gpu.md`).
- **Un solo clip en las cargas:** la variabilidad de duración se cubre en E8 (muestra estratificada) y en E2 (corpus).
- **Control de WER del motor nuevo:** verificado con 30 clips; los 2111 quedan pendientes.

---

## 8. Pendiente

| Pendiente | Cuándo |
|---|---|
| Control de WER de CTranslate2 sobre 2111 clips y RTF del corpus | Mañana |
| Todo lo de GPU | **Hecho**: `docs/18-resultados-v2-gpu.md` |
| Commit de los cambios de esta sesión | Al cerrar |
