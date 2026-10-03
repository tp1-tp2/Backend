### 1.2.2 Análisis de Problema 

A nivel nacional, Perú se distingue por una profunda riqueza multilingüe. El Censo Nacional de 2017 reveló que más de cuatro millones de personas, lo que representa el 16.3% de la población del país, tienen como lengua materna una lengua originaria. De esta cifra, el quechua es la lengua nativa más hablada, con 3 millones de quechuahablantes, lo que representa aproximadamente el 14% de la población peruana. Le siguen en número el aimara y las diversas lenguas de la Amazonía. Los estudiosos consideran al quechua una lengua vital, pero alertan que muchas de sus variedades se encuentran hoy en peligro de desaparecer por la indiferencia que existe en el trabajo por mantenerla vigente (Etoscano, 2021). 

El desarrollo de sistemas de ASR modernos depende fundamentalmente de la disponibilidad de grandes volúmenes de datos de audio transcritos para el aprendizaje supervisado. Mientras que los idiomas con alto retorno de inversión (ROI) como el inglés y el español, cuentan con miles de horas de datos, el quechua es clasificado como una lengua de bajos recursos (low-resource language). La escasez de corpus de datos a escala es el mayor obstáculo para que las tecnologías de voz alcancen una calidad de grado comercial (Abdulmumin et al., 2025). Los sistemas globales disponibles en la web, como Whisper o Google, presentan tasas de error significativamente más altas en quechua o simplemente no ofrecen soporte oficial, relegando la tecnología a entornos de laboratorio académico (Akhulkova, 2025). 

Actualmente se puede identificar una jerarquía lingüística global creada por la Inteligencia Artificial, donde la inversión se concentra en un grupo especifico de lenguas (Occhini et al., 2026). Las grandes empresas tecnológicas priorizan mercados con alta capacidad económica, dejando a los hablantes de lenguas indígenas en una situación de "muerte lingüística digital", donde su exclusión de los ecosistemas digitales acelera la desaparición del idioma (Akindotuni, 2025). En regiones como Argentina y Perú, aunque hay un auge de la IA en sectores como el bancario o educativo, el soporte para el quechua sigue siendo exploratorio o inexistente en las interfaces web de uso masivo (Bonafide Research, 2026).

### 1.2.4 Formulación del Problema 

**¿Cómo puede plataforma web con servicios de reconocimiento automático de voz (ASR) para el quechua, mejorar la accesibilidad e interacción en quechua dentro de aplicaciones digitales, en el contexto de los esfuerzos de revitalización lingüística en el Perú?**

La implementación de una plataforma web de reconocimiento automático de voz (ASR) para el quechua se considera una solución adecuada dado que las lenguas indígenas suelen ser invisibles y no escuchadas en el mundo digital debido a la falta de suficientes conjuntos de datos necesarios para el aprendizaje automático. Esta carencia impide que los hablantes de lenguas minoritarias interactúen con la tecnología mediante la voz, lo que profundiza su marginación y limita su participación en la sociedad digital actual (Papa Reo, s. f.). 

El uso de un marco de trabajo modular e interoperable permitiría integrar servicios de IA como la transcripción de voz a texto y la traducción multilingüe de manera flexible y escalable. Este diseño facilita que la tecnología se adapte a diversos contextos educativos y sociales, permitiendo que las herramientas de reconocimiento de voz no funcionen de forma aislada, sino como parte de una experiencia educativa y comunicativa integral (Tantaroudas et al., 2026). 

A su vez, en la revista Languages se revisan sistemáticamente los avances del ASR en la adquisición de segundas lenguas. El estudio concluye que las herramientas de aprendizaje cada vez integran más modelos de reconocimiento de voz y síntesis de voz. Farrús observa que “muchos de estos sistemas incluyen o se basan en [tecnologías de] texto a voz, traducción o reconocimiento automáticos de voz (ASR)” y que su uso ha crecido en la última década, pues los ASR modernos son capaces de reconocer tanto el contenido verbal del usuario como sus características fonéticas Farrús (2023).  

Contar con una plataforma web dedicada soluciona el problema de la baja disponibilidad al ofrecer una solución de mayor precisión, evitando la frustración del usuario por errores de transcripción comunes en modelos de propósito general. La elección de una arquitectura de servicios robusta permite que las aplicaciones de voz entreguen resultados altamente precisos incluso en condiciones de ruido o con diferentes dialectos (Francisco, 2026). 

La estabilidad y la disponibilidad continua del servicio mediante la aplicación de estrategias avanzadas de optimización de escalabilidad en la nube, nos permitirá superar las limitaciones de los métodos tradicionales de gestión de recursos que suelen presentar retrasos ante fluctuaciones de carga repentinas. Al integrar un enfoque para la distribución adaptativa de la carga la plataforma puede anticipar picos de uso y ajustar proactivamente sus recursos. Este nivel de optimización técnica asegura que el sistema mantenga una utilización de recursos estable y una latencia mínima (Jin & Yang, 2025), permitiendo que el reconocimiento de voz en quechua sea una herramienta fiable y de alto rendimiento incluso en escenarios de alta concurrencia digital. 

Finalmente, la integración de infraestructuras escalables y automáticas garantiza que la actualización y la ejecución de estos modelos, como el ASR, sean económicamente viables y rápidos (Ali et al., 2022). Esto permite que la plataforma gestione demandas de recursos, asegurando que el servicio esté disponible en tiempo real sin incurrir en costes prohibitivos para las comunidades que requieren el uso de estas tecnologías para incentivar el uso del quechua en entornos digitales.

## 1.3 OBJETIVOS 

### 1.3.1 Objetivo General 

OG: Desarrollar una plataforma web basada en servicios de reconocimiento automático de voz (ASR) que permita la integración del quechua en aplicaciones web y móviles, contribuyendo a los esfuerzos de revitalización lingüística en entornos digitales del Perú. 

### 1.3.2 Objetivos Específicos 

- OE1: Analizar el estado del arte de los sistemas de reconocimiento automático de voz (ASR) orientados a lenguas de bajos recursos para identificar limitaciones, oportunidades y criterios de selección de modelos ASR preentrenados, mediante la revisión de servicios web, APIs y propuestas tecnológicas relacionadas con reconocimiento de voz en quechua y otros idiomas indígenas.  

- OE2: Diseñar la arquitectura de microservicios de una plataforma web basada en servicios para permitir la integración escalable de funcionalidades de reconocimiento automático de voz en aplicaciones web y móviles, mediante la definición de componentes, interfaces, mecanismos de comunicación y estrategias de contenerización y almacenamiento asociadas al módulo ASR. 

- OE3: Desarrollar los servicios y componentes funcionales de la plataforma web propuesta para exponer el reconocimiento automático de voz en quechua como un servicio interoperable y accesible, mediante la integración y contenerización de un modelo ASR preentrenado, el desarrollo de APIs de comunicación (REST) y una interfaz de usuario para entornos web.   

- OE4: Validar el desempeño y la calidad de la plataforma web basada en servicios para determinar su capacidad de procesamiento y funcionamiento en entornos reales, mediante la evaluación de métricas de ingeniería de software como latencia, tiempo de respuesta, disponibilidad, escalabilidad y usabilidad en solicitudes de reconocimiento de voz en quechua. 

## 1.4 PROPUESTA DE SOLUCIÓN 

La propuesta de solución consiste en el desarrollo de una plataforma web basada en servicios de reconocimiento automático de voz (ASR) en quechua, orientada a apoyar los esfuerzos de revitalización digital de la lengua mediante su disponibilidad en entornos tecnológicos accesibles e integrables. 

La plataforma será desplegada en infraestructura en la nube y estará compuesta por una arquitectura basada en servicios desacoplados, permitiendo la separación de responsabilidades entre los componentes de procesamiento, acceso y presentación. La solución tendrá como núcleo un módulo ASR encargado de procesar entradas de audio en lengua quechua y generar transcripciones de texto mediante la integración de un modelo de reconocimiento de voz. 

El sistema expondrá funcionalidades mediante servicios web accesibles a través de una API documentada con Swagger/OpenAPI, facilitando su consumo por parte de desarrolladores y la integración con aplicaciones externas. Asimismo, contará con una interfaz web que permitirá a usuarios no técnicos interactuar directamente con el sistema, realizar pruebas de reconocimiento de voz y visualizar los resultados generados. 

La plataforma soportará tanto el procesamiento de archivos de audio cargados por el usuario como el reconocimiento de voz mediante transmisión continua de audio (streaming), ampliando las posibilidades de interacción y uso del sistema en distintos escenarios digitales. 

Con esta propuesta se busca reducir la limitada disponibilidad de servicios ASR en quechua en entornos digitales, proporcionando una solución tecnológica accesible, reutilizable y escalable que contribuya a incrementar la presencia de la lengua en aplicaciones y servicios digitales. 

### 1.4.1 DISEÑO DE SOLUCIÓN 

El diseño de la solución se fundamenta en una arquitectura de servicios desplegada en la nube, orientada a garantizar escalabilidad, mantenibilidad e interoperabilidad entre los componentes del sistema. La arquitectura propuesta estará organizada en diferentes módulos desacoplados que permitirán gestionar de forma independiente las funcionalidades de presentación, acceso a servicios y procesamiento del reconocimiento de voz.

## Arquitectura Lógica

La arquitectura lógica de la Plataforma Web de Reconocimiento Automático de Voz (ASR) para quechua está implementada como un conjunto de 6 microservicios en Python 3.11 + FastAPI, desacoplados y comunicados vía HTTP/REST (con httpx.AsyncClient) y WebSockets, que facilitan la escalabilidad, la interoperabilidad y la evolución independiente de sus componentes. 

- Presentation Layer: 	 

    - Aplicación web en Angular 18 (TypeScript), con pruebas unitarias en Jest y E2E en Cypress. Interfaz para carga de audio, control de transmisión en tiempo real (streaming WebSocket), visualización y descarga de transcripciones, historial de procesos y gestión de perfil. 
    - Documentación técnica e interactiva expuesta vía Swagger UI / OpenAPI, generada automáticamente por cada servicio FastAPI. 

- Application Layer: 

    - API Gateway: Punto unificado de entrada. Enruta las peticiones a los demás servicios, valida el token JWT en cada request protegido contra `auth-service` (`/internal/auth/validate-token`) y agrega datos de `user-service` y `transcription-manager` para el dashboard. 
    - Auth-service: Gestión de identidad — login, logout, emisión/validación de tokens JWT, recuperación de contraseña, lista de revocación (blocklist) de tokens y rate limiting de intentos de login.   
    - User-service: Registro y gestión de perfiles de usuario (CRUD), orquesta el registro creando el perfil propio y delegando la creación de credenciales en auth-service; gestiona también el cambio de email con verificación. 
    - Audio-processor: Recepción y validación de archivos de audio, conversión/normalización con FFmpeg (formato, sample rate, mono 16kHz) y reenvío del audio procesado a `asr-service`.   
    - Asr-service: Inferencia con modelo Whisper afinado para quechua, tanto en modo batch (`/internal/asr/transcribe`) como en modo streaming en tiempo real vía WebSocket, devolviendo transcripciones parciales y finales.   
    - Transcription-manager: Persistencia, listado paginado, renombrado, eliminación y descarga de transcripciones, junto con el nivel de confianza por palabra (`word_confidences`).   

- Data Layer: 

    - 4 instancias de PostgreSQL 16 independientes, una por servicio con estado: auth-db (auth_db), user-db (user_db), audio-db (audio_db) y trans-db (trans_db). asr-service y api-gateway son stateless (sin base de datos propia). 
    - Almacenamiento de archivos: volumen compartido asr_audio para los audios subidos y sus derivados procesados (WAV normalizado), consumido por audio-processor y asr-service. 
    - Modelo ASR: caché local del modelo Whisper (whisper-cache) montado en el contenedor de asr-service para evitar redescargas en cada reinicio. 

## Arquitectura Física 

La arquitectura física define el despliegue en infraestructura contenerizada, garantizando alta disponibilidad, seguridad y escalabilidad horizontal. El repositorio incluye dos perfiles de despliegue: Docker Compose para desarrollo local y Kubernetes para staging/producción.  

- Componentes físicos y despliegue: 

    - Frontend: aplicación Angular (asr-quechua-frontend) compilada como artefactos estáticos. 
    - API Gateway: api-gateway (puerto interno 8000, expuesto en 8000 en Compose) — único punto de entrada hacia el resto de microservicios; en Kubernetes cuenta con Deployment + Service + HorizontalPodAutoscaler (mín. 2, máx. 10 réplicas, target 70% CPU / 80% memoria). 
    - Microservicios backend (cada uno con su propio Dockerfile, Deployment, Service, ConfigMap, Secret y HPA en k8s/<service>/): 
        - auth-service  
        - user-service  
        - audio-processor (volumen asr_audio para archivos en proceso) 
        - asr-service - recursos reservados más altos (requests: 1 CPU / 4Gi, limits: 2 CPU / 8Gi) y start_period extendido (120s) por la carga del modelo Whisper; volumen de caché whisper-cache. 
        - transcription-manager  

    - Bases de datos: contenedores postgres:16-alpine independientes por servicio (auth-db, user-db, audio-db, trans-db), cada uno con su propio volumen persistente y healthcheck (pg_isready). 
    - Orquestación y resiliencia: docker-compose.yml define depends_on con condition: service_healthy para garantizar el orden de arranque (bases de datos → servicios dependientes → api-gateway); en Kubernetes, los Deployment usan RollingUpdate (maxUnavailable: 0) y readinessProbe/livenessProbe sobre /health. 
    - Red y seguridad: namespace dedicado asr-platform en Kubernetes; en Compose, red interna de Docker, secretos sensibles (JWT_SECRET_KEY, credenciales de DB) gestionados vía k8s/<service>/secret.yaml o variables de entorno en Compose. 
    - Integración CI/CD: pipelines de build, pruebas (pytest, pytest.ini, conftest.py) y despliegue de imágenes mediante GitHub Actions, con etapas separadas para entornos de desarrollo, staging y producción. 