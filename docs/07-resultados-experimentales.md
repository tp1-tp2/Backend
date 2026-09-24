# Resumen de resultados experimentales (E1-E6)

Este documento consolida los resultados reales de todos los experimentos corridos contra el artefacto (E1-E6 del Protocolo Experimental). Reemplaza los placeholders `[pendiente]` del paper — ver también `Paper_v2_resultados.docx` para la versión ya integrada al texto completo.

**Nota de rigor**: durante E4 se encontró y corrigió un bug real en `experiments/e4_load_test/report.py` (el error rate por escalón se calculaba con una muestra instantánea, no un conteo acumulado — ver detalle en la sección E4). Todos los números de E4 en este documento ya reflejan la corrección.

---

## E1 — Caracterización del corpus

| Métrica | Valor |
|---|---|
| Clips | 2111 |
| Duración total | 10:47:32 (10.79h) |
| Duración por clip | min=0.59s, max=34.16s, promedio=18.40s, mediana=23.04s |
| Hablantes identificados | 47 |
| Variante dialectal declarada | solo Siminchik (698 clips): "quechua sureño" |
| Condición de grabación declarada | solo Siminchik (698 clips): radio |
| Fuentes | Huqariq (IWSLT2026/que_spa_synthetic_translation, Zevallos et al. 2022): 1413 clips · Siminchik (IWSLT2026/que_spa_unconstrained, Cardenas et al. 2018): 698 clips |

**Decisión metodológica**: se evitó deliberadamente `QuechuaBase/asr-puno-quechua` y Mozilla Common Voice (variante qxp) por su probable solapamiento con los datos de ajuste fino del modelo evaluado (`QuechuaBase/whisper-base-qxp-finetuned`), reduciendo el riesgo de contaminación train/test.

**Limitación**: Huqariq (67% del corpus) no reporta variante dialectal, condición de grabación, sexo ni edad del hablante.

---

## E2 — WER / CER / RTF

| Métrica | n | Valor | Intervalo | Base |
|---|---|---|---|---|
| WER | 2111 | 0.697 | [0.500, 0.852] | mediana±IQR (no normal, Shapiro p<0.001) |
| CER | 2111 | 0.172 | [0.089, 0.343] | mediana±IQR (no normal, Shapiro p<0.001) |
| RTF | 2111 | 0.149 | [0.120, 0.201] | mediana±IQR (no normal, Shapiro p<0.001), CPU/fp32 |

### Por fuente del corpus

| Fuente | n | WER mediana | WER media | CER mediana | RTF mediana |
|---|---|---|---|---|---|
| Huqariq | 1413 | 0.714 | 0.705 | 0.192 | 0.135 |
| Siminchik | 698 | 0.638 | 0.625 | 0.121 | 0.183 |

**Anomalías**: 13 clips (0.6%) con WER>1.5 (posible alucinación/inserción excesiva) · 46 clips (2.2%) con WER=0 (transcripción perfecta) · 0 transcripciones vacías.

**Interpretación**: el WER elevado es consistente con la alta complejidad morfológica del quechua (Romero et al., 2024) y con la decisión de evitar corpora contaminados — no indica una falla del artefacto (RTF muy por debajo de 1, sin transcripciones vacías).

---

## E3 — Monolito vs. arquitectura propuesta

Misma rampa de carga (10→50→100→200→500→1000 usuarios, 6 escalones de 180s) corrida localmente contra ambas arquitecturas, mismo hardware.

| Métrica | Propuesta (media) | Monolito (media) | Test | p-value | Effect size | ¿Significativo? |
|---|---|---|---|---|---|---|
| p50 latencia (ms) | 16,787.4 | 24,882.3 | Mann-Whitney U | 0.0000 | Cliff's δ=-0.579 | **Sí** |
| p95 latencia (ms) | 69,787.4 | 54,082.9 | Mann-Whitney U | 0.9929 | Cliff's δ=-0.000 | No |
| p99 latencia (ms) | 82,581.9 | 57,364.3 | Mann-Whitney U | 0.2599 | Cliff's δ=0.028 | No |
| Throughput (req/s) | 2.8 | 4.2 | Mann-Whitney U | 0.3933 | Cliff's δ=0.021 | No |

**Interpretación**: la arquitectura propuesta tiene latencia mediana significativamente mejor (efecto medio-grande). Consistente con el diseño: el monolito serializa auth+ffmpeg+Whisper en un único worker; la propuesta solo serializa Whisper (auth y conversión de audio corren en servicios de 4 workers).

Ver también la sección E6 para el aislamiento de fallos (la otra mitad de la comparación E3).

---

## E4 — Escalabilidad bajo carga (Azure Container Apps)

Cuatro rondas de la misma rampa de carga contra el despliegue productivo, incrementando progresivamente el autoescalado horizontal.

### Bug de medición encontrado y corregido

`report.py` calculaba el error rate por escalón usando `Failures/s`/`Requests/s` — la tasa **instantánea** de la última muestra dentro de la ventana de 180s — no un conteo acumulado. Un burst de errores a mitad de ventana podía reportarse como 0% si no caía justo en el segundo final muestreado. Se corrigió para usar `Total Request Count`/`Total Failure Count` (diferencia entre el fin de un escalón y el anterior). Los 5 reportes afectados fueron regenerados.

### Resultados (corregidos) — escalón final de cada ronda

| Ronda | Configuración | Usuarios sostenidos | Error rate (escalón final) | p99 |
|---|---|---|---|---|
| 1 | Sin autoscaling | 254 | 96.9-100% | ~68-81s |
| 2 | + autoscale `asr-service` (1-3 réplicas, `concurrentRequests=2`) | 307 | 85.6% | ~81s |
| 3 | + modelo horneado en la imagen Docker | 244 | 97.1-100% | ~67s |
| 4 | + autoscale `auth-service` también (1-3 réplicas, `concurrentRequests=10`) | **353** | 85.9-100% | **149s** |

### Hallazgo: `auth-service` como cuello de botella real

La ronda 3 (modelo horneado, sin tocar `auth-service`) salió **peor** que la ronda 2, no mejor — esto llevó a investigar la causa en el código: `api-gateway` valida el JWT contra `auth-service` (`POST /internal/auth/validate-token`) en **cada** solicitud autenticada, no solo en login. Cualquier respuesta que no sea `200+valid:true` —incluyendo un 5xx de `auth-service` sobrecargado— se traduce en un 401 para el cliente, enmascarando la causa real. La ronda 3 tuvo 2652 errores 401 en `/transcribe`; autoescalar `auth-service` (ronda 4) los redujo a 235 (-91%).

### Conclusión honesta

Ninguna de las 4 configuraciones mantiene el error rate por debajo de ~85% en el escalón de carga más extremo (500-1000 usuarios objetivo). La mejora real y consistente entre rondas es el **número de usuarios concurrentes sostenidos antes del colapso** (254→307→353), no la eliminación del colapso en sí. El mecanismo de adaptación vertical (`device_manager.py`) nunca reaccionó durante estas pruebas — su señal (CPU%) no detecta el encolamiento por concurrencia de requests contra un único worker.

**Limitación**: cada configuración se corrió una sola vez (no hay repeticiones ni intervalo de confianza para E4, a diferencia de E2/E3/E5) — costo de créditos de Azure for Students. Las comparaciones deben leerse como tendencia observada, no diferencia estadísticamente confirmada.

---

## E5 — Streaming: PCM crudo vs. Opus comprimido

Muestra estratificada de 30 clips (20 Huqariq + 10 Siminchik, proporcional a sus tamaños), 3 repeticiones por condición (n=90 por condición), transmitidos por WebSocket.

| Condición | n | WER (media±IC95%) | CER (media±IC95%) | Latencia s (media±IC95%) | Bytes enviados (media) |
|---|---|---|---|---|---|
| PCM | 90 | 0.735±[0.668,0.801] | 0.261±[0.206,0.316] | 11.56±[10.20,12.91] | 582,785 |
| Opus | 90 | 0.736±[0.660,0.812] | 0.271±[0.206,0.335] | 5.34±[4.73,5.95] | 165,071 |

| Métrica | Test | p-value | Effect size | ¿Significativo? |
|---|---|---|---|---|
| WER | Mann-Whitney U | 0.6716 | Cliff's δ=0.037 | No |
| CER | Mann-Whitney U | 0.9703 | Cliff's δ=0.003 | No |
| Latencia | Mann-Whitney U | 0.0000 | Cliff's δ=0.523 | **Sí** |

**Hallazgo importante — contradice la hipótesis de diseño original**: no hay diferencia significativa de WER/CER entre PCM y Opus. Opus sí es significativamente más rápido (54% menos latencia) y usa 72% menos bytes.

**Bug de producción encontrado y corregido**: `services/asr-service/app/services/codec_service.py` no especificaba `-ar 16000` en el decode de ffmpeg — Opus codifica a 48kHz internamente, y sin resamplear de vuelta a 16kHz, Whisper necesita `torchaudio` (no instalado) para hacerlo en tiempo de inferencia. Esto rompía el streaming comprimido por completo (fallaba silenciosamente, el cliente quedaba colgado 300s sin respuesta). Ya corregido (una línea: agregar `-ar 16000`).

**Caveat metodológico**: el experimento codificó cada clip completo a Opus de una sola vez (vía ffmpeg) antes de trocearlo para la transmisión — no reproduce el patrón de codificación incremental específico de `MediaRecorder` del navegador (que trocea en límites que no coinciden con los frames de Opus, y es la razón original por la que se deshabilitó). El resultado no valida usar `MediaRecorder` tal cual, solo indica que la compresión Opus bien formada no degrada WER/CER por sí sola.

---

## E6 — Aislamiento de fallos (fault injection)

Con ~50 usuarios concurrentes reales ejecutando login+transcribe, se detuvo cada contenedor crítico (`docker stop`, 30s de caldeo) y se midió el impacto real en `/api/v1/transcribe` durante la caída.

| Servicio caído | Requests totales | Fallas | % fallas | Comportamiento |
|---|---|---|---|---|
| `asr-service` | 437 | 0 | **0.0%** | las requests en curso se encolan (hasta 81s de latencia) y se completan cuando el contenedor vuelve — sin pérdida |
| `auth-service` | 539 | 352 | **65.3%** | está en el critical path de toda solicitud autenticada, no solo login |
| `transcription-manager` | 238 | 0 | **0.0%** | diseño "non-fatal on failure" — el cliente recibe su transcripción igual, solo se pierde la persistencia |
| **Monolito** (todo el proceso) | 1160 | 1082 | **93.3%** | un solo proceso — cualquier componente interno que falle tumba todo, incluido el 12% de los logins |

| Servicio detenido | Detección | Recuperación | Propagó a servicios vecinos |
|---|---|---|---|
| `asr-service` | 3.4s | no auto-recupera (`docker stop` limpio, restart policy `on-failure` no aplica) | No |
| `auth-service` | 3.5s | no auto-recupera | No |
| `transcription-manager` | 3.5s | no auto-recupera | No |
| Monolito | 3.7s | no auto-recupera | N/A (todo es el mismo proceso) |

**Interpretación**: la separación de responsabilidades aísla el impacto real de una caída entre 0% y 65.3% del tráfico según el servicio, nunca el sistema completo — frente al 93.3% del monolito sin excepción. Esta es la evidencia cuantitativa más limpia del proyecto a favor del principio arquitectónico central.

---

## Resumen ejecutivo — qué está fuerte y qué hay que matizar

**Evidencia fuerte** (E3 + E6): separación de responsabilidades → latencia significativamente mejor + aislamiento de fallos dramático (0-65% vs. 93.3%).

**Evidencia parcial/débil** (E4): autoscaling horizontal ayuda (254→307→353 usuarios sostenidos) pero no resuelve la escalabilidad — todas las configuraciones colapsan a carga extrema (>85% error).

**Hallazgo que contradice el diseño original** (E5): PCM crudo no muestra mejor WER/CER que Opus comprimido — la restricción actual se sostiene como precaución de ingeniería (caso MediaRecorder no probado), no como mejora de precisión demostrada.

**Gap no resuelto**: RQ1 (conmutación CPU/GPU) no pudo medirse — sin hardware GPU disponible en esta ronda experimental.

**Rigor del proceso**: se encontraron y corrigieron 2 bugs reales durante la ejecución de los experimentos (el cálculo de error rate en `report.py`, y la falta de `-ar 16000` en `codec_service.py`) — documentados explícitamente como parte de Threats to Validity en vez de ocultados.
