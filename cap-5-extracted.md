5. # **VALIDACIÓN Y RESULTADOS DEL PROYECTO**

Una vez diseñada e implementada la plataforma web basada en servicios de reconocimiento automático de voz en quechua, corresponde a este capítulo desarrollar la validación de la plataforma web basada en servicios de reconocimiento automático de voz (ASR) para el quechua y responder de manera principal al cuarto objetivo específico del trabajo (OE4). A través de este objetivo se busca aportar evidencia empírica a la formulación del problema, es decir, a la pregunta de cómo una plataforma web con servicios ASR puede mejorar la accesibilidad e interacción en quechua dentro de aplicaciones digitales.  
La validación se plantea bajo el enfoque de la investigación en ciencia del diseño (Design Science Research), en el cual la contribución principal es un artefacto construido para resolver un problema relevante, y su validación consiste en evaluar de forma rigurosa los atributos de calidad de dicho artefacto en relación con el propósito para el que fue creado (Hevner et al., 2004). Dentro de la metodología propuesta por Peffers et al. (2007), este capítulo corresponde a las actividades de demostración y evaluación. En coherencia con este enfoque, se distinguen dos niveles de evaluación la verificación, que comprueba que el artefacto opera de extremo a extremo tal como fue construido, y la validación, que determina si el artefacto cumple con los atributos de calidad que el objetivo exige.  
La investigación relaciona dos variables. La variable independiente es la plataforma web basada en servicios ASR en quechua, entendida como el artefacto que se construye en específico una arquitectura de microservicios desplegada en la nube con escalado adaptativo, que contiene un modelo ASR preentrenado y contenerizado, una API REST y WebSocket, y una interfaz web. La variable dependiente es la accesibilidad e interacción en quechua en entornos digitales. En consecuencia, un servicio que se encuentre disponible, que soporte demanda concurrente, que responda con rapidez, que reconozca el habla con calidad aceptable y que resulte utilizable constituye la condición técnica necesaria para que dicho acceso exista, más aún considerando que el reconocimiento de voz se ha consolidado como un componente central de las herramientas digitales de interacción y aprendizaje de lenguas (Farrús, 2023). Por ello, la variable dependiente se desarrolla en dos dimensiones la accesibilidad, que agrupa los indicadores de disponibilidad y escalabilidad, y la interacción, que agrupa los indicadores de rendimiento, calidad de reconocimiento y usabilidad.  
Dado que no existe una condición previa contra el cual contrastar la intervención del artefacto, la relación entre la variable independiente y la variable dependiente se sustenta mediante la evaluación del artefacto frente a criterios de aceptación definidos y frente al estado del arte, en lugar de mediante un grupo de control tradicional (Easterbrook et al., 2008). Las comparaciones controladas se plantean sobre factores internos de la propia plataforma, como el estilo arquitectónico, la configuración de escalado y la codificación del audio en streaming, lo que permite atribuir las diferencias observadas a decisiones de diseño específicas.

1. ## **PROTOCOLO EXPERIMENTAL**

El protocolo experimental define qué se mide, cómo se mide, con qué instrumentos, en qué entornos y bajo qué criterios se considera satisfactorio cada resultado. Siguiendo las recomendaciones de la experimentación en software, los indicadores y sus criterios de aceptación se establecen como parte de la planificación (Wohlin et al., 2012). Para obtener la evidencia de cada indicador se definen seis técnicas de evaluación la caracterización del corpus, la evaluación de reconocimiento sobre el corpus, la prueba de carga comparativa frente a una línea base, la prueba de carga progresiva en la nube, la prueba comparativa de codificación en streaming y la prueba de inyección de fallos, a las que se suma la evaluación de usabilidad.

1. ### **Enfoque de validación y trazabilidad con el objetivo**

Para definir qué atributos evaluar se adopta como marco de referencia el modelo de calidad de producto ISO/IEC 25010 (ISO/IEC, 2023), que organiza la calidad del software en características y subcaracterísticas medibles. En lugar de aplicar el modelo de forma exhaustiva, se utiliza para dar respaldo normativo a cada indicador que el OE4 establece, de modo que cada dimensión de la variable dependiente queda asociada con una característica reconocida del modelo. De forma complementaria, el proceso de pruebas se alinea con los conceptos de la norma ISO/IEC/IEEE 29119 (ISO/IEC/IEEE, 2022), en particular con la distinción entre niveles de prueba de integración y de sistema.

Tabla X.

| Indicador del OE4 | Característica ISO/IEC 25010 | Pregunta de evaluación |
| ----- | ----- | ----- |
| Disponibilidad | Fiabilidad (disponibilidad, tolerancia a fallos) | ¿Qué proporción del servicio se mantiene operativa ante la caída de un componente y bajo carga? |
| Escalabilidad | Eficiencia de desempeño (capacidad) y Flexibilidad (escalabilidad) | ¿Cuánta carga concurrente sostiene la plataforma en la nube y cómo se adapta a ella? |
| Latencia y tiempo de respuesta | Eficiencia de desempeño (comportamiento temporal) | ¿Qué tiempos entrega la plataforma en carga de archivos y en streaming? |
| Calidad de reconocimiento | Adecuación funcional (corrección funcional) | ¿Con qué precisión transcribe la plataforma el habla en quechua? |
| Usabilidad | Capacidad de interacción | ¿Pueden los usuarios utilizar la plataforma con eficacia, eficiencia y satisfacción? |

La calidad de reconocimiento se incorpora como indicador porque un servicio disponible y rápido que no reconoce correctamente el habla no proporciona acceso real a la lengua. La literatura sobre lenguas de bajos recursos identifica precisamente la calidad del reconocimiento como la principal barrera para que estas tecnologías alcancen un uso práctico (Abdulmumin et al., 2025), y señala que los sistemas globales presentan tasas de error significativamente más altas en quechua (Akhulkova, 2025). Por esta razón, consideramos, la tasa de error por palabra (WER) y por carácter (CER) como métricas adicionales, a razón de evidenciar que el modelo preentrenado incluido en nuestra arquitectura su capacidad de reconocimiento de voz.

2. ### **Variables, dimensiones e indicadores**

Variable independiente. La variable independiente es la plataforma web basada en servicios ASR en quechua. Está compuesta por seis microservicios desarrollados en Python 3.11 con FastAPI (api-gateway, auth-service, user-service, audio-processor, asr-service y transcription-manager), un modelo ASR preentrenado y contenerizado, una API REST y WebSocket documentada mediante OpenAPI, una interfaz web en Angular, un despliegue en la nube con escalado horizontal por concurrencia y un mecanismo de adaptación de recursos en tiempo de ejecución. Como se indicó, la plataforma no se manipula como un todo, sino a través de factores internos cuyos niveles se comparan de forma controlada, tal como se muestra en la Tabla X.

Tabla X. Factores de la variable independiente considerados en el diseño.

| Factor | Niveles |
| ----- | ----- |
| Estilo arquitectónico | Microservicios y monolito |
| Configuración de escalado | Configuración fija sin autoescalado y configuraciones progresivas de autoescalado definidas de forma iterativa |
| Codificación del audio en streaming | PCM sin comprimir y Opus comprimido |

Variable dependiente. La variable dependiente es la accesibilidad e interacción en quechua en entornos digitales. En este trabajo, la accesibilidad se entiende como la disponibilidad técnica de un servicio de reconocimiento de voz en quechua para ser consumido por usuarios y aplicaciones. La interacción se entiende como la posibilidad de que dicho servicio sea utilizado por voz de manera útil, oportuna y satisfactoria. La Tabla X presenta la operacionalización completa de esta variable.

| Dimensión | Indicador | Definición operacional |
| :---- | :---- | :---- |
| Accesibilidad | Tasa de éxito ante fallos | Proporción de solicitudes de transcripción completadas con éxito durante la caída inducida de un servicio |
| Accesibilidad | Tasa de éxito bajo carga | Complemento de la tasa de error acumulada en cada escalón de carga |
| Accesibilidad | Tiempo de detección de fallos | Tiempo transcurrido entre la detención de un servicio y su detección mediante el endpoint de salud |
| Accesibilidad | Propagación de fallos | Presencia o ausencia de degradación en servicios vecinos al servicio detenido |
| Accesibilidad | Usuarios concurrentes sostenidos | Número máximo de usuarios concurrentes alcanzado en el último escalón de carga sostenido |
| Accesibilidad | Throughput | Solicitudes procesadas por segundo |
| Interacción | Tiempo de respuesta | Percentiles 50, 95 y 99 del tiempo de extremo a extremo de una solicitud REST de transcripción |
| Interacción | Latencia de streaming | Tiempo hasta la recepción del resultado final de una sesión de transcripción por WebSocket |
| Interacción | Factor de tiempo real (RTF) | Cociente entre el tiempo de procesamiento y la duración del audio |
| Interacción | Tasa de error por palabra (WER) | Proporción de sustituciones, eliminaciones e inserciones respecto del número de palabras de la referencia |
| Interacción | Tasa de error por carácter (CER) | Cálculo equivalente al WER aplicado a caracteres |
| Interacción | Satisfacción de uso | Puntaje de la escala SUS |
| Interacción | Tasa de éxito de tareas | Proporción de tareas completadas sin asistencia |

Algunos indicadores requieren precisiones adicionales. En primer lugar, el OE4 menciona la latencia y el tiempo de respuesta como indicadores distintos, por lo que se diferencian de la siguiente manera el tiempo de respuesta corresponde a la duración completa de una solicitud REST de transcripción observada por el cliente, mientras que la latencia se refiere al retardo del resultado en la modalidad de streaming y se complementa con el RTF, que expresa el costo de la inferencia en relación con la duración del audio. Un RTF menor que 1 indica que el sistema transcribe más rápido que el tiempo real.  
   
En segundo lugar, el tiempo de respuesta se reporta mediante percentiles y no únicamente mediante promedios, porque en sistemas distribuidos los tiempos de la cola de la distribución (percentiles 95 y 99\) determinan la experiencia de una fracción relevante de usuarios y tienden a crecer a medida que aumenta el número de componentes que intervienen en una solicitud (Dean & Barroso, 2013).  
   
Finalmente, la usabilidad se operacionaliza según la definición de la norma ISO 9241-11, que la entiende como el grado en que un producto puede ser utilizado por usuarios específicos para alcanzar objetivos con eficacia, eficiencia y satisfacción en un contexto de uso determinado (ISO, 2018). En consecuencia, la tasa de éxito de tareas mide la eficacia, el tiempo por tarea mide la eficiencia y la escala SUS mide la satisfacción.

3. ### **Objeto de evaluación, entornos y línea base**

El artefacto evaluado es la plataforma completa descrita en la variable independiente. El núcleo de reconocimiento reside en asr-service, que ejecuta el modelo QuechuaBase/whisper-base-qxp-finetuned, una variante de Whisper (Radford et al., 2023\) ajustada para quechua, tanto en modalidad de carga de archivos como en modalidad de streaming mediante WebSocket. En la modalidad de streaming, la plataforma admite audio PCM sin comprimir y audio comprimido en formato Opus o MP3; en el caso del audio comprimido, el servicio acumula los fragmentos recibidos y los decodifica a WAV de 16 kHz antes de la inferencia, por lo que las transcripciones parciales en tiempo real solo están disponibles para PCM, mientras que el audio comprimido produce únicamente el resultado final.

La validación se realizó en dos iteraciones de construcción y evaluación, coherentes con el ciclo de la ciencia del diseño (Hevner et al., 2004). La primera iteración evaluó la arquitectura inicial y permitió identificar sus limitaciones: la cadena de servicios era síncrona y no tenía control de admisión, la validación de cada token dependía de auth-service y el mecanismo de adaptación decidía según el porcentaje de uso de CPU. A partir de esos hallazgos se construyó una segunda versión de la arquitectura, que es la que se valida en este capítulo e incorpora los siguientes cambios:

* **Disponibilidad.** api-gateway valida los tokens de forma local (firma JWT y un registro de revocaciones replicado en Redis), por lo que auth-service deja de estar en el camino crítico de cada solicitud; los errores de un servicio dependiente se informan como 503 con la cabecera Retry-After, en lugar de enmascararse como 401; los servicios separan el endpoint de vida (`/health`) del de disponibilidad para recibir tráfico (`/ready`), y se reinician automáticamente ante una terminación inesperada.
* **Escalabilidad.** Se incorpora una API asíncrona (`/api/v1/jobs`) sobre una cola de Redis Streams con entrega al menos una vez, de modo que una solicitud aceptada no se pierde aunque el proceso de inferencia falle. Se añade un control de admisión en dos niveles: en el borde, api-gateway limita las transcripciones síncronas en curso y rechaza el exceso con 503 antes de procesar el archivo; en asr-service, el planificador de inferencia rechaza las solicitudes cuya espera estimada supera el límite.
* **Rendimiento.** asr-service incorpora un planificador de inferencia con prioridades (resultado final de streaming, solicitud REST, trabajo asíncrono y resultado parcial) y varias líneas de inferencia en paralelo, y ejecuta el mismo modelo con el motor CTranslate2, que ofrece cuantización int8 eficiente en CPU. La persistencia de la transcripción se realiza fuera del camino de respuesta.
* **Adaptación.** El mecanismo de adaptación vertical decide según la profundidad de la cola de inferencia, la señal en que se manifiesta la saturación, y no según el porcentaje de uso de CPU. Cada cambio de precisión pasa por un periodo de prueba: el mecanismo mide el costo real por clip en el nuevo estado y revierte el cambio si no resulta más rápido, de modo que una adaptación perjudicial no permanece activa.

Cada transcripción registra el dispositivo y la precisión con que fue procesada, y los mecanismos de adaptación y de planificación exponen endpoints de estado con su historial de decisiones y sus contadores, lo que permite observar su comportamiento durante la evaluación.

Antes de ejecutar las mediciones se verifica que el artefacto opere de extremo a extremo en condiciones reales. Siguiendo la distinción entre niveles de prueba de la norma ISO/IEC/IEEE 29119, la verificación comprende pruebas de integración contra la pila completa en ejecución y pruebas de sistema de los flujos principales. El objetivo de esta etapa no es validar atributos de calidad, sino asegurar que los atributos medidos posteriormente correspondan a un artefacto que funciona según su diseño.

Respecto a la línea base monolítica, que sirve para aislar el efecto de la decisión arquitectónica, se construye una versión monolítica de control que reúne en un único proceso la lógica de autenticación, registro, procesamiento de audio, inferencia y persistencia, reutilizando el mismo código funcional de los servicios originales. En esta versión, las llamadas HTTP que la arquitectura propuesta realiza entre audio-processor, asr-service y transcription-manager se reemplazan por llamadas directas a funciones dentro del mismo proceso. El monolito expone las mismas rutas públicas que la plataforma, utiliza un dispositivo de ejecución fijo sin mecanismo de adaptación, dispone de una base de datos propia y, para que la comparación aísle el estilo arquitectónico y no el motor de inferencia, ejecuta el mismo modelo con el mismo motor, la misma precisión y el mismo número de líneas de inferencia que la arquitectura propuesta.

La evaluación se realiza en dos entornos de ejecución. El primero es un entorno local basado en Docker Compose, en el que se despliegan todos los contenedores de la plataforma y de la línea base sobre el mismo hardware: un procesador Intel Core i5-10400 de 6 núcleos y 12 hilos a 2.9 GHz, con 23.8 GB de RAM, de los cuales se asignan 12 CPU lógicas y 16 GB al entorno de contenedores, sin GPU dedicada. El segundo es Azure Container Apps en el plan de consumo, sin disponibilidad de GPU, con réplicas de asr-service de 2 vCPU y un servidor PostgreSQL flexible de tipo Standard\_B1ms compartido por las bases de datos de los servicios. Esta combinación responde al marco de evaluación propuesto por Venable et al. (2016), que distingue entre evaluaciones artificiales, en las que el investigador controla las condiciones, y evaluaciones cercanas al uso real del artefacto. La primera iteración evaluó la escalabilidad horizontal en Azure; la segunda iteración, cuyas comparaciones requieren condiciones idénticas entre configuraciones y entre arquitecturas, se evaluó en el entorno local.

Algunos criterios de la segunda iteración no pueden evaluarse sin aceleración por hardware. Por ello se incorporó un tercer entorno: un equipo con GPU dedicada, en el que se desplegaron con Docker Compose los mismos contenedores de la plataforma y de la línea base, con acceso de los servicios de inferencia a la GPU. Una GPU (unidad de procesamiento gráfico) es un procesador diseñado para ejecutar en paralelo una gran cantidad de operaciones matemáticas simples, que es justamente el tipo de cálculo que realiza un modelo de reconocimiento de voz basado en redes neuronales. Por ello, una GPU puede ejecutar la inferencia (el proceso de obtener la transcripción a partir del audio con el modelo ya entrenado) mucho más rápido que la CPU (unidad central de procesamiento), que es el procesador de propósito general del equipo. Los servicios acceden a la GPU mediante CUDA, la plataforma de programación que permite a las librerías de aprendizaje profundo ejecutar cálculos en ella. En este entorno se evaluaron los criterios que dependen de la aceleración y se repitieron, con GPU, las pruebas de escalabilidad, de adaptación y de rendimiento de la segunda iteración. Como se trata de un equipo distinto del entorno local sin GPU, las comparaciones que exigen el mismo hardware, como la del criterio C3.4, se realizaron íntegramente dentro de este equipo.

4. ### **Corpus de evaluación**

Las mediciones basadas en audio requieren un corpus con transcripciones de referencia. Para su selección se aplican tres criterios disponibilidad pública, existencia de transcripciones de referencia en quechua y ausencia de solapamiento con los datos de ajuste fino del modelo evaluado. Este último criterio lleva a descartar deliberadamente los conjuntos QuechuaBase/asr-puno-quechua y la variante de quechua de Mozilla Common Voice, cuyo probable solapamiento con los datos de entrenamiento del modelo produciría una contaminación entre entrenamiento y prueba, con resultados artificialmente favorables.

El corpus seleccionado integra dos fuentes Huqariq (Zevallos et al., 2022\) y Siminchik (Cardenas et al., 2018). Sus características se presentan en la Tabla X.

Tabla X. Caracterización del corpus de evaluación.

| Atributo | Valor |
| ----- | ----- |
| Número de clips | 2111 |
| Duración total | 10:47:32 (10.79 h) |
| Duración por clip | mín. 0.59 s, máx. 34.16 s, media 18.40 s, mediana 23.04 s |
| Hablantes identificados | 47 |
| Clips por fuente | Huqariq: 1413 (67 %); Siminchik: 698 (33 %) |
| Variante dialectal declarada	 | Quechua sureño (solo Siminchik) |
| Condición de grabación declarada | Radio (solo Siminchik) |

Nota: Características documentadas de los audios

Cada clip se registra en un manifiesto con la ruta del audio, la transcripción de referencia y los metadatos disponibles. Una limitación relevante es que Huqariq, que representa el 67 % del corpus, no reporta variante dialectal, condición de grabación, sexo ni edad del hablante. Antes del cálculo de WER y CER, tanto las referencias como las hipótesis se normalizan para eliminar diferencias de formato que no constituyen errores de reconocimiento. El grado en que dicha normalización debe considerar particularidades ortográficas del quechua constituye una decisión metodológica que influye en los valores obtenidos, tal como se ha documentado en la evaluación de modelos de la familia Whisper (Radford et al., 2023).

5. ### **Diseño de la evaluación por dimensión**

Los diseños se presentan en el orden de las dimensiones de la variable dependiente: primero los indicadores de accesibilidad (disponibilidad y escalabilidad) y luego los de interacción (rendimiento, calidad de reconocimiento y usabilidad). En las pruebas de carga se utiliza como audio un clip real del corpus de 24.05 s, cercano a la mediana de duración del corpus (23.04 s), y cada respuesta se valida por su contenido: una respuesta con código 200 que no contiene una transcripción se cuenta como fallo.

1. #### **Disponibilidad**

La disponibilidad se evalúa principalmente mediante la prueba de inyección de fallos, que consiste en provocar fallos de forma deliberada mientras el sistema atiende carga realista para observar su comportamiento, en lugar de suponer su resiliencia a partir del diseño (Basiri et al., 2016).

Mientras un grupo de usuarios ejecuta de forma continua el flujo de inicio de sesión y transcripción, y tras un periodo de calentamiento de 60 segundos, se provoca la caída de un componente terminando su proceso principal con la señal SIGKILL, lo que reproduce una terminación inesperada y activa la política de reinicio automático. La carga se fija en 10 usuarios concurrentes, que corresponden a la capacidad de la plataforma en el hardware de evaluación según la ley de Little (apartado de escalabilidad), de modo que la prueba mida la respuesta ante el fallo y no la saturación. Se evalúan ocho escenarios, cada uno con tres repeticiones:

Tabla X. Escenarios de inyección de fallos.

| Código | Componente | Pregunta de evaluación |
| ----- | ----- | ----- |
| D1 | asr-service | ¿Se recupera solo y en cuánto tiempo? ¿Cómo fallan las solicitudes durante el corte? |
| D2 | auth-service (validación local) | ¿Deja auth-service de ser un punto único de fallo? |
| D2b | auth-service (validación remota, como en la primera iteración) | Contraste para aislar el efecto de la validación local |
| D3 | transcription-manager | ¿Sigue siendo la persistencia un componente no crítico? |
| D4 | asr-service con carga asíncrona | ¿Se pierde algún trabajo aceptado? |
| D5 | Redis | ¿Sobreviven la ruta síncrona y la autenticación a la caída de la cola? |
| D6 | asr-service congelado durante 60 s | ¿Se aísla un proceso vivo pero sin respuesta? |
| D7 | Monolito completo | Línea base |

Durante cada prueba se registran todas las solicitudes con su instante de finalización, lo que permite calcular la tasa de éxito antes, durante y después del corte; se consulta el endpoint de salud de cada servicio cada segundo para medir el tiempo de detección y el tiempo de recuperación (MTTR), y se observa si la caída degrada a los servicios vecinos.

De forma complementaria, la tasa de éxito bajo carga se obtiene de la prueba de carga progresiva, cuyo diseño se describe en el apartado siguiente.

2. #### **Escalabilidad**

La escalabilidad se evalúa mediante la prueba de carga progresiva, aplicada con Locust en una rampa de seis escalones de 180 segundos cada uno, con objetivos de 10, 50, 100, 200, 500 y 1000 usuarios concurrentes, en los que cada usuario simulado ejecuta de forma repetida el flujo de inicio de sesión y transcripción con un tiempo de espera de 1 a 3 s entre solicitudes.

La prueba se diseña de forma iterativa, coherente con los ciclos de construcción y evaluación propios de la ciencia del diseño (Hevner et al., 2004). En la primera iteración se ejecutó en Azure Container Apps con cuatro configuraciones de escalado horizontal, cada una definida a partir del análisis de la anterior. En la segunda iteración se ejecuta en el entorno local, con tres repeticiones por configuración, comparando configuraciones que difieren en un solo factor:

Tabla X. Configuraciones de la prueba de carga de la segunda iteración.

| Corrida | Configuración | Propósito |
| ----- | ----- | ----- |
| S1 | Réplica de la primera iteración: motor transformers en fp32, validación remota del token y sin control de admisión | Referencia |
| S2 | Arquitectura v2 sin admisión en el borde | Efecto de los cambios de software sin hardware nuevo |
| S2c | Arquitectura v2 completa, con admisión en el borde | Efecto del control de admisión en el borde |
| S2b | Arquitectura v2 completa con la API asíncrona | Efecto del modelo asíncrono |
| S3 | Arquitectura v2 con GPU, sin admisión en el borde | Capacidad con aceleración y calibración del límite de admisión |
| S3c | Arquitectura v2 completa con GPU, con admisión en el borde | Efecto del control de admisión en el borde con GPU |
| S4 | Arquitectura v2 completa con GPU y la API asíncrona | Efecto del modelo asíncrono con GPU |

Las corridas S1, S2, S2c y S2b se ejecutaron en el entorno local sin GPU, y las corridas S3, S3c y S4 en el equipo con GPU, también con tres repeticiones cada una. El control de admisión en el borde necesita un valor: el número máximo de transcripciones síncronas que api-gateway deja en curso al mismo tiempo. Si ese límite es demasiado bajo, se rechazan solicitudes que el sistema podría atender; si es demasiado alto, las solicitudes se acumulan y esperan demasiado. Por ello, el límite no se fijó de antemano, sino que se calculó a partir de la corrida sin admisión en el borde del mismo hardware (S2 en CPU y S3 en GPU), con la ley de Little que se describe a continuación: el límite es el producto del goodput máximo observado por el tiempo de respuesta en ese mismo escalón, es decir, el número de solicitudes que el sistema mantiene en curso cuando trabaja a su máxima capacidad.

Para cada escalón se registran la tasa de éxito, el goodput (solicitudes completadas con éxito por segundo), los percentiles 50 y 95 del tiempo de respuesta de las solicitudes exitosas y el desglose de los fallos en rechazos rápidos (503), timeouts y errores 5xx. Esta distinción es necesaria porque un sistema puede fallar de dos maneras muy distintas: rechazando de inmediato lo que no puede atender, lo que permite al cliente reintentar, o aceptando la solicitud y fallando después de una espera prolongada. Se calcula además el techo analítico de usuarios concurrentes mediante la ley de Little, N = X · (R + Z), donde X es el throughput máximo, R el tiempo de respuesta objetivo (10 s) y Z el tiempo de espera entre solicitudes (2 s en promedio), lo que permite determinar si un objetivo de usuarios es alcanzable con un hardware dado.

En la corrida asíncrona, cada usuario envía un trabajo y consulta su estado hasta que termina. Al final de la rampa se espera a que la cola se vacíe y se comparan los trabajos aceptados con los procesados por el worker.

Durante las corridas se observa además el mecanismo de adaptación vertical mediante su endpoint de estado. Su comportamiento se evalúa de forma aislada con una prueba específica: tras 30 s de reposo se aplica una ráfaga de 24 clientes concurrentes durante 120 s, seguida de 90 s de reposo, y se registran las decisiones del mecanismo, su tiempo de reacción, el resultado del periodo de prueba y el throughput antes y después de la primera decisión, con tres repeticiones con cada motor de inferencia.

En el equipo con GPU, la misma prueba se aplicó a tres escenarios, también con tres repeticiones cada uno. En el escenario A, el servicio arranca en la GPU y puede cambiar su precisión y el tamaño de sus lotes. En el escenario B, el servicio queda restringido a la CPU, como contraste. En el escenario C, el servicio arranca en la CPU con la GPU disponible, para observar si el mecanismo traslada la inferencia de un dispositivo a otro sin reiniciar el servicio, es decir, en caliente.

3. #### **Rendimiento**

El rendimiento se evalúa con cuatro fuentes de evidencia complementarias:

* **Costo de inferencia**. En la evaluación de reconocimiento sobre el corpus se mide el RTF de cada uno de los 2111 clips, ejecutados en CPU con precisión fp32. La misma evaluación se repite en el equipo con GPU, con la configuración por defecto de la arquitectura v2.
* **Throughput de inferencia por configuración**. Directamente contra asr-service, sin pasar por el gateway, se mide el throughput (segundos de audio procesados por segundo) y la latencia con 1, 2, 4, 8 y 16 clientes concurrentes, para cada combinación de motor (transformers y CTranslate2), precisión (fp32 e int8) y número de líneas de inferencia, usando la muestra estratificada de 30 clips. La salida de cada configuración se compara con la de referencia mediante WER como control, para verificar que una optimización no altera el reconocimiento. En el equipo con GPU, la misma medición se extiende hasta 32 clientes concurrentes y compara la CPU en fp32 e int8 con la GPU en fp32 y en fp16, y en este último caso con lotes de 1, 4, 8 y 16 clips. La precisión fp16 representa cada número del modelo con 16 bits en lugar de 32, lo que reduce a la mitad la memoria y acelera el cálculo en la GPU, a cambio de una pérdida mínima de exactitud numérica. El procesamiento por lotes (*batching*) consiste en agrupar varias solicitudes que llegan casi al mismo tiempo y procesarlas en una sola pasada del modelo, lo que aprovecha mejor el paralelismo de la GPU. Como referencia adicional, se mide en el mismo equipo la mejor configuración de CPU (CTranslate2 int8 con tres líneas), para comparar la GPU no solo con la CPU sin optimizar, sino también con la CPU optimizada.
* **Tiempo de respuesta bajo carga**. En la prueba de carga comparativa se aplica la misma rampa contra la arquitectura propuesta y contra la línea base monolítica, en el entorno local, sobre el mismo hardware y con el mismo motor de inferencia, con tres repeticiones por arquitectura, y se comparan los percentiles 50, 95 y 99 del tiempo de respuesta y el throughput. La comparación se repite en el equipo con GPU, con ambas arquitecturas ejecutando la inferencia en la GPU con precisión fp32 fija, ya que el monolito no tiene mecanismo de adaptación.
* **Latencia de streaming**. En la prueba comparativa de codificación se transmite por WebSocket una muestra estratificada de 30 clips, específicamente 20 de Huqariq y 10 de Siminchik, en proporción al tamaño de cada fuente. Cada clip se envía una vez como audio PCM sin comprimir y otra como audio comprimido en Opus, y se registran la latencia hasta el resultado final y el volumen de bytes transmitidos. Para la condición Opus, cada clip se codifica completo con ffmpeg y luego se fragmenta para su transmisión.

  4. #### **Calidad de reconocimiento**

La calidad de reconocimiento se evalúa sobre la totalidad del corpus. Para cada clip se obtiene la transcripción de la plataforma y se calculan WER y CER respecto de la referencia, tras la normalización descrita anteriormente. Los resultados se desagregan por fuente del corpus y se identifican dos tipos de anomalías las transcripciones vacías y los clips con WER superior a 1.5, indicativos de inserciones excesivas o alucinaciones del modelo. Adicionalmente, la prueba comparativa de codificación en streaming aporta la comparación de WER y CER entre las condiciones PCM y Opus, con el fin de determinar si la compresión del audio afecta la calidad del reconocimiento; sus resultados de latencia se reportan en la dimensión de rendimiento.

5. #### **Usabilidad**

La usabilidad se evalúa mediante dos instrumentos dirigidos a los dos tipos de usuarios de la plataforma.  
   
El primero está dirigido a usuarios finales. Cada participante realiza un conjunto de tareas representativas en la plataforma como registrarse, iniciar sesión, cargar un archivo de audio para su transcripción, realizar una transcripción por streaming desde el micrófono, consultar el historial y descargar una transcripción. Para cada tarea se registra si se completa sin asistencia y el tiempo empleado. Al finalizar, el participante responde el cuestionario System Usability Scale (SUS), un instrumento de diez ítems con escala de cinco puntos que produce un puntaje de 0 a 100 (Brooke, 1996), y un conjunto de preguntas abiertas sobre su experiencia.  
   
El segundo está dirigido a expertos. Los expertos revisan la documentación OpenAPI, consumen la API y responden un cuestionario con escala Likert de 1 a 5 sobre la adecuación de las técnicas empleadas la arquitectura de microservicios, la API REST documentada, la transmisión por WebSocket y el escalado horizontal. El cuestionario incluye preguntas abiertas para recoger observaciones y propuestas de mejora.

6. ### **Instrumentación y tratamiento estadístico**

Las mediciones se realizan con un conjunto de herramientas desarrolladas específicamente para este fin, separado de las pruebas automatizadas de regresión del repositorio, debido a que se trata de mediciones de varios minutos contra servicios en ejecución y no de verificaciones rápidas con dependencias simuladas. Este conjunto incluye módulos compartidos para cargar y validar el manifiesto del corpus, un cliente HTTP y WebSocket capaz de operar contra ambas arquitecturas sin modificaciones, gracias a que ambas exponen las mismas rutas, la normalización de texto previa al cálculo de métricas y un módulo estadístico común que utilizan todos los reportes. Para las métricas de reconocimiento se utiliza la librería jiwer; para la generación de carga, Locust con una forma de carga programada; para el monitoreo de recursos de los contenedores, un muestreador de estadísticas de Docker; y para la inyección de fallos, un script que detiene contenedores y monitorea los endpoints de salud.  
   
El tratamiento estadístico es común a todas las evaluaciones. Para cada métrica se calcula la media con su intervalo de confianza al 95 % y la mediana con su rango intercuartil, y se evalúa la normalidad de la distribución mediante la prueba de Shapiro-Wilk. Cuando la distribución no es normal, se reporta la mediana como medida de tendencia central. Para comparar dos condiciones se aplica la prueba t de Student con el tamaño de efecto d de Cohen cuando ambas muestras son normales y, en caso contrario, la prueba U de Mann-Whitney con el tamaño de efecto delta de Cliff. El uso de pruebas no paramétricas y de tamaños de efecto no paramétricos es recomendado en ingeniería de software, donde las métricas de tiempo rara vez siguen una distribución normal (Arcuri & Briand, 2011). Se adopta un nivel de significancia de 0.05, y la magnitud del delta de Cliff se interpreta según los umbrales de Romano et al. (2006): despreciable si su valor absoluto es menor que 0.147, pequeño si es menor que 0.33, mediano si es menor que 0.474 y grande en caso contrario.

7. ### **Criterios de aceptación**

Los criterios de aceptación establecen, para cada dimensión, el umbral a partir del cual el resultado se considera satisfactorio. La Tabla X los presenta junto con su fundamento. Los criterios C1.5 a C1.7, C2.4 y C3.4 se incorporaron en la segunda iteración para evaluar las capacidades añadidas a la arquitectura. Los criterios C1.4 y C2.2 se reformularon a partir de lo observado en la primera iteración, antes de ejecutar las mediciones de la segunda. En esa iteración el número de "usuarios sostenidos" no indicaba si esos usuarios estaban siendo atendidos, y ningún sistema de una sola máquina sin GPU puede atender 1000 usuarios síncronos dentro de un tiempo de respuesta razonable, como muestra la cota de la ley de Little. Por ello se distingue entre la capacidad dentro del objetivo de servicio y el comportamiento ante la sobrecarga, que no debe ser el colapso.

Tabla X. Criterios de aceptación por dimensión.

| Código | Dimensión | Criterio | Fundamento |
| ----- | ----- | ----- | ----- |
| C1.1 | Disponibilidad | Ante la caída de un servicio individual, la tasa de éxito es superior a la del monolito en la misma condición y ninguna caída afecta al 100 % de las solicitudes | Principio de aislamiento de fallos de la arquitectura de microservicios |
| C1.2 | Disponibilidad | El tiempo de detección de una caída es menor o igual a 5 s | Intervalo de monitoreo de salud de 1 s |
| C1.3 | Disponibilidad | La caída de un servicio no se propaga a sus servicios vecinos | Principio de aislamiento de fallos |
| C1.4 | Disponibilidad | La tasa de éxito es mayor o igual a 95 % con la carga dentro de la capacidad de la plataforma | Criterio definido por el equipo |
| C1.5 | Disponibilidad | El tiempo de recuperación (MTTR) tras una terminación inesperada es menor o igual a 30 s | Recuperación automática sin intervención |
| C1.6 | Disponibilidad | Ningún trabajo asíncrono aceptado se pierde ante la caída del servicio de inferencia | Entrega al menos una vez |
| C1.7 | Disponibilidad | Con auth-service caído, la tasa de éxito de las transcripciones es mayor o igual a 95 % | Eliminación del punto único de fallo identificado en la primera iteración |
| C2.1 | Escalabilidad | La capacidad de la arquitectura propuesta supera a la de la configuración de referencia en el mismo hardware | Propósito de las mejoras de escalabilidad |
| C2.2 | Escalabilidad | Con 1000 usuarios concurrentes la plataforma no colapsa: en modo asíncrono acepta al menos el 99 % de los trabajos y completa el 100 % de los aceptados; en modo síncrono rechaza el exceso de forma rápida y explícita (503 con Retry-After), sin errores internos | Criterio definido por el equipo |
| C2.3 | Escalabilidad | El mecanismo de adaptación vertical registra al menos una decisión de cambio ante la presión de carga | Diseño del mecanismo de adaptación |
| C2.4 | Escalabilidad | Ninguna adaptación que empeore el costo de inferencia permanece activa después de su periodo de prueba | Adaptación verificada por medición |
| C3.1 | Rendimiento | El RTF mediano es menor que 1 | Transcripción más rápida que el tiempo real |
| C3.2 | Rendimiento | El tiempo de respuesta mediano en carga baja es menor o igual a 10 s | Límite de atención del usuario (Nielsen, 1993\) |
| C3.3 | Rendimiento | La arquitectura propuesta no presenta tiempos de respuesta significativamente mayores que el monolito | Comparación con la línea base |
| C3.4 | Rendimiento | La inferencia con GPU y procesamiento por lotes alcanza al menos 5 veces el throughput de la CPU en fp32, sin diferencia material de WER | Justificación del uso de aceleración |
| C4.1 | Calidad | La proporción de transcripciones vacías es 0 % | Criterio definido por el equipo |
| C4.2 | Calidad | La proporción de clips con WER superior a 1.5 es menor o igual a 1 % | Criterio definido por el equipo |
| C4.3 | Calidad | La compresión del audio en streaming no degrada significativamente WER ni CER | Hipótesis de diseño de la modalidad de streaming |
| C4.4 | Calidad | El WER se encuentra en un rango comparable al reportado en el estado del arte para quechua | \[Completar con el valor de referencia del Capítulo 2\] |
| C5.1 | Usabilidad | El puntaje SUS promedio es mayor o igual a 68 | Promedio de referencia de la escala SUS (Bangor et al., 2008\) |
| C5.2 | Usabilidad | La tasa de éxito de tareas es mayor o igual a 80 % | Criterio definido por el equipo |

8. ### **Consideraciones éticas**

El corpus de evaluación proviene de conjuntos de datos públicos, utilizados conforme a sus condiciones de uso. Las pruebas de carga y de inyección de fallos se ejecutan con usuarios de prueba creados en dominios reservados para documentación, sin datos personales reales. Para la evaluación de usabilidad, la participación es voluntaria y está precedida por un consentimiento informado que explica el propósito del estudio, el uso de los datos y el derecho a retirarse en cualquier momento; las respuestas se registran de forma anónima. Dado que el trabajo involucra una lengua originaria, se procura que la interacción con hablantes de quechua respete su lengua y su contexto cultural. Finalmente, se asume el compromiso de reportar los resultados de manera íntegra, incluidos los resultados desfavorables, las desviaciones respecto del plan y los errores detectados durante la ejecución.

2. ## **RESULTADOS**

Esta sección describe la ejecución del protocolo y presenta los resultados obtenidos siguiendo el mismo orden de dimensiones. Siguiendo las guías para el reporte de experimentos en ingeniería de software, la ejecución se describe de forma separada de los resultados, con el propósito de declarar las condiciones reales en que se aplicó cada técnica y las desviaciones dadas en el desarrollo (Jedlitschka et al., 2008).

1. ### **Resultados Cuantitativos**

El protocolo se ejecutó en dos iteraciones. En la primera, la verificación y las comparaciones controladas se realizaron en el entorno local con Docker Compose, y la prueba de carga progresiva en Azure Container Apps. Todos los contenedores alcanzaron un estado saludable, y los flujos de registro, inicio de sesión, transcripción, persistencia y consulta funcionaron correctamente en ambas arquitecturas. A modo de ejemplo, la transcripción de un clip real del corpus produjo el texto "wañuchisunchu kay suwakunata", idéntico a su referencia, tanto en la plataforma como en la línea base. Se confirmó también que la precisión de cómputo de cada transcripción quedó registrada en la base de datos, y las pruebas de integración contra la pila en ejecución se superaron en su totalidad.

Durante la verificación de la primera iteración se detectaron y corrigieron cuatro errores que no eran observables mediante pruebas con dependencias simuladas. El primero fue una incompatibilidad de versiones entre las librerías transformers y torch que impedía cargar el modelo, corregida fijando versiones compatibles. El segundo y el tercero correspondieron a diferencias entre las respuestas reales de los servicios y las esperadas por el cliente de medición: el código de error ante un correo ya registrado y la forma de la respuesta de la solicitud de transcripción, que en la plataforma no incluye el tiempo de procesamiento y obliga a consultar el registro completo de la transcripción. Sin esta última corrección, el cálculo de RTF y WER habría producido valores inválidos. El cuarto fue un dominio de correo de prueba rechazado por la validación de datos, reemplazado por un dominio reservado para documentación.

La segunda iteración se ejecutó íntegramente en el entorno local descrito en el protocolo. Las pruebas automatizadas de los servicios modificados se superaron en su totalidad (75 en api-gateway, 44 en asr-service y 26 en audio-processor), y una transcripción de extremo a extremo del clip de carga respondió en 2.9 s por la vía síncrona y en 2.7 s por la vía asíncrona. Esta iteración también detectó y corrigió errores, que se declaran porque afectan la interpretación de los resultados:

* En la primera iteración, con asr-service detenido, audio-processor respondía 200 sin transcripción y el cliente de carga lo contaba como éxito. El 100 % de éxito reportado entonces para la caída de asr-service **no era válido**. La segunda versión propaga el error como 503 y el cliente valida el contenido de cada respuesta.
* El motor CTranslate2 decodificaba de nuevo el final de la ventana de 30 s y producía continuaciones inexistentes en algunos clips. Se corrigió decodificando una sola ventana, como el motor de referencia.
* El cálculo del tamaño de la cola asíncrona confiaba en un contador de Redis que puede quedar desactualizado. Se reemplazó por un conteo exacto de los mensajes no entregados.
* Los cupos del control de admisión en el borde no se liberaban cuando el cliente se desconectaba. Se corrigió protegiendo la liberación frente a la cancelación.

La evaluación con GPU se ejecutó después de completar la del entorno local, con la misma versión del código, el mismo corpus y el mismo clip de carga. Antes de medir se verificó que tanto asr-service como el monolito cargaran el modelo en la GPU, y que la inferencia efectivamente se ejecutara en ella: durante una ráfaga de 32 transcripciones, la GPU alcanzó hasta un 99 % de uso y el planificador agrupó las solicitudes en lotes de hasta seis clips. Una transcripción de extremo a extremo del clip de carga respondió en 0.62 s por la vía síncrona y en 0.77 s por la vía asíncrona, frente a los 2.9 s y 2.7 s del entorno local. No fue necesario modificar el código ni descartar ninguna repetición. Se declaran tres aspectos de la ejecución que influyen en la interpretación de los resultados:

* En el escenario C de la prueba de adaptación, la migración de la CPU a la GPU ocurrió durante el periodo de reposo previo a la ráfaga, cuando no había transcripciones en curso. El resultado demuestra que el traslado se produce en caliente, sin reiniciar el servicio, pero no permite afirmar que se produzca sin interrumpir inferencias en curso. Se decidió reportar el resultado tal como se obtuvo, sin repetir la prueba con otra configuración.
* Durante la prueba comparativa con GPU, el monolito respondió con errores internos a parte de los inicios de sesión desde 100 usuarios, porque su único proceso agotó las conexiones disponibles hacia su base de datos. Este comportamiento forma parte del resultado de la línea base y no se corrigió.
* El límite de admisión en el borde (73 transcripciones en curso) se calculó con la arquitectura v2 en su configuración normal, en la que el mecanismo de adaptación puede cambiar a fp16. En la prueba comparativa con el monolito, la precisión se fijó en fp32, que es más lenta, y el límite no se volvió a calcular para esa condición.

1. #### **Síntesis de métricas frente a los criterios de aceptación**

La siguiente tabla resume el resultado de cada criterio de aceptación. Para los criterios de disponibilidad, escalabilidad y rendimiento se reportan los resultados de la segunda iteración, que corresponden a la arquitectura final, primero en el entorno local sin GPU y, cuando corresponde, en el equipo con GPU. El detalle de cada dimensión se presenta en los apartados siguientes.

Tabla X. Resultados frente a los criterios de aceptación.

| Código | Resultado obtenido | Estado |
| ----- | ----- | ----- |
| C1.1 | Éxito global entre 93.6 % y 100 % ante la caída de cada servicio individual, frente a 60.5 % del monolito (0 % durante su caída) | Cumple |
| C1.2 | Detección media entre 1.1 s y 1.9 s según el escenario | Cumple |
| C1.3 | Ninguna caída se propagó a servicios vecinos | Cumple |
| C1.4 | 100 % de éxito con la carga dentro de la capacidad (10 usuarios), en todas las configuraciones de la segunda versión. Con GPU, 100 % de éxito con 10 y 50 usuarios | Cumple |
| C1.5 | MTTR medio entre 4.9 s y 8.7 s | Cumple |
| C1.6 | 0 trabajos perdidos ante la caída de asr-service con carga asíncrona | Cumple |
| C1.7 | 100 % de éxito con auth-service caído y validación local, frente a 42.9 % con validación remota | Cumple |
| C2.1 | Throughput máximo 2.4 veces mayor que la referencia en el mismo hardware (0.86 frente a 0.36 transcripciones/s) y techo de Little de 10 frente a 4 usuarios. Con GPU, goodput máximo de 9.8 transcripciones/s, capacidad de 50 usuarios dentro del objetivo de servicio y techo de Little de 119 usuarios | Cumple |
| C2.2 | Asíncrono: 99.98 % de los trabajos aceptados y 100 % de los aceptados completados con 1000 usuarios. Síncrono: exceso rechazado con 503, sin errores internos (0 %, frente a 71.6 % sin admisión en el borde). Con GPU: 100 % de 25 151 trabajos aceptados y completados; en modo síncrono, 0 % de errores internos frente a 9.4 % sin admisión en el borde | Cumple |
| C2.3 | El mecanismo de adaptación aplicó decisiones en las 6 repeticiones de la ráfaga, y en las 9 repeticiones con GPU | Cumple |
| C2.4 | La única adaptación que no mejoró el costo de inferencia se revirtió automáticamente. Con GPU, todas las adaptaciones superaron su periodo de prueba | Cumple |
| C3.1 | RTF mediano de 0.149 sobre el corpus con el motor de referencia, y de 0.069 con el motor optimizado (muestra de 30 clips). Con GPU, RTF mediano de 0.031 sobre el corpus | Cumple |
| C3.2 | Tiempo de respuesta mediano de 9.4 s con 10 usuarios y un clip de 24 s en el entorno local, y de 4.7 s en la nube (primera iteración). Con GPU, 1.2 s con 10 usuarios | Cumple |
| C3.3 | Mediana de 14.9 s frente a 15.6 s con 10 usuarios (U de Mann-Whitney, p = 0.034, delta de Cliff = −0.107, efecto despreciable); desde 50 usuarios el monolito deja de responder y la propuesta mantiene 0.33–0.56 req/s. Con GPU, la propuesta fue significativamente más rápida en todos los escalones (1.3 s frente a 4.3 s con 10 usuarios; delta de Cliff entre −0.78 y −0.98, efecto grande) | Cumple |
| C3.4 | Con GPU, precisión fp16 y lotes de 8 clips, 8.8 veces el throughput de la CPU en fp32 (98.4 frente a 11.2 segundos de audio por segundo), sin diferencia significativa de WER (Wilcoxon, p = 0.18) | Cumple |
| C4.1 | 0 transcripciones vacías, tanto en CPU como en GPU | Cumple |
| C4.2 | 0.6 % de clips con WER superior a 1.5 (0.7 % con GPU) | Cumple |
| C4.3 | Sin diferencia significativa en WER (p \= 0.6716) ni en CER (p \= 0.9703) | Cumple |
| C4.4 | WER mediano de 0.697 | En proceso |
| C5.1 | \[Pendiente\] | Pendiente |
| C5.2 | \[Pendiente\] | Pendiente |

2. #### **Disponibilidad**

La prueba de inyección de fallos se ejecutó en el entorno local según el procedimiento planificado, con 10 usuarios concurrentes y tres repeticiones por escenario. Una ejecución preliminar con 50 usuarios mostró que esa carga supera la capacidad de la plataforma en el hardware de evaluación: solo el 57.5 % de las solicitudes tenía éxito antes de inyectar el fallo. Con esa carga, la prueba habría medido la saturación y no la respuesta ante el fallo, por lo que se adoptó la carga correspondiente a la capacidad. La siguiente tabla presenta los resultados agregados de las tres repeticiones.

Tabla X. Resultados de la inyección de fallos.

| Escenario | Detección (s) | MTTR (s) | Éxito antes | Éxito durante | Éxito después | Éxito global | Propagación |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| D1 asr-service | 1.3 | 4.9 | 100 % | 0 % (45 rechazos 503) | 100 % | 93.6 % | No |
| D2 auth-service, validación local | 1.3 | 5.5 | 100 % | 100 % | 100 % | 100 % | No |
| D2b auth-service, validación remota | 1.4 | 4.9 | 100 % | 42.9 % | 100 % | 97.8 % | No |
| D3 transcription-manager | 1.8 | 6.0 | 100 % | 100 % | 100 % | 100 % | No |
| D4 asr-service, carga asíncrona | 1.9 | 4.9 | 100 % | 100 % | 100 % | 100 % (0 trabajos perdidos) | No |
| D5 Redis | 1.1 | 8.7 | 100 % | 100 % | 100 % | 100 % | No |
| D6 asr-service congelado 60 s | 1.1 | — | 100 % | — | 96.0 % | 96.9 % | No |
| D7 monolito | 1.2 | 5.6 | 100 % | 0 % | 81.3 % | 60.5 % | No aplica |

Gracias a la política de reinicio, todos los componentes se recuperaron solos en menos de 9 s, algo que en la primera iteración no pudo observarse porque la detención se hacía como una parada ordenada. La caída de asr-service en modo síncrono es la única que afecta a las transcripciones durante el corte, como corresponde a una única réplica del servicio de inferencia. Aun así, las solicitudes afectadas reciben de inmediato un 503 con la indicación de reintentar, en lugar de quedar en espera, y el servicio vuelve al 100 % al recuperarse. En modo asíncrono, la misma caída no afecta a ningún trabajo: los mensajes pendientes se vuelven a entregar al proceso reiniciado.

La caída de auth-service, que en la primera iteración afectó al 65.3 % de las solicitudes, no tuvo ningún efecto con la validación local del token. La ejecución del mismo escenario con la validación remota, que reproduce el comportamiento original, redujo el éxito durante el corte al 42.9 %, lo que confirma que la mejora se debe a la validación local. Las caídas de transcription-manager y de Redis tampoco afectaron a las transcripciones: la persistencia se realiza en segundo plano con reintentos, y la validación de revocaciones admite el token si Redis no responde. En la línea base, la caída del proceso monolítico dejó sin servicio al 100 % de las solicitudes durante el corte, porque todos los componentes comparten el mismo proceso.

En cuanto a la disponibilidad bajo carga, con la carga dentro de la capacidad (10 usuarios) todas las configuraciones de la segunda versión completaron el 100 % de las solicitudes. Por encima de la capacidad, el comportamiento depende del control de admisión, como se detalla en el apartado siguiente.

3. #### **Escalabilidad**

*Primera iteración (Azure Container Apps).* La prueba de carga progresiva se ejecutó en cuatro rondas, una por configuración de escalado horizontal. El autoescalado de asr-service y de auth-service incrementó el número de usuarios concurrentes de 254 a 353 (39.0 %), pero en todas las configuraciones la tasa de error del escalón final superó el 85 % y el percentil 99 del tiempo de respuesta llegó a 149 s. El análisis de los registros mostró que la saturación de auth-service se ocultaba detrás de errores 401, y que el sistema "admitía más y fallaba después": la cadena síncrona de servicios no tenía control de admisión. El mecanismo de adaptación vertical no registró ninguna decisión, porque su señal, el uso de CPU, no detectaba el encolamiento. Estos hallazgos motivaron la segunda versión de la arquitectura.

*Segunda iteración (entorno local).* La siguiente tabla compara, en el mismo hardware, la réplica de la arquitectura original (S1), la arquitectura v2 sin admisión en el borde (S2) y la arquitectura v2 completa (S2c). Los valores son la mediana de tres repeticiones; el goodput se expresa en transcripciones completadas por segundo.

Tabla X. Resultados de la prueba de carga progresiva (segunda iteración).

| Usuarios | S1 goodput | S1 p50 / p95 (s) | S1 fallos | S2 goodput | S2 p50 / p95 (s) | S2 fallos | S2c goodput | S2c p50 / p95 (s) | S2c fallos |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| 10 | 0.36 | 25.6 / 26.8 | — | 0.82 | 9.4 / 13.3 | — | 0.82 | 9.5 / 13.8 | — |
| 50 | 0.33 | 84.7 / 99.9 | timeout 24 % | 0.86 | 54.6 / 56.9 | 503 9 % (0.46 s) | 0.77 | 13.1 / 14.3 | 503 96 % (0.01 s) |
| 100 | 0.12 | 98.6 / 100.3 | timeout 84 % | 0.34 | 64.0 / 96.4 | 503 97 % (2.98 s); timeout 1 % | 0.68 | 14.2 / 17.2 | 503 98 % (0.01 s) |
| 200 | 0.11 | 99.7 / 100.3 | timeout 93 % | 0.31 | 72.6 / 79.9 | 503 98 % (9.56 s) | 0.48 | 20.4 / 22.6 | 503 99 % (0.06 s) |
| 500 | 0.06 | 99.9 / 100.3 | timeout 99 % | 0.34 | 80.1 / 100.5 | 503 90 % (25.81 s); 5xx 7 % | 0.48 | 22.9 / 27.4 | 503 99 % (2.85 s) |
| 1000 | 0.01 | 105.1 / 110.1 | timeout 40 %; 5xx 60 % | 0.22 | 104.9 / 121.2 | 503 26 % (51.95 s); timeout 1 %; 5xx 72 % | 0.44 | 26.5 / 33.5 | 503 99 % (5.43 s) |

En la referencia (S1), la plataforma atiende 0.36 transcripciones por segundo y, desde 50 usuarios, las solicitudes esperan hasta agotar el tiempo límite de 100 s: con 100 usuarios, el 84 % termina en timeout, y con 1000 usuarios no se completa ninguna. Los cambios de la arquitectura v2 sin admisión en el borde (S2) multiplican por 2.4 el goodput máximo y reducen el tiempo de respuesta mediano con 10 usuarios de 25.6 s a 9.4 s. Sin embargo, desde 100 usuarios el goodput cae a 0.3 transcripciones por segundo, los rechazos tardan hasta 52 s y con 1000 usuarios el 71.6 % de las solicitudes termina en error interno. La causa es que el control de admisión de S2 actúa al final de la cadena: antes de rechazar una solicitud, api-gateway y audio-processor ya recibieron, convirtieron y registraron el audio, y ese trabajo desperdiciado compite por la CPU con la inferencia.

Con la admisión en el borde (S2c), el exceso se rechaza en api-gateway antes de procesar el audio, en una mediana de 0.01 s con hasta 200 usuarios. El goodput se mantiene cerca de su máximo hasta 100 usuarios, las solicitudes admitidas se responden en 13 a 17 s en lugar de 55 a 105 s, y no se registran errores internos en ningún escalón. Con 500 y 1000 usuarios el goodput desciende a 0.44–0.48 transcripciones por segundo. Este descenso se atribuye a que el generador de carga se ejecuta en el mismo equipo y reenvía de inmediato cada solicitud rechazada con el audio completo, sin respetar la indicación Retry-After: con 1000 usuarios emite alrededor de 200 solicitudes por segundo que compiten por la misma CPU.

Por la ley de Little, el techo de usuarios síncronos que el hardware de evaluación puede atender con un tiempo de respuesta de 10 s es de unos 10 usuarios con la arquitectura v2 (0.86 × 12) y de 4 con la original (0.36 × 12). Ninguna arquitectura puede atender 1000 usuarios síncronos en este equipo; lo que distingue a la arquitectura propuesta es que, ante esa carga, sigue atendiendo a su capacidad y rechaza el exceso de forma explícita, en lugar de colapsar.

La alternativa para atender la demanda que supera la capacidad es la API asíncrona. La siguiente tabla presenta el resultado de la corrida asíncrona con 1000 usuarios.

Tabla X. Resultados de la prueba de carga asíncrona (S2b).

| Repetición | Trabajos enviados | Aceptados | Procesados | Fallidos | Completitud |
| ----- | ----- | ----- | ----- | ----- | ----- |
| 1 | 1905 | 1905 (100 %) | 1905 | 0 | 100 % |
| 2 | 1757 | 1756 (99.94 %) | 1756 | 0 | 100 % |
| 3 | 1865 | 1865 (100 %) | 1865 | 0 | 100 % |

La plataforma aceptó el 99.98 % de los 5527 trabajos enviados y completó el 100 % de los aceptados, sin pérdidas ni duplicados. El único envío no aceptado fue un error interno en el pico de 1000 usuarios. La cola absorbe la demanda que excede la capacidad y la procesa a la velocidad que el hardware permite, a costa de un mayor tiempo de espera para cada trabajo.

*Evaluación con GPU.* La misma rampa de carga se aplicó en el equipo con GPU. Primero se ejecutó la arquitectura v2 sin admisión en el borde (S3), cuyo resultado sirvió para calcular el límite de admisión, y luego la arquitectura v2 completa, con admisión en el borde (S3c). La siguiente tabla compara ambas corridas. Al igual que en el entorno local, los valores son la mediana de tres repeticiones, y el tiempo de respuesta corresponde solo a las solicitudes que se completaron con éxito.

Tabla X. Resultados de la prueba de carga progresiva con GPU.

| Usuarios | S3 goodput | S3 p50 / p95 (s) | S3 fallos | S3c goodput | S3c p50 / p95 (s) | S3c fallos |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| 10 | 3.04 | 1.2 / 1.8 | — | 3.06 | 1.2 / 1.9 | — |
| 50 | 9.28 | 3.2 / 5.3 | — | 9.39 | 3.2 / 4.2 | — |
| 100 | 9.51 | 7.7 / 8.5 | 503 20 % (0.25 s) | 9.78 | 7.0 / 7.6 | 503 39 % (0.00 s) |
| 200 | 4.71 | 17.8 / 19.6 | 503 84 % (2.27 s) | 9.24 | 8.3 / 8.7 | 503 85 % (0.00 s) |
| 500 | 3.64 | 27.0 / 35.3 | 503 89 % (11.55 s) | 8.44 | 9.2 / 9.6 | 503 96 % (0.00 s) |
| 1000 | 3.64 | 43.4 / 65.9 | 503 77 % (24.77 s); 5xx 9 % | 7.91 | 9.7 / 10.6 | 503 98 % (0.01 s) |

Con GPU, la plataforma completa entre 9 y 10 transcripciones por segundo, unas once veces más que la arquitectura v2 en el entorno local sin GPU (0.86), y atiende 50 usuarios con un tiempo de respuesta mediano de 3.2 s. El objetivo de servicio planteado en el protocolo es que el 95 % de las solicitudes se responda en 10 s o menos (percentil 95 ≤ 10 s) con una tasa de error de hasta 5 %. Con ese objetivo, la capacidad pasa de 10 usuarios en CPU a 50 usuarios con GPU.

Sin admisión en el borde (S3), la GPU repite el patrón observado en CPU con S2: por encima de 100 usuarios, el goodput cae a menos de la mitad, los rechazos tardan hasta 25 s en llegar al cliente y, con 1000 usuarios, el 9 % de las solicitudes termina en error interno. El goodput máximo de S3 se registró con 100 usuarios (9.51 transcripciones por segundo), con un tiempo de respuesta mediano de 7.7 s en ese escalón. Por la ley de Little, el número de solicitudes que la plataforma mantiene en curso cuando trabaja a su máxima capacidad es 9.51 × 7.7 ≈ 73, que se adoptó como límite de admisión en el borde. En el entorno local, el mismo cálculo dio un límite de 10.

Con ese límite (S3c), el goodput se mantiene entre 7.9 y 9.8 transcripciones por segundo desde 50 hasta 1000 usuarios, el doble que sin admisión en el borde en los escalones altos. El percentil 95 de las solicitudes atendidas con 1000 usuarios baja de 65.9 s a 10.6 s, el exceso se rechaza en milisegundos y no se registran errores internos en ningún escalón. El alto porcentaje de rechazos en los escalones altos no indica una falla del sistema: el generador de carga reenvía de inmediato cada solicitud rechazada, sin respetar la indicación Retry-After, y con 1000 usuarios llegó a emitir unas 65 000 solicitudes en un solo escalón de 180 s.

Por la ley de Little, el techo de usuarios síncronos que la plataforma puede atender con GPU dentro de un tiempo de respuesta de 10 s es de aproximadamente 119 usuarios (9.92 × 12), frente a unos 10 en el entorno local sin GPU. Ni siquiera con GPU es posible atender 1000 usuarios síncronos dentro del objetivo de servicio; nuevamente, lo que distingue a la arquitectura propuesta es que sigue atendiendo cerca de su capacidad y rechaza el exceso de forma explícita.

La siguiente tabla presenta el resultado de la corrida asíncrona con GPU y 1000 usuarios.

Tabla X. Resultados de la prueba de carga asíncrona con GPU (S4).

| Repetición | Trabajos enviados | Aceptados | Procesados | Fallidos | Completitud |
| ----- | ----- | ----- | ----- | ----- | ----- |
| 1 | 8543 | 8543 (100 %) | 8543 | 0 | 100 % |
| 2 | 8236 | 8236 (100 %) | 8236 | 0 | 100 % |
| 3 | 8372 | 8372 (100 %) | 8372 | 0 | 100 % |

Con GPU, la plataforma aceptó y completó el 100 % de los 25 151 trabajos enviados en las tres repeticiones, sin pérdidas ni duplicados, cerca de 4.6 veces más trabajos que en el entorno local sin GPU (5527). La cola quedó vacía al terminar cada repetición. Hasta 100 usuarios, cada trabajo se completó en una mediana de entre 2 y 10 s. Desde 200 usuarios, la demanda supera la capacidad de unas 9 transcripciones por segundo, y la cola absorbe la diferencia a cambio de un mayor tiempo de espera, que con 1000 usuarios alcanzó una mediana de 108 s, sin que se rechazara ni se perdiera ningún trabajo.

*Adaptación vertical.* La siguiente tabla presenta el comportamiento del mecanismo de adaptación ante la ráfaga de 24 clientes, con tres repeticiones por motor de inferencia.

Tabla X. Comportamiento del mecanismo de adaptación vertical.

| Motor | Decisiones aplicadas | Tiempo de reacción (s) | Transcripciones/s antes → después | Resultado del periodo de prueba |
| ----- | ----- | ----- | ----- | ----- |
| CTranslate2 | 2 en cada repetición | 12.8 – 13.4 | 0.46 → 0.89 (mediana) | int8 superó el periodo de prueba en 3 de 3 |
| transformers | 2 en cada repetición | 16.2 – 16.8 | 0.25 → 0.50 (mediana) | int8 superó el periodo de prueba en 2 de 3 y se revirtió en 1 de 3 |

En todas las repeticiones, el mecanismo detectó la presión de carga por la profundidad de la cola, cambió la precisión de fp32 a int8 y volvió a fp32 al terminar la ráfaga, con un tiempo de reacción de entre 13 y 17 s. Con el motor CTranslate2, el cambio casi duplicó el throughput. Con el motor transformers, en una de las repeticiones la ganancia medida fue inferior al 5 % exigido y el mecanismo revirtió el cambio, registrando ese estado como rechazado en el equipo. Esto contrasta con la primera iteración, en la que el mecanismo no tomó ninguna decisión, y con una prueba preliminar en otro equipo, donde la cuantización int8 resultó dos veces más lenta y se revirtió de forma automática. La verificación por medición permite que una misma política produzca el resultado correcto en hardware distinto.

En el equipo con GPU, la prueba de adaptación se aplicó a los tres escenarios descritos en el protocolo. La siguiente tabla resume sus resultados.

Tabla X. Comportamiento del mecanismo de adaptación con GPU.

| Escenario | Decisiones aplicadas | Tiempo de reacción (s) | Transcripciones/s antes → después | Resultado del periodo de prueba | Estado final |
| ----- | ----- | ----- | ----- | ----- | ----- |
| A: inicio en GPU | De 6 a 8 por repetición (precisión y tamaño de lote) | 3.7 – 4.0 | 2.1 – 4.0 → 9.6 – 9.7 | fp16 superó el periodo de prueba en 3 de 3 | GPU en fp32 en 2 de 3; GPU en fp16 en 1 de 3 |
| B: solo CPU | 2 por repetición (precisión) | 14.9 – 15.1 | 0.53 → 0.86 | int8 superó el periodo de prueba en 3 de 3 | CPU en fp32 en 3 de 3 |
| C: inicio en CPU con GPU disponible | De 5 a 7 por repetición, incluido el cambio de dispositivo | 4.1 – 4.2 | 3.8 – 3.9 → 9.8 | fp16 superó el periodo de prueba en 3 de 3 | GPU en fp32 en 3 de 3 |

En el escenario A, el mecanismo reaccionó a la ráfaga en unos 4 s, aumentó el tamaño de lote de 8 a 16 clips y cambió la precisión de fp32 a fp16. El periodo de prueba confirmó que fp16 era más rápido, con un costo de unos 0.13 s por clip frente a 0.21 s en fp32, y el throughput subió a casi 10 transcripciones por segundo. Al terminar la ráfaga, el servicio volvió a fp32 en dos de las tres repeticiones; en la restante permaneció en fp16 al finalizar los 90 s de reposo. En el escenario B, restringido a la CPU, el comportamiento fue el mismo observado en el entorno local: la reacción tomó unos 15 s y la cuantización int8 superó su periodo de prueba en las tres repeticiones.

El escenario C responde a la pregunta de si la plataforma puede aprovechar un acelerador que se encuentra disponible sin necesidad de reiniciarse. En las tres repeticiones, el servicio arrancó en la CPU y, a los nueve segundos, el mecanismo detectó la GPU y trasladó a ella la inferencia, sin reiniciar el servicio; después se comportó igual que en el escenario A. Como se indicó en la ejecución, este cambio ocurrió durante el periodo de reposo previo a la ráfaga, cuando no había transcripciones en curso, por lo que la evidencia muestra una migración en caliente, pero no una migración con inferencias en curso. Con GPU, todas las adaptaciones superaron su periodo de prueba, de modo que no hubo reversiones; el mecanismo de reversión quedó verificado en el entorno local.

4. #### **Rendimiento**

La evaluación de reconocimiento procesó los 2111 clips del corpus en CPU con precisión fp32. El RTF mediano sobre el corpus fue de 0.149, con un rango intercuartílico de 0.120 a 0.201. Por fuente, el RTF mediano fue de 0.135 en Huqariq y de 0.183 en Siminchik. En términos prácticos, la plataforma procesa un clip de 10 s en aproximadamente 1.5 s de cómputo. En la nube, con 10 usuarios concurrentes y sin autoescalado, el tiempo de respuesta mediano fue de 4.7 s.

La misma evaluación, repetida en el equipo con GPU sobre los 2111 clips, obtuvo un RTF mediano de 0.031, con un rango intercuartílico de 0.026 a 0.038; por fuente, 0.029 en Huqariq y 0.035 en Siminchik. Todas las transcripciones se ejecutaron en la GPU con precisión fp32, ya que, al procesarse los clips uno a la vez, el mecanismo de adaptación no tuvo presión de carga para cambiar a fp16. Un RTF de 0.031 significa que la plataforma procesa un clip de 10 s en unos 0.3 s, aproximadamente 4.8 veces más rápido que en la CPU.

La siguiente tabla presenta el throughput de inferencia de las principales configuraciones evaluadas, medido directamente contra asr-service.

Tabla X. Throughput de inferencia por configuración (segundos de audio procesados por segundo).

| Configuración | 1 cliente | 4 clientes | 16 clientes | Máximo | Respecto de la referencia | p95 con 16 clientes (s) |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| transformers fp32 (referencia) | 7.1 | 6.1 | 5.0 | 7.1 | 1.00 | 47.7 |
| transformers int8 | 9.8 | 8.8 | 8.1 | 9.8 | 1.39 | 32.7 |
| CTranslate2 int8, 1 línea | 13.5 | 12.2 | 10.3 | 13.8 | 1.95 | 23.5 |
| CTranslate2 int8, 3 líneas (seleccionada) | 11.9 | 19.4 | 16.3 | 19.4 | 2.74 | 17.5 |

El motor CTranslate2 con cuantización int8 y tres líneas de inferencia en paralelo alcanzó 2.7 veces el throughput de la configuración de referencia, sin hardware adicional, y redujo el percentil 95 de la latencia con 16 clientes de 47.7 s a 17.5 s. Como control, se comparó la transcripción de los 30 clips de la muestra con cada motor y precisión. Ninguna configuración mostró una diferencia significativa de WER respecto de la referencia (prueba de rangos con signo de Wilcoxon: p \= 0.11 para CTranslate2 fp32 y p \= 0.22 para CTranslate2 int8), y la mediana de WER fue la misma (0.75). En una sola solicitud, el RTF mediano pasó de 0.135 a 0.069.

La siguiente tabla presenta la misma medición en el equipo con GPU. En este caso, la configuración de referencia es la CPU de ese mismo equipo con el motor transformers en fp32, de modo que todas las razones de la tabla comparan configuraciones sobre el mismo hardware.

Tabla X. Throughput de inferencia con GPU (segundos de audio procesados por segundo).

| Configuración | Máximo | Respecto de la referencia | Tiempo mediano con 1 cliente (s) |
| ----- | ----- | ----- | ----- |
| CPU, transformers fp32 (referencia) | 11.2 | 1.0 | 1.375 |
| CPU, transformers int8 | 16.8 | 1.5 | 1.070 |
| CPU, CTranslate2 int8, 3 líneas (mejor configuración de CPU) | 28.4 | 2.5 | — |
| GPU, fp32, sin lotes | 36.5 | 3.3 | 0.389 |
| GPU, fp16, sin lotes | 58.7 | 5.3 | 0.241 |
| GPU, fp16, lotes de 4 | 91.3 | 8.2 | 0.273 |
| GPU, fp16, lotes de 8 | 98.4 | 8.8 | 0.272 |
| GPU, fp16, lotes de 16 | 100.0 | 8.9 | 0.270 |

La GPU con precisión fp16 y lotes de 8 clips procesó 98.4 segundos de audio por cada segundo de cómputo, 8.8 veces más que la referencia de CPU y 3.5 veces más que la mejor configuración de CPU. La tabla permite distinguir el aporte de cada técnica: el solo paso a la GPU triplicó el throughput, la precisión fp16 lo elevó a 5.3 veces y el procesamiento por lotes a casi 9 veces. El beneficio de los lotes se agota en 8 clips, ya que duplicar el tamaño a 16 solo aportó un 1.6 % adicional. Con un solo cliente, el tiempo por transcripción bajó de 1.375 s a entre 0.24 y 0.39 s, una diferencia significativa y de efecto grande en todas las configuraciones de GPU (U de Mann-Whitney, p < 0.001; delta de Cliff entre −0.83 y −0.98).

Como control de calidad, se comparó la transcripción de cada uno de los 30 clips de la muestra con la de la referencia. El WER medio fue de 0.735 en la referencia, 0.736 en la GPU con fp32 y 0.742 en la GPU con fp16, sin diferencia significativa (prueba de rangos con signo de Wilcoxon, p = 0.18 para fp16), y la mediana de WER fue de 0.75 en todos los casos. En 25 de los 30 clips, la transcripción con fp16 fue idéntica a la de la referencia, y las transcripciones con fp16 fueron iguales para todos los tamaños de lote, lo que confirma que agrupar solicitudes no altera el resultado de cada una.

La prueba de carga comparativa se ejecutó con la misma rampa contra ambas arquitecturas, con tres repeticiones cada una, en el mismo equipo y con el mismo motor de inferencia, la misma precisión fijada (fp32, sin adaptación) y el mismo número de líneas de inferencia. La siguiente tabla presenta los resultados (mediana de las repeticiones).

Tabla X. Tiempo de respuesta y goodput de la arquitectura propuesta frente al monolito.

| Usuarios | Propuesta: goodput (req/s) | Propuesta: p50 / p95 (s) | Propuesta: fallos | Monolito: goodput (req/s) | Monolito: p50 / p95 (s) | Monolito: fallos |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| 10 | 0.56 | 14.9 / 19.8 | Ninguno | 0.48 | 15.6 / 24.5 | Ninguno |
| 50 | 0.56 | 17.7 / 21.7 | Exceso rechazado con 503 | 0.01 | 22.3 / 23.0 | Sin respuesta |
| 100 | 0.45 | 21.0 / 26.5 | Exceso rechazado con 503 | 0 | — | 100 % sin respuesta (300 s) |
| 200 | 0.33 | 27.9 / 34.5 | Exceso rechazado con 503 | 0 | — | 100 % sin respuesta |
| 500 | 0.35 | 30.4 / 37.1 | Exceso rechazado con 503 | 0 | — | 100 % sin respuesta |
| 1000 | 0.37 | 32.1 / 41.2 | Exceso rechazado con 503, sin errores internos | 0 | — | 100 % sin respuesta |

Con 10 usuarios, el único escalón en que ambas arquitecturas completan solicitudes, la arquitectura propuesta obtuvo un tiempo de respuesta mediano de 14.9 s frente a 15.6 s del monolito. La diferencia fue estadísticamente significativa (U de Mann-Whitney, p \= 0.034), pero con un tamaño de efecto despreciable (delta de Cliff de −0.107), por lo que en carga baja ambas arquitecturas responden en tiempos equivalentes. La propuesta tuvo además un percentil 95 menor (19.8 s frente a 24.5 s) y un goodput 17 % mayor. Las tres llamadas HTTP adicionales entre servicios no penalizan el tiempo de respuesta.

Desde 50 usuarios, el monolito dejó de completar solicitudes, incluidos los inicios de sesión, y las solicitudes agotaron el tiempo límite de 300 s del cliente; el proceso no se detuvo, pero quedó procesando una cola de solicitudes ya abandonadas. La causa es su diseño de proceso único: la verificación de contraseñas, una operación intensiva en CPU que se ejecuta en el mismo proceso que el resto de la lógica, bloquea al único worker cada vez que nuevos usuarios inician sesión, y con ello detiene también las transcripciones. En la arquitectura propuesta, el mismo código se ejecuta en auth-service, con sus propios workers, y la inferencia continúa: la plataforma mantuvo entre 0.33 y 0.56 transcripciones por segundo en todos los escalones y rechazó el exceso de forma explícita, sin errores internos.

La prueba comparativa se repitió en el equipo con GPU, con ambas arquitecturas ejecutando la inferencia en la GPU con precisión fp32 fija y tres repeticiones cada una. La siguiente tabla presenta los resultados.

Tabla X. Tiempo de respuesta y goodput de la arquitectura propuesta frente al monolito con GPU.

| Usuarios | Propuesta: goodput (req/s) | Propuesta: p50 / p95 (s) | Monolito: goodput (req/s) | Monolito: p50 / p95 (s) | Monolito: fallos | Delta de Cliff |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| 10 | 3.06 | 1.3 / 1.8 | 1.63 | 4.3 / 5.2 | Ninguno | −0.933 |
| 50 | 4.94 | 7.8 / 9.9 | 1.52 | 25.4 / 32.9 | Ninguno | −0.976 |
| 100 | 5.07 | 14.5 / 15.3 | 1.56 | 45.3 / 56.5 | 48 errores internos | −0.974 |
| 200 | 4.53 | 16.6 / 17.8 | 1.28 | 53.5 / 66.0 | 726 errores internos | −0.963 |
| 500 | 4.18 | 18.5 / 20.2 | 0.97 | 53.7 / 68.9 | 4869 errores internos | −0.784 |
| 1000 | 3.91 | 19.6 / 22.3 | 0.30 | 67.9 / 69.5 | 1161 errores internos y 400 errores de conexión | −0.835 |

A diferencia del entorno local, con GPU la arquitectura propuesta fue más rápida que el monolito en todos los escalones, incluso con carga baja. Con 10 usuarios, su tiempo de respuesta mediano fue de 1.3 s frente a 4.3 s del monolito, con casi el doble de goodput. La diferencia fue estadísticamente significativa en los seis escalones (U de Mann-Whitney, p < 0.001), con un tamaño de efecto grande en todos ellos. El signo negativo del delta de Cliff indica que los tiempos de la propuesta tienden a ser menores que los del monolito. Esta ventaja se explica por el planificador de inferencia de la propuesta, que agrupa en lotes las solicitudes que llegan al mismo tiempo y aprovecha el paralelismo de la GPU; el monolito procesa las solicitudes de una en una. En CPU esta ventaja no se observó, porque en ese entorno el planificador procesa las solicitudes en lotes de un solo clip, igual que el monolito.

Con GPU, el monolito no dejó de responder desde 50 usuarios como en el entorno local, pero su tiempo de respuesta creció hasta 25 a 68 s, y desde 100 usuarios parte de los inicios de sesión terminó en error interno porque su único proceso agotó las conexiones disponibles hacia su base de datos. La propuesta, en cambio, no registró errores internos y rechazó el exceso de forma inmediata. Desde 100 usuarios, el percentil 95 de la propuesta (15 a 22 s) superó el objetivo de 10 s, porque en esta prueba la precisión se fijó en fp32, más lenta que la fp16 que el mecanismo de adaptación usaría bajo carga, y el límite de admisión no se recalculó para esa condición. Esto no afecta la comparación, que se realizó con el mismo dispositivo y la misma precisión en ambas arquitecturas.

La siguiente tabla presenta los resultados de latencia y volumen transmitido de la prueba comparativa de codificación.

Tabla X. Latencia y volumen transmitido en streaming.

| Condición | n | Latencia media (s) | IC 95 % | Bytes enviados (media) |
| :---- | :---- | :---- | :---- | :---- |
| PCM | 90 | 11.56 | 10.20 a 12.91 | 582 785 |
| Opus | 90 | 5.34 | 4.73 a 5.95 | 165 071 |

La condición Opus redujo la latencia en un 53.8 % y el volumen transmitido en un 71.7 % respecto de PCM. La diferencia de latencia fue estadísticamente significativa (U de Mann-Whitney, p \< 0.001) con un tamaño de efecto grande (delta de Cliff de 0.523).

5. #### **Calidad de reconocimiento**

La evaluación de reconocimiento se completó sobre la totalidad del corpus, sin clips excluidos, aplicando la normalización de texto. La comparación de calidad entre PCM y Opus se obtuvo de las mismas 90 sesiones por condición descritas en el apartado anterior, ya con el error de decodificación corregido.  
La siguiente tabla presenta los resultados sobre el corpus completo. Las métricas presentaron distribuciones no normales (Shapiro-Wilk, p \< 0.001), por lo que se reportan la mediana y el rango intercuartílico.

Tabla X. Calidad de reconocimiento sobre el corpus completo.

| Métrica | n | Mediana | Rango intercuartílico |
| :---- | :---- | :---- | :---- |
| WER | 2111 | 0.697 | 0.500 a 0.852 |
| CER | 2111 | 0.172 | 0.089 a 0.343 |

La siguiente tabla presenta los resultados desagregados por fuente del corpus.

Tabla X. Calidad de reconocimiento por fuente.

| Fuente | n | WER mediana | WER media | CER mediana |
| :---- | :---- | :---- | :---- | :---- |
| Huqariq | 1413 | 0.714 | 0.705 | 0.192 |
| Siminchik | 698 | 0.638 | 0.625 | 0.121 |

Respecto de las anomalías, no se registraron transcripciones vacías; 13 clips (0.6 %) presentaron un WER superior a 1.5, compatible con inserciones excesivas del modelo, y 46 clips (2.2 %) se transcribieron sin errores.

La evaluación sobre el corpus completo en el equipo con GPU obtuvo el mismo WER mediano (0.697, con rango intercuartílico de 0.500 a 0.852) y prácticamente el mismo CER mediano (0.172). Por fuente, el WER mediano fue de 0.714 en Huqariq y de 0.638 en Siminchik, iguales a los obtenidos en CPU. Tampoco hubo transcripciones vacías; 14 clips (0.7 %) presentaron un WER superior a 1.5 y 46 clips (2.2 %) se transcribieron sin errores. Estos resultados confirman que ejecutar el modelo en la GPU acelera el reconocimiento sin alterar su calidad.  
La siguiente tabla presenta la comparación de calidad entre las condiciones de streaming.  
Tabla X. Calidad de reconocimiento en streaming PCM frente a Opus.

| Métrica | PCM (media e IC 95 %) | Opus (media e IC 95 %) | Valor p | Delta de Cliff | Significativo |
| ----- | ----- | ----- | ----- | ----- | ----- |
| WER | 0.735 (0.668 a 0.801) | 0.736 (0.660 a 0.812) | 0.6716 | 0.037 | No |
| CER | 0.261 (0.206 a 0.316) | 0.271 (0.206 a 0.335) | 0.9703 | 0.003 | No |

No se encontró diferencia significativa de WER ni de CER entre ambas condiciones, y los tamaños de efecto fueron despreciables.

6. #### **Usabilidad**

   2. ### **Resultados Cualitativos**

Los resultados cualitativos provienen de los cuestionarios a expertos y de las preguntas abiertas aplicadas a usuarios finales, según el protocolo. Las respuestas abiertas se analizan mediante codificación temática, agrupando las observaciones recurrentes en categorías.

3. ## **Discusión**

   1. ### **Análisis Comparativo**

Los resultados se contrastan con cuatro referentes: la arquitectura de la primera iteración, la línea base monolítica, el estado del arte del reconocimiento de voz para quechua y lenguas de bajos recursos, y los criterios de aceptación del protocolo.

Respecto de la primera iteración, la segunda versión de la arquitectura convirtió en cumplidos los tres criterios que antes no se cumplían. En disponibilidad, la caída de auth-service pasó de afectar al 65.3 % de las solicitudes a no afectar a ninguna, y todos los componentes se recuperaron solos en menos de 9 s. En escalabilidad, la plataforma pasó de colapsar con timeouts de 100 s a mantenerse cerca de su capacidad y rechazar el exceso de forma explícita, y en modo asíncrono completó el 100 % de los trabajos aceptados con 1000 usuarios. En adaptación, el mecanismo pasó de no registrar ninguna decisión a reaccionar en todas las repeticiones. Estas mejoras no requirieron hardware adicional: se obtuvieron en un equipo sin GPU, sobre el mismo hardware en que se midió la réplica de la primera versión.

La evaluación con GPU muestra hasta dónde puede llegar la misma arquitectura cuando dispone de aceleración. Sin cambios en el código, la GPU con precisión fp16 y procesamiento por lotes multiplicó por 8.8 el throughput de inferencia frente a la CPU del mismo equipo, sin diferencia significativa de WER. Ese aumento se trasladó a la plataforma completa: el goodput pasó de 0.86 a cerca de 10 transcripciones por segundo, la capacidad dentro del objetivo de servicio de 10 a 50 usuarios y el techo de Little de 10 a 119 usuarios. En modo asíncrono, la plataforma procesó 4.6 veces más trabajos que sin GPU, de nuevo sin pérdidas. Los mecanismos diseñados en la segunda versión siguieron siendo necesarios con GPU: sin admisión en el borde, la plataforma con GPU repitió el patrón de degradación observado en CPU, con rechazos lentos y errores internos ante 1000 usuarios, y con ella esos errores desaparecieron. La GPU aumenta la capacidad, pero no sustituye a los mecanismos que controlan el comportamiento ante la sobrecarga.

Sobre la línea base monolítica, la comparación ofrece su evidencia más sólida en la dimensión de disponibilidad. Ante la caída de un componente, la arquitectura propuesta conservó entre el 93.6 % y el 100 % de las solicitudes exitosas, mientras que el monolito conservó el 60.5 % y quedó sin servicio durante toda su caída. En rendimiento, con carga baja ambas arquitecturas responden en tiempos equivalentes (14.9 s frente a 15.6 s de mediana, con un efecto despreciable), lo que indica que las llamadas adicionales entre servicios no penalizan la experiencia típica, en contraste con la preocupación señalada por Dean y Barroso (2013) sobre el crecimiento de la cola de la distribución al aumentar el número de componentes. Bajo carga, en cambio, la diferencia es categórica: el monolito dejó de responder desde 50 usuarios porque una operación de un componente, la verificación de contraseñas, bloqueó al proceso compartido, mientras que la propuesta siguió atendiendo a su capacidad. El aislamiento entre servicios protege, por tanto, no solo ante caídas sino también ante la competencia por recursos entre componentes. Con GPU, la comparación fue aún más favorable a la propuesta: fue más rápida que el monolito en todos los escalones, incluso con 10 usuarios (1.3 s frente a 4.3 s de mediana, con efecto grande), porque su planificador agrupa las solicitudes en lotes y aprovecha el paralelismo de la GPU, algo que el diseño del monolito no contempla. Bajo carga, el monolito volvió a fallar por la competencia entre sus componentes, esta vez al agotar las conexiones a su base de datos durante los inicios de sesión, mientras que la propuesta no registró errores internos. Villamizar et al. (2015) también evaluaron ambos patrones en despliegues en la nube y advirtieron que los beneficios de los microservicios dependen del contexto de carga y de la configuración de la infraestructura. Los resultados de este trabajo precisan esa observación: la separación en servicios aporta aislamiento de fallos por sí misma, pero la escalabilidad bajo sobrecarga depende de mecanismos explícitos, como el control de admisión y la cola asíncrona, que deben diseñarse como parte de la arquitectura.

Sobre el estado del arte, el WER mediano de 0.697 es elevado en términos absolutos, pero debe interpretarse considerando dos factores. Primero, se evitó deliberadamente evaluar con corpus que probablemente se solapan con los datos de entrenamiento del modelo, lo que produce una estimación más conservadora y realista que la que se obtendría con datos contaminados. Segundo, el CER mediano de 0.172 indica que el modelo reconoce correctamente la mayor parte de los caracteres, y que una proporción considerable de los errores por palabra corresponde a diferencias parciales dentro de palabras largas, lo que es consistente con la alta complejidad del quechua. Estos resultados confirman el diagnóstico de la literatura sobre la escasez de datos como principal limitante de la calidad en lenguas de bajos recursos (Abdulmumin et al., 2025\) y matizan la expectativa de que una arquitectura de servicios robusta permita por sí sola resultados altamente precisos (Francisco, 2026\): la arquitectura garantiza la disponibilidad y el rendimiento del servicio, pero la precisión depende principalmente del modelo y de los datos con que fue ajustado. En el mismo sentido, la optimización del motor de inferencia multiplicó el throughput sin alterar de forma significativa el WER, y la ejecución en GPU produjo exactamente el mismo WER mediano sobre el corpus completo que la ejecución en CPU.

   2. ### **Hallazgos**

El aislamiento de fallos es el aporte más sólido de la arquitectura. La separación de responsabilidades limitó el impacto de la caída de cada servicio a una ventana de unos 5 s y, salvo en el caso del propio servicio de inferencia, a ninguna solicitud. Frente a ello, la caída del monolito interrumpió todo el servicio. Este resultado respalda empíricamente la decisión arquitectónica y el enfoque modular e interoperable propuesto para integrar servicios de inteligencia artificial (Tantaroudas et al., 2026).

La validación local del token eliminó el punto único de fallo identificado en la primera iteración. En la primera iteración, dos técnicas de evaluación independientes convergieron en que auth-service, consultado en cada solicitud, era un punto único de fallo y la causa oculta del deterioro bajo carga, enmascarada por errores 401. En la segunda iteración, la validación local del token llevó el éxito durante su caída al 100 %, y el contraste con la validación remota (42.9 %) atribuye la mejora a ese cambio.

La escalabilidad bajo sobrecarga requiere que el rechazo ocurra en el borde. El escalado horizontal de la primera iteración incrementó los usuarios atendidos en un 39 %, pero todas las configuraciones colapsaron. En la segunda iteración, un control de admisión ubicado solo al final de la cadena mejoró la capacidad, pero no evitó la degradación: el trabajo invertido en solicitudes que luego se rechazaban redujo el goodput a la tercera parte y produjo errores internos. Al trasladar la decisión a api-gateway, antes de procesar el audio, el goodput se mantuvo cerca de la capacidad, el tiempo de respuesta de las solicitudes admitidas cayó a menos de la cuarta parte y los errores internos desaparecieron. El hallazgo muestra que la ubicación del control de admisión importa tanto como su existencia.

Una cola asíncrona permite atender una demanda superior a la capacidad sin perder solicitudes. Ninguna arquitectura puede atender 1000 usuarios síncronos en un equipo sin GPU dentro de un tiempo de respuesta razonable, como muestra la cota de Little. Con la API asíncrona, la plataforma aceptó el 99.98 % de los trabajos y completó el 100 % de los aceptados, incluso ante la caída del servicio de inferencia. Con GPU, la misma modalidad completó los 25 151 trabajos enviados, sin pérdidas. El compromiso es el tiempo de espera, que crece con la demanda, por lo que la modalidad asíncrona es adecuada para la transcripción de archivos y no para la interacción en tiempo real.

La adaptación vertical funciona cuando observa la señal correcta y verifica su efecto. La justificación del proyecto planteaba que una distribución adaptativa de la carga permitiría ajustar proactivamente los recursos ante picos de uso y mantener una latencia mínima (Jin & Yang, 2025). En la primera iteración, el mecanismo basado en el uso de CPU no reaccionó, porque la saturación se manifestaba como encolamiento, en coherencia con la observación de que la eficacia de las reglas reactivas depende de elegir una métrica que refleje la saturación real del servicio (Lorido-Botran et al., 2014). Con la profundidad de la cola como señal, el mecanismo reaccionó en todas las repeticiones y casi duplicó el throughput. El periodo de prueba evitó además mantener una adaptación que no rendía, lo que resultó necesario porque el efecto de la cuantización varió entre equipos. Con GPU, el mecanismo reaccionó en unos 4 s, combinó el cambio de precisión con el aumento del tamaño de lote y, cuando el servicio arrancó en la CPU con una GPU disponible, trasladó la inferencia a la GPU sin reiniciar el servicio. La plataforma puede, por tanto, aprovechar el hardware que encuentre disponible sin intervención manual, aunque este traslado se observó solo en ausencia de transcripciones en curso.

La optimización del motor de inferencia es la palanca de rendimiento más eficaz sin GPU. El motor CTranslate2 con cuantización int8 y varias líneas en paralelo multiplicó por 2.7 el throughput de inferencia sin diferencia significativa de WER, y ese aumento se trasladó directamente a la capacidad de la plataforma, que pasó de 4 a 10 usuarios síncronos dentro del objetivo de servicio según la ley de Little.

Con GPU, el procesamiento por lotes es la técnica que más aporta. El paso de la CPU a la GPU triplicó el throughput de inferencia, la precisión fp16 lo llevó a 5.3 veces y el procesamiento por lotes a 8.8 veces, sin diferencia significativa de WER, con lo que se cumple el criterio C3.4. Este resultado justifica que el planificador de inferencia se haya diseñado para agrupar solicitudes, ya que es el componente que permite aprovechar el paralelismo de la GPU y el que explica la ventaja de la propuesta sobre el monolito incluso con carga baja. El beneficio de los lotes se agota en torno a ocho clips, lo que indica que, a partir de ese punto, la capacidad solo puede aumentar añadiendo más aceleradores o réplicas del servicio de inferencia.

La compresión del audio no degrada la calidad en streaming. La hipótesis de diseño original sostenía que el envío de audio comprimido produciría errores en la transcripción, razón por la cual la interfaz transmite audio PCM sin comprimir. Los resultados contradicen esa hipótesis para audio Opus bien formado: no hubo diferencias de WER ni de CER, mientras que la latencia se redujo en un 53.8 % y el volumen transmitido en un 71.7 %. Este hallazgo es relevante para la accesibilidad, ya que un menor volumen de datos favorece el uso de la plataforma en conexiones de baja capacidad.

   3. ### **Amenazas a la validez**

* **Generador de carga en el mismo equipo.** En la segunda iteración, Locust se ejecutó en el mismo equipo que la plataforma. Con 500 y 1000 usuarios, los reintentos inmediatos de las solicitudes rechazadas consumieron CPU compartida, por lo que el goodput medido en esos escalones es una cota inferior del que se obtendría con un generador independiente. Además, el proxy de puertos de Docker Desktop se saturó en el escalón de 1000 usuarios; entre corridas se esperó a que liberara sus conexiones, y una repetición contaminada por ese efecto se descartó y se repitió.
* **Generador de carga en el equipo con GPU.** En el equipo con GPU, Locust también se ejecutó en el mismo equipo que la plataforma y reenvió cada rechazo de inmediato, hasta unas 65 000 solicitudes en el escalón de 1000 usuarios. Por ello, el goodput de los escalones altos con GPU también debe interpretarse como una cota inferior.
* **Evaluación en dos equipos distintos.** Los resultados con GPU se obtuvieron en un equipo distinto del entorno local sin GPU. Las comparaciones entre ambos entornos (por ejemplo, el goodput con GPU frente al goodput en CPU) combinan el efecto de la GPU con las diferencias entre los equipos, por lo que deben leerse como órdenes de magnitud. Las comparaciones que sustentan los criterios, como la de C3.4 y la de la propuesta frente al monolito, se realizaron siempre dentro de un mismo equipo.
* **Alcance de la migración entre dispositivos.** El traslado de la inferencia de la CPU a la GPU se observó en las tres repeticiones, pero siempre durante el reposo, sin transcripciones en curso. No se evaluó el traslado con inferencias en curso.
* **Límite de admisión en la prueba comparativa con GPU.** El límite de admisión en el borde se calculó con la plataforma en su configuración normal, con adaptación a fp16. En la comparación con el monolito, con fp32 fija, ese límite resultó alto para la menor capacidad de esa configuración, y el percentil 95 de la propuesta superó los 10 s desde 100 usuarios. La comparación entre arquitecturas no se ve afectada, porque ambas usaron el mismo dispositivo y la misma precisión.
* **Motor de inferencia en GPU.** Con GPU solo se evaluó el motor transformers; el motor CTranslate2, seleccionado para la CPU, no se evaluó en la GPU.
* **Un único clip en las pruebas de carga.** Las pruebas de carga utilizan un clip representativo del corpus para que la carga sea comparable entre configuraciones; la variabilidad de duración se cubre en la evaluación sobre el corpus y en la muestra estratificada de las pruebas de rendimiento.
* **Control de calidad del motor optimizado.** La equivalencia de WER entre motores se verificó sobre la muestra estratificada de 30 clips; su confirmación sobre el corpus completo se encuentra en curso.
* **Corrección de un resultado de la primera iteración.** El 100 % de éxito reportado en la primera iteración para la caída de asr-service se debía a respuestas exitosas sin transcripción; los resultados de disponibilidad de la segunda iteración validan el contenido de cada respuesta.

# **CONCLUSIONES Y RECOMENDACIONES**

El desarrollo de una plataforma en línea que emplee una API REST y tecnología para el reconocimiento automático de voz, orientada al quechua, representa una contribución significativa a los esfuerzos por revitalizar digitalmente las lenguas nativas. La implementación de sistemas para el reconocimiento de la voz amplía las oportunidades de acceso, interacción y preservación del idioma mediante herramientas tecnológicas modernas que están al alcance de distintos grupos de usuarios. 

La investigación de estudios relacionados reveló que las tecnologías ASR en lenguas de escasos recursos se topan con barreras considerables, sobre todo a causa de la carencia de corpus lingüísticos, las disparidades dialectales y las restricciones en lo que respecta a la calidad de los datos para entrenamiento. No obstante, los progresos recientes en aprendizaje profundo y modelos multilingües han arrojado resultados alentadores para optimizar la eficiencia de estos sistemas. 

Asimismo, se infiere que la interoperabilidad, la escalabilidad y la reutilización del sistema en diferentes plataformas digitales, como las aplicaciones web y móviles, son favorecidas por el empleo de arquitecturas basadas en APIs REST y servicios web. Este método posibilita que se incorporen en el futuro funciones vinculadas con la traducción, la síntesis de voz o los recursos didácticos orientados a reforzar el idioma quechua. 

En lo que respecta a la evaluación del sistema, se resaltó la importancia de utilizar métricas técnicas y de desarrollo de software, considerando elementos como el rendimiento, la disponibilidad, el tiempo de reacción, la capacidad para escalar y la experiencia del usuario. Estos indicadores proporcionan un panorama más integral acerca de la calidad del sistema, y van más allá de las medidas tradicionales de precisión en el reconocimiento de voz. 

Para resumir, el estudio muestra que la incorporación de tecnologías de inteligencia artificial, metodologías ágiles y perspectivas centradas en la conservación cultural puede resultar en soluciones novedosas con un impacto educativo y social. La propuesta no solo se enfoca en la tecnología, sino que también promueve la inclusión digital y la valorización de las lenguas indígenas en situaciones contemporáneas.

# **REFERENCIAS BIBLIOGRÁFICAS**

Akindotuni, D. (2025). Resource Asymmetry in Multilingual NLP: A Comprehensive Review and Critique. Journal Of Computer And Communications, 13(07), 14-47. https\://doi.org/10.4236/jcc.2025.137002

Bhushan, S., Mishra, V. P., Rishiwal, V., Arunkumar, S., & Agarwal, U. (2025). Advancing Text-to-Speech Systems for Low-Resource Languages: Challenges, Innovations, and Future Directions. IEEE Access, 13, 155729-155758. [https\://doi.org/10.1109/access.2025.3605236](https://doi.org/10.1109/access.2025.3605236)

Bonafide Research. (2026, 4 mayo). Argentina Natural Language Processing Market Overview, 2030\. https\://www\.bonafideresearch.com/product/6505491322/argentina-natural-language-processing-market

Ebrahimi, A., Mager, M., Wiemerslage, A., Denisov, P., Oncevay, A., Liu, D., Koneru, S., Ugan, E. Y., Li, Z., Niehues, J., Romero, M., Torre, I. G., Alumäe, T., Kong, J., Polezhaev, S., Belousov, Y., Chen, W., Sullivan, P., Adebara, I., . . . Kann, K. (2023, 31 agosto). Findings of the Second AmericasNLP Competition on Speech-to-Text Translation. PMLR. [https\://proceedings.mlr.press/v220/ebrahimi23a.html](https://proceedings.mlr.press/v220/ebrahimi23a.html)

Ministerio de Cultura. (s. f.). Política Nacional de Lenguas Originarias, Tradición Oral e Interculturalidad al 2040 \- PNLOTI | Centro de Recursos Interculturales. https\://centroderecursos.cultura.pe/es/registrobibliografico/pol%C3%ADtica-nacional-de-lenguas-originarias-tradici%C3%B3n-oral-e-interculturalidad--0

Mosquera, M., Robles, M., Rodriguez, J., & Manrique, R. (2025). Improving Low-Resource Translation with Dictionary-Guided Fine-Tuning and RL: A Spanish-to-Wayuunaiki Study. arXiv (Cornell University). [https\://doi.org/10.48550/arxiv.2508.19481](https://doi.org/10.48550/arxiv.2508.19481)

Occhini, G., Tanaka-Ishii, K., Barford, A., Tikochinski, R., Hu, S., Reichart, R., Zhou, Y., Claus, H., Petti, U., Vulić, I., Debnath, R., & Korhonen, A. (2026, 12 febrero). Artificial intelligence is creating a new global linguistic hierarchy. arXiv.org. https\://arxiv.org/abs/2602.12018

OEI \- Organización de Estados Iberoamericanos. (2025, 14 noviembre). La OEI lanza aplicación móvil que fortalece el aprendizaje y uso del quechua-Collao \- Organización de Estados Iberoamericanos. Organización de Estados Iberoamericanos. https\://oei.int/oficinas/peru/noticias/la-oei-lanza-aplicacion-movil-que-fortalece-el-aprendizaje-y-uso-del-quechua-collao/

Ortega, J. E., Zevallos, R., & Carraro, F. (2026). Giving Voice to the Constitution: Low-Resource Text-to-Speech for Quechua and Spanish Using a Bilingual Legal Corpus. arXiv (Cornell University). https\://doi.org/10.48550/arxiv.2604.13288

Pacheco, L. L. (2025, 22 enero). Brechas lingüísticas en Internet: a propósito del Día Internacional de la Lengua Materna. Hiperderecho. [https\://hiperderecho.org/2024/02/brechas-linguisticas-en-internet-a-proposito-del-dia-internacional-de-la-lengua-materna/](https://hiperderecho.org/2024/02/brechas-linguisticas-en-internet-a-proposito-del-dia-internacional-de-la-lengua-materna/)

Papa Reo. (s. f.). https\://papareo.nz/

Rangel, J., & Kobayashi, N. (2024). Advancing NMT for Indigenous Languages: A Case Study on Yucatec Mayan and Chol. Proceedings Of The 4th Workshop On Natural Language Processing For Indigenous Languages Of The Americas (AmericasNLP 2024), 138-142. https\://doi.org/10.18653/v1/2024.americasnlp-1.16

Segibadm. (2024, 22 octubre). El 38,4 % de las lenguas indígenas de América Latina y Caribe se encuentran en peligro de desaparición. SEGIB. [https\://www\.segib.org/el-384-de-las-lenguas-indigenas-de-america-latina-y-caribe-se-encuentran-en-peligro-de-desaparicion/](https://www.segib.org/el-384-de-las-lenguas-indigenas-de-america-latina-y-caribe-se-encuentran-en-peligro-de-desaparicion/)

Tonja, A., Balouchzahi, F., Butt, S., Kolesnikova, O., Ceballos, H., Gelbukh, A., & Solorio, T. (2024). NLP Progress in Indigenous Latin American Languages. Proceedings Of The 2024 Conference Of The North American Chapter Of The Association For Computational Linguistics: Human Language Technologies (Volume 1: Long Papers), 6972-6987. https\://doi.org/10.18653/v1/2024.naacl-long.385

Unesco. (2023, 7 agosto). ¡El Decenio Internacional de las Lenguas Indígenas celebra el \#DíaDeLosPueblosIndígenas, \#IndigenousDay\! Unesco. [https\://www\.unesco.org/es/articles/el-decenio-internacional-de-las-lenguas-indigenas-celebra-el-diadelospueblosindigenas-indigenousday](https://www.unesco.org/es/articles/el-decenio-internacional-de-las-lenguas-indigenas-celebra-el-diadelospueblosindigenas-indigenousday)
