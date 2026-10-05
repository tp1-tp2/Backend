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
   
El servicio incorpora además un mecanismo de adaptación vertical de recursos que, cada 20 segundos, evalúa el estado del hardware y decide el dispositivo de ejecución entre CPU o GPU. Para evitar cambios constantes provocados por lecturas puntuales, una decisión solo se aplica si se repite en tres sondeos consecutivos y si han transcurrido al menos 60 segundos desde el último cambio. El nuevo modelo se construye en segundo plano y solo reemplaza al anterior cuando está listo, de modo que las inferencias en curso no se interrumpen. Cada transcripción registra el dispositivo y la precisión con que fue procesada, y el mecanismo expone un endpoint de estado con el historial de sus decisiones, lo que permite observar su comportamiento durante la evaluación.  
   
Antes de ejecutar las mediciones se verifica que el artefacto opere de extremo a extremo en condiciones reales. Siguiendo la distinción entre niveles de prueba de la norma ISO/IEC/IEEE 29119, la verificación comprende pruebas de integración contra la pila completa en ejecución y pruebas de sistema de los flujos principales. El objetivo de esta etapa no es validar atributos de calidad, sino asegurar que los atributos medidos posteriormente correspondan a un artefacto que funciona según su diseño.  
   
Respecto a la línea base monolítica, que sirve para aislar el efecto de la decisión arquitectónica se construye una versión monolítica de control que reúne en un único proceso la lógica de autenticación, registro, procesamiento de audio, inferencia y persistencia, reutilizando el mismo código funcional de los servicios originales. En esta versión, las tres llamadas HTTP que la arquitectura propuesta realiza entre audio-processor, asr-service y transcription-manager se reemplazan por llamadas directas a funciones dentro del mismo proceso. El monolito expone las mismas rutas públicas que la plataforma, utiliza un dispositivo de ejecución fijo sin mecanismo de adaptación y dispone de una base de datos propia.  
   
La evaluación se realiza en dos entornos de ejecución. El primero es un entorno local basado en Docker Compose, en el que se despliegan todos los contenedores de la plataforma y de la línea base sobre el mismo hardware (\[especificar procesador, número de núcleos y memoria RAM del equipo\]). El segundo es Azure Container Apps en el plan de consumo, sin disponibilidad de GPU, con réplicas de asr-service de 2 vCPU y un servidor PostgreSQL flexible de tipo Standard\_B1ms compartido por las bases de datos de los servicios. Esta combinación responde al marco de evaluación propuesto por Venable et al. (2016), que distingue entre evaluaciones artificiales, en las que el investigador controla las condiciones, y evaluaciones cercanas al uso real del artefacto. Las comparaciones controladas entre arquitecturas y la inyección de fallos se realizan en el entorno local, donde es posible garantizar condiciones idénticas para ambas versiones, mientras que la prueba de escalabilidad se realiza en Azure, con lo que se atiende la exigencia del OE4 de evaluar el funcionamiento en entornos reales.

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

Los diseños se presentan en el orden de las dimensiones de la variable dependiente: primero los indicadores de accesibilidad (disponibilidad y escalabilidad) y luego los de interacción (rendimiento, calidad de reconocimiento y usabilidad).

1. #### **Disponibilidad**

La disponibilidad se evalúa principalmente mediante la prueba de inyección de fallos. Que consiste en provocar fallos de forma deliberada mientras el sistema atiende carga realista para observar su comportamiento, en lugar de suponer su resiliencia a partir del diseño (Basiri et al., 2016).  
   
El procedimiento es el siguiente. Con aproximadamente 50 usuarios concurrentes ejecutando de forma continua el flujo de inicio de sesión y transcripción, y tras un periodo de calentamiento de 30 segundos, se detiene un contenedor por vez. En la arquitectura propuesta se detienen tres servicios representativos del camino crítico de una transcripción: asr-service (inferencia), auth-service (autenticación) y transcription-manager (persistencia). En la línea base se detiene el proceso monolítico completo. Durante cada caída se registran las solicitudes totales y fallidas dirigidas al endpoint de transcripción, se consulta el endpoint de salud de cada servicio cada segundo para medir el tiempo de detección y se observa si la caída degrada a los servicios vecinos.  
   
De forma complementaria, la tasa de éxito bajo carga se obtiene de la prueba de carga progresiva en la nube, cuyo diseño se describe en el apartado siguiente.

2. #### **Escalabilidad**

La escalabilidad se evalúa mediante la prueba de carga progresiva en la nube, sobre Azure Container Apps. Se registran previamente 30 usuarios de prueba y se aplica con Locust una rampa de carga de seis escalones de 180 segundos cada uno, con objetivos de 10, 50, 100, 200, 500 y 1000 usuarios concurrentes, en los que cada usuario simulado ejecuta de forma repetida el flujo de inicio de sesión y transcripción de audio real del corpus.  
   
La prueba se diseña de forma iterativa, coherente con los ciclos de construcción y evaluación propios de la ciencia del diseño (Hevner et al., 2004). La primera ejecución se realiza con una configuración fija de una, que sirve como referencia. Cada configuración posterior se define a partir del análisis del resultado anterior, se identifica el componente que limita la capacidad, se formula una hipótesis sobre su causa y se aplica el cambio de configuración correspondiente, de modo que cada ejecución pone a prueba la hipótesis de la anterior.  
   
El escalado horizontal se configura mediante reglas basadas en la concurrencia de solicitudes HTTP por réplica y no en el porcentaje de uso de CPU. Esta elección responde a que asr-service opera con un único worker, por lo que puede acumular solicitudes en espera mientras su uso de CPU todavía es moderado; una regla basada en CPU reaccionaría tarde ante ese encolamiento. Las reglas reactivas basadas en umbrales son la técnica de autoescalado más extendida en plataformas en la nube por su simplicidad, aunque su eficacia depende de elegir una métrica que refleje la saturación real del servicio (Lorido-Botran et al., 2014). El umbral de cada servicio se fija según su capacidad de atender solicitudes simultáneas: un umbral bajo para servicios de un único worker con operaciones de varios segundos, como la inferencia, y un umbral más alto para servicios de cuatro workers con operaciones breves.  
   
Durante cada ejecución se observa además el mecanismo de adaptación vertical mediante su endpoint de estado y sus registros estructurados, con el fin de determinar si reacciona ante la presión de carga.

3. #### **Rendimiento**

El rendimiento se evalúa con tres fuentes de evidencia complementarias:  
 

* **Costo de inferencia**. En la evaluación de reconocimiento sobre el corpus se mide el RTF de cada uno de los 2111 clips, ejecutados en CPU con precisión fp32.  
* **Tiempo de respuesta bajo carga**. En la prueba de carga comparativa se aplica la misma rampa contra la arquitectura propuesta y contra la línea base monolítica, en el entorno local y sobre el mismo hardware, y se comparan los percentiles 50, 95 y 99 del tiempo de respuesta y el throughput. El tiempo de respuesta en la nube se obtiene de los primeros escalones de la prueba de carga progresiva.  
* **Latencia de streaming**. En la prueba comparativa de codificación se transmite por WebSocket una muestra estratificada de 30 clips especificamente 20 de Huqariq y 10 de Siminchik, en proporción al tamaño de cada fuente. Cada clip se envía una vez como audio PCM sin comprimir y otra como audio comprimido en Opus, y se registran la latencia hasta el resultado final y el volumen de bytes transmitidos. Para la condición Opus, cada clip se codifica completo con ffmpeg y luego se fragmenta para su transmisión.

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

Los criterios de aceptación establecen, para cada dimensión, el umbral a partir del cual el resultado se considera satisfactorio. La Tabla X los presenta junto con su fundamento.

Tabla X. Criterios de aceptación por dimensión.

| Código | Dimensión | Criterio | Fundamento |
| ----- | ----- | ----- | ----- |
| C1.1 | Disponibilidad | Ante la caída de un servicio individual, la tasa de éxito es superior a la del monolito en la misma condición y ninguna caída afecta al 100 % de las solicitudes | Principio de aislamiento de fallos de la arquitectura de microservicios |
| C1.2 | Disponibilidad | El tiempo de detección de una caída es menor o igual a 5 s | Intervalo de monitoreo de salud de 1 s |
| C1.3 | Disponibilidad | La caída de un servicio no se propaga a sus servicios vecinos | Principio de aislamiento de fallos |
| C1.4 | Disponibilidad | La tasa de éxito bajo carga es mayor o igual a 95 % en todos los escalones de la rampa | Criterio definido por el equipo |
| C2.1 | Escalabilidad | El escalado horizontal incrementa el número de usuarios concurrentes sostenidos respecto de la configuración fija | Propósito del escalado horizontal |
| C2.2 | Escalabilidad | La plataforma sostiene el escalón objetivo máximo de la rampa (1000 usuarios) | Criterio definido por el equipo |
| C2.3 | Escalabilidad | El mecanismo de adaptación vertical registra al menos una decisión de cambio ante la presión de carga | Diseño del mecanismo de adaptación |
| C3.1 | Rendimiento | El RTF mediano es menor que 1 | Transcripción más rápida que el tiempo real |
| C3.2 | Rendimiento | El tiempo de respuesta mediano en carga baja en la nube es menor o igual a 10 s | Límite de atención del usuario (Nielsen, 1993\) |
| C3.3 | Rendimiento | La arquitectura propuesta no presenta tiempos de respuesta significativamente mayores que el monolito | Comparación con la línea base |
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

El protocolo se ejecutó en los dos entornos planificados. La verificación previa se realizó en el entorno local, con la pila completa de la plataforma y de la línea base desplegada mediante Docker Compose, y las ejecuciones de la prueba de carga progresiva en Azure Container Apps. Todos los contenedores alcanzaron un estado saludable, y los flujos de registro, inicio de sesión, transcripción, persistencia y consulta funcionaron correctamente en ambas arquitecturas. A modo de ejemplo, la transcripción de un clip real del corpus produjo el texto "wañuchisunchu kay suwakunata", idéntico a su referencia, tanto en la plataforma como en la línea base. Se confirmó también que la precisión de cómputo de cada transcripción quedó registrada en la base de datos, y las pruebas de integración contra la pila en ejecución se superaron en su totalidad.  
   
Durante la verificación se detectaron y corrigieron cuatro errores que no eran observables mediante pruebas con dependencias simuladas. El primero fue una incompatibilidad de versiones entre las librerías transformers y torch que impedía cargar el modelo, corregida fijando versiones compatibles. El segundo y el tercero correspondieron a diferencias entre las respuestas reales de los servicios y las esperadas por el cliente de medición el código de error ante un correo ya registrado y la forma de la respuesta de la solicitud de transcripción, que en la plataforma no incluye el tiempo de procesamiento y obliga a consultar el registro completo de la transcripción. Sin esta última corrección, el cálculo de RTF y WER habría producido valores inválidos. El cuarto fue un dominio de correo de prueba rechazado por la validación de datos, reemplazado por un dominio reservado para documentación.

1. #### **Síntesis de métricas frente a los criterios de aceptación**

La siguiente tabla resume el resultado de cada criterio de aceptación. El detalle de cada dimensión se presenta en los apartados siguientes.

Tabla X. Resultados frente a los criterios de aceptación.

| Código | Resultado obtenido | Estado |
| ----- | ----- | ----- |
| C1.1 | Tasa de éxito entre 34.7 % y 100 % según el servicio detenido, frente a 6.7 % del monolito | Cumple |
| C1.2 | Detección entre 3.4 s y 3.5 s | Cumple |
| C1.3 | Ninguna caída se propagó a servicios vecinos | Cumple |
| C1.4 | Tasa de éxito en el escalón final entre 0 % y 14.4 % según la configuración | No cumple |
| C2.1 | Incremento de 254 a 353 usuarios sostenidos (39.0 %) | Cumple |
| C2.2 | Máximo de 353 usuarios sostenidos frente a un objetivo de 1000 | No cumple |
| C2.3 | El mecanismo de adaptación vertical no registró decisiones de cambio | No cumple |
| C3.1 | RTF mediano de 0.149 | Cumple |
| C3.2 | Tiempo de respuesta mediano de 4.7 s con 10 usuarios concurrentes | Cumple |
| C3.3 | Percentil 50 significativamente menor en la arquitectura propuesta; percentiles 95 y 99 sin diferencia significativa | Cumple |
| C4.1 | 0 transcripciones vacías | Cumple |
| C4.2 | 0.6 % de clips con WER superior a 1.5 | Cumple |
| C4.3 | Sin diferencia significativa en WER (p \= 0.6716) ni en CER (p \= 0.9703) | Cumple |
| C4.4 | WER mediano de 0.697 | En proceso |
| C5.1 | \[Pendiente\] | Pendiente |
| C5.2 | \[Pendiente\] | Pendiente |

2. #### **Disponibilidad**

La prueba de inyección de fallos se ejecutó en el entorno local según el procedimiento planificado, con aproximadamente 50 usuarios concurrentes ejecutando el flujo de inicio de sesión y transcripción. Se detuvieron por separado asr-service, auth-service y transcription-manager, y en una ejecución independiente se detuvo el proceso de la línea base monolítica. La detención se realizó mediante una parada ordenada del contenedor. Este método no activa la política de reinicio configurada en los servicios, que solo actúa ante terminaciones con error, por lo que la recuperación automática no pudo evaluarse con este procedimiento.

La siguiente tabla presenta el impacto de la caída de cada servicio sobre las solicitudes de transcripción.

Tabla X. Impacto de la caída de servicios sobre las solicitudes de transcripción.

| Servicio detenido | Solicitudes totales | Solicitudes fallidas | Tasa de fallas | Tasa de éxito |
| ----- | ----- | ----- | ----- | ----- |
| asr-service | 437 | 0 | 0.0 % | 100.0 % |
| auth-service | 539 | 352 | 65.3 % | 34.7 % |
| transcription-manager | 238 | 0 | 0.0 % | 100.0 % |
| Monolito (proceso completo) | 1160 | 1082 | 93.3 % | 6.7 % |

La caída de asr-service no produjo fallas, las solicitudes en curso quedaron en espera, con tiempos de hasta 81 s, y se completaron cuando el servicio volvió a estar disponible. La caída de transcription-manager tampoco produjo fallas, debido a que el diseño trata la persistencia como una operación no crítica, de modo que el cliente recibe su transcripción aunque esta no se almacene. En cambio, la caída de auth-service afectó al 65.3 % de las solicitudes, porque api-gateway valida el token de cada solicitud autenticada contra este servicio, lo que lo sitúa en el camino crítico de todo el tráfico y no solo del inicio de sesión. En la línea base, la detención del proceso afectó al 93.3 % de las solicitudes de transcripción e incluso al 12 % de los inicios de sesión, ya que todos los componentes comparten el mismo proceso.  
La siguiente tabla presenta los tiempos de detección y la propagación observada.

Tabla X. Detección y propagación de fallos.

| Servicio detenido | Tiempo de detección | Propagación a servicios vecinos |
| ----- | ----- | ----- |
| asr-service | 3.4 s | No |
| auth-service | 3.5 s | No |
| transcription-manager | 3.5 s | No |
| Monolito | 3.7 s | No aplica |

En cuanto a la disponibilidad bajo carga, obtenida de la prueba de carga progresiva en la nube, la tasa de éxito en el escalón final de la rampa se ubicó entre 0 % y 14.4 % en las cuatro configuraciones ejecutadas, es decir, ninguna configuración mantuvo la disponibilidad del servicio en los escalones de carga extrema. El detalle por configuración se presenta en el apartado siguiente.

3. #### **Escalabilidad**

La prueba de carga progresiva se ejecutó en cuatro rondas sobre Azure Container Apps, una por configuración, siguiendo el diseño iterativo planificado. La siguiente tabla presenta cada configuración y la hipótesis que motivó su definición.

Tabla X. Configuraciones de escalado ejecutadas.

| Ronda | Configuración | Hipótesis que la motivó |
| ----- | ----- | ----- |
| 1 | Una réplica fija por servicio, sin autoescalado | Configuración de referencia |
| 2 | Autoescalado de asr-service, con umbral de 2 solicitudes concurrentes | En la ronda 1, asr-service, con un único worker, aparecía como el cuello de botella |
| 3 | Configuración de la ronda 2 con el modelo precargado en la imagen del contenedor | Las réplicas nuevas no alcanzaban a estar listas dentro de cada escalón, porque descargaban el modelo de aproximadamente 279 MB en cada arranque |
| 4 | Configuración de la ronda 3 con autoescalado de auth-service, con umbral de 10 solicitudes concurrentes | La ronda 3 mostró errores de autenticación masivos atribuibles a la saturación de auth-service |

La siguiente tabla presenta los resultados de las cuatro rondas en su escalón final.  
   
Tabla X. Resultados de escalabilidad por configuración.

| Ronda | Configuración | Usuarios concurrentes sostenidos | Tasa de error en el escalón final | Percentil 99 del tiempo de respuesta |
| ----- | ----- | ----- | ----- | ----- |
| 1 | Sin autoescalado | 254 | 96.9 % a 100 % | 68 s a 81 s aprox. |
| 2 | Autoescalado de asr-service | 307 | 85.6 % | 81 s aprox. |
| 3 | Ronda 2 más modelo precargado en la imagen | 244 | 97.1 % a 100 % | 67 s aprox. |
| 4 | Ronda 3 más autoescalado de auth-service | 353 | 85.9 % a 100 % | 149 s |

El autoescalado de asr-service incrementó el número de usuarios concurrentes sostenidos de 254 a 307 (20.9 %), y la incorporación del autoescalado de auth-service lo elevó a 353, un 39.0 % más que la configuración sin autoescalado. Sin embargo, ninguna configuración redujo la tasa de error del escalón final por debajo de aproximadamente 85 %, de modo que todas terminaron colapsando ante la carga extrema.  
   
La ronda 3 obtuvo un resultado inferior al de la ronda 2 pese a incorporar una mejora en el tiempo de arranque. El análisis de los registros de fallas mostró 2652 errores de autenticación (código 401\) en el endpoint de transcripción, inexistentes en la ronda 2\. La revisión del código de api-gateway explicó el origen, cualquier respuesta de auth-service distinta de una validación exitosa, incluidos los errores 500, 502 y 504 producidos por sobrecarga, se traduce en un error 401 para el cliente, lo que ocultaba que la causa real era la saturación de auth-service, que operaba con una única réplica fija. Tras autoescalar este servicio en la ronda 4, los errores 401 disminuyeron a 235, una reducción del 91.1 %, y se alcanzó el mayor número de usuarios sostenidos de la serie. En contrapartida, el percentil 99 del tiempo de respuesta aumentó a 149s la plataforma admitió más tráfico, pero lo hizo esperar más tiempo antes de fallar.  
   
Durante las cuatro rondas, el mecanismo de adaptación vertical no registró ninguna decisión de cambio de precisión. Su señal de decisión, el porcentaje de uso de CPU, no detecta el encolamiento de solicitudes frente a un único worker, que es precisamente la forma en que se manifestó la saturación de asr-service.

4. #### **Rendimiento**

La evaluación de reconocimiento procesó los 2111 clips del corpus en CPU con precisión fp32. La prueba de carga comparativa se ejecutó en el entorno local con la misma rampa contra ambas arquitecturas, sobre el mismo hardware. La prueba comparativa de codificación se ejecutó con la muestra de 30 clips y tres repeticiones por condición, lo que dio 90 sesiones por condición. Durante su ejecución se detectó un error en el servicio de decodificación la conversión con ffmpeg no especificaba la frecuencia de muestreo de salida, por lo que el audio Opus, codificado internamente a 48 kHz, llegaba al modelo sin remuestrear a 16 kHz y la sesión quedaba sin respuesta. El error se corrigió agregando la frecuencia de 16 kHz a la conversión antes de obtener los resultados reportados.

El RTF mediano sobre el corpus fue de 0.149, con un rango intercuartílico de 0.120 a 0.201. Por fuente, el RTF mediano fue de 0.135 en Huqariq y de 0.183 en Siminchik. En términos prácticos, la plataforma procesa un clip de 10 s en aproximadamente 1.5 s de cómputo. En la nube, con 10 usuarios concurrentes y sin autoescalado, el tiempo de respuesta mediano fue de 4.7 s.  
 La siguiente tabla presenta los resultados de la prueba de carga comparativa.  
   
Tabla X. Tiempo de respuesta y throughput de arquitectura propuesta frente a monolito.

| Métrica | Propuesta (media) | Monolito (media) | Prueba | Valor p | Delta de Cliff | Magnitud | Significativo |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| Percentil 50 (ms) | 16 787.4 | 24 882.3 | U de Mann-Whitney | \< 0.001 | \-0.579 | Grande | Sí |
| Percentil 95 (ms) | 69 787.4 | 54 082.9 | U de Mann-Whitney | 0.9929 | 0.000 | Despreciable | No |
| Percentil 99 (ms) | 82 581.9 | 57 364.3 | U de Mann-Whitney | 0.2599 | 0.028 | Despreciable | No |
| Throughput (req/s) | 2.8 | 4.2 | U de Mann-Whitney | 0.3933 | 0.021 | Despreciable | No |

La arquitectura propuesta obtuvo un percentil 50 un 32.5 % menor que el del monolito, con una diferencia estadísticamente significativa y un tamaño de efecto grande. En los percentiles 95 y 99 y en el throughput, las diferencias no fueron significativas y los tamaños de efecto fueron despreciables, aunque los valores medios del monolito fueron numéricamente menores en esos indicadores. Cabe precisar que los valores medios de la tabla agregan todos los escalones de la rampa, incluidos los de carga extrema, por lo que no representan el tiempo de respuesta en condiciones normales de uso.  
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

Los resultados se contrastan con tres referentes la línea base monolítica, el estado del arte del reconocimiento de voz para quechua y lenguas de bajos recursos, y los criterios de aceptación del protocolo.  
   
Sobre la línea base monolítica, la comparación ofrece su evidencia más sólida en la dimensión de disponibilidad. Ante la caída de un componente, la arquitectura propuesta conservó entre el 34.7 % y el 100 % de las solicitudes exitosas, mientras que el monolito conservó solo el 6.7 %. En rendimiento, la arquitectura propuesta redujo el percentil 50 del tiempo de respuesta en un 32.5 % con un efecto grande, lo que es consistente con su diseño el monolito serializa autenticación, conversión de audio e inferencia en un único worker, mientras que la propuesta solo serializa la inferencia y ejecuta la autenticación y el procesamiento de audio en servicios con cuatro workers. Sin embargo, la ventaja no se extiende a los percentiles 95 y 99 ni al throughput, donde no hubo diferencias significativas. Este patrón coincide con lo señalado por Dean y Barroso (2013) mencionando que a medida que una solicitud atraviesa más componentes, la cola de la distribución de tiempos tiende a crecer, de modo que la separación en servicios mejora la experiencia típica sin garantizar una mejora en los peores casos. Villamizar et al. (2015) también evaluaron ambos patrones en despliegues en la nube y advirtieron que los beneficios de los microservicios dependen del contexto de carga y de la configuración de la infraestructura, lo que resulta coherente con que la ventaja observada aquí sea parcial y no absoluta.  
   
Sobre el estado del arte, El WER mediano de 0.697 es elevado en términos absolutos, pero debe interpretarse considerando dos factores. Primero, se evitó deliberadamente evaluar con corpus que probablemente se solapan con los datos de entrenamiento del modelo, lo que produce una estimación más conservadora y realista que la que se obtendría con datos contaminados. Segundo, el CER mediano de 0.172 indica que el modelo reconoce correctamente la mayor parte de los caracteres, y que una proporción considerable de los errores por palabra corresponde a diferencias parciales dentro de palabras largas, lo que es consistente con la alta complejidad del quechua. Estos resultados confirman el diagnóstico de la literatura sobre la escasez de datos como principal limitante de la calidad en lenguas de bajos recursos (Abdulmumin et al., 2025\) y matizan la expectativa de que una arquitectura de servicios robusta permita por sí sola resultados altamente precisos (Francisco, 2026\) la arquitectura garantiza la disponibilidad y el rendimiento del servicio, pero la precisión depende principalmente del modelo y de los datos con que fue ajustado.  
 

2. ### **Hallazgos**

El aislamiento de fallos es el aporte más sólido de la arquitectura. La separación de responsabilidades limitó el impacto de la caída de un servicio a entre 0 % y 65.3 % del tráfico, nunca al sistema completo, frente al 93.3 % del monolito. Este resultado respalda empíricamente la decisión arquitectónica y el enfoque modular e interoperable propuesto para integrar servicios de inteligencia artificial (Tantaroudas et al., 2026).  
El servicio auth-service es un punto único de fallo en el camino crítico. Dos técnicas de evaluación independientes convergen en este hallazgo. En la inyección de fallos, la caída de auth-service fue la única que afectó de forma significativa a las transcripciones, y en la prueba de carga progresiva, su saturación fue la causa real del deterioro observado en la ronda 3, oculta tras errores 401 que aparentaban ser problemas de credenciales. El hallazgo muestra que el servicio con mayor carga computacional, asr-service, no era necesariamente el cuello de botella, y que identificar el límite real requirió instrumentación y análisis de registros. Asimismo, evidencia que la forma en que api-gateway traduce los errores de un servicio dependiente puede ocultar la causa de una falla.  
   
El escalado horizontal mejora la capacidad, pero no resuelve la escalabilidad. El autoescalado incrementó en un 39.0 % el número de usuarios concurrentes sostenidos, pero todas las configuraciones colapsaron ante la carga extrema. Además, la mejora de la ronda 4 se obtuvo a costa de un percentil 99 de 149 s, lo que indica que el sistema pasó de fallar rápidamente a hacer esperar a los usuarios antes de fallar.  
   
La adaptación vertical no reaccionó ante la carga real. La justificación del proyecto planteaba que una distribución adaptativa de la carga permitiría ajustar proactivamente los recursos ante picos de uso y mantener una latencia mínima (Jin & Yang, 2025). Los resultados muestran que el mecanismo de adaptación vertical, basado en el porcentaje de uso de CPU, no registró ninguna decisión durante la prueba de carga, porque la saturación se manifestó como encolamiento de solicitudes y no como un uso elevado de CPU. Este resultado es consistente con la observación de que la eficacia de las reglas reactivas depende de elegir una métrica que refleje la saturación real del servicio (Lorido-Botran et al., 2014), y respalda la decisión de configurar el escalado horizontal sobre la concurrencia de solicitudes. La adaptación efectiva de la plataforma provino, por tanto, del escalado horizontal y no del mecanismo vertical.  
   
La compresión del audio no degrada la calidad en streaming. La hipótesis de diseño original sostenía que el envío de audio comprimido produciría errores en la transcripción, razón por la cual la interfaz transmite audio PCM sin comprimir. Los resultados contradicen esa hipótesis para audio Opus bien formado no hubo diferencias de WER ni de CER, mientras que la latencia se redujo en un 53.8 % y el volumen transmitido en un 71.7 %. Este hallazgo es relevante para la accesibilidad, ya que un menor volumen de datos favorece el uso de la plataforma en conexiones de baja capacidad.  
   
La plataforma responde en tiempos adecuados en condiciones normales, pero no en los extremos. Con un RTF mediano de 0.149 y un tiempo de respuesta mediano de 4.7 s con 10 usuarios concurrentes en la nube, la plataforma se encuentra dentro del límite de atención del usuario en condiciones de carga baja (Nielsen, 1993). Esta ventaja se pierde a medida que la carga crece, lo que refuerza la necesidad de distinguir entre el rendimiento típico y el rendimiento bajo saturación al interpretar los resultados.

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
