# Hallazgos de Validación Cualitativa RAG

## Propósito

Registrar de forma acumulativa los hallazgos cualitativos obtenidos en pruebas RAG con preguntas de negocio, para poder reutilizarlos luego en la redacción de la monografía y en el documento LaTeX.

## Criterio de lectura

Cada caso resume:

1. la pregunta evaluada;
2. los escenarios comparados;
3. el comportamiento del retrieval;
4. el comportamiento de la respuesta RAG;
5. la utilidad narrativa para la monografía.

## Caso 1. `biz_001` medicamentos hospitalarios

### Pregunta

`Mi empresa provee medicamentos hospitalarios. Que convocatorias recuperadas parecen mas alineadas y por que?`

### Archivos de evidencia

- `outputs/tables/business_question_validation_smoke.csv`
- `outputs/tables/business_question_validation_smoke_metrics.csv`
- `outputs/tables/business_question_validation_biz001_compare.csv`
- `outputs/tables/business_question_validation_biz001_compare_metrics.csv`

### Escenarios comparados

1. `keyword_base`
2. `hybrid_base`

### Hallazgos

1. `keyword_base` generó una respuesta breve, clara y selectiva.
2. `keyword_base` destacó dos convocatorias centrales:
   - `26-1101-04-1669637-1-1`
   - `26-0423-00-1669738-1-1`
3. La respuesta de `keyword_base` descartó explícitamente procesos no relacionados como consultoría, imprenta u obras.
4. `hybrid_base` generó una respuesta más amplia y exhaustiva.
5. `hybrid_base` mencionó cinco convocatorias del rubro medicamentos/salud, todas apoyadas en el contexto recuperado.
6. En ambos escenarios:
   - `has_llm_answer = 1`
   - `grounded_cuce_precision = 1.0`
   - no hubo `llm_error`
7. La diferencia práctica entre escenarios no fue de veracidad sino de estilo:
   - `keyword_base` fue más preciso y fácil de leer;
   - `hybrid_base` fue más exploratorio y cubrió más oportunidades.

### Interpretación para la monografía

Este caso apoya la tesis de que:

1. el retrieval sirve para detectar candidatos plausibles;
2. el RAG agrega valor al explicar por qué esos candidatos son pertinentes;
3. el valor del RAG aparece en la interpretación y priorización de convocatorias recuperadas, no necesariamente en mejorar el ranking inicial.

## Caso 2. `biz_002` reactivos de laboratorio

### Pregunta

`Mi empresa vende reactivos de laboratorio. Que evidencia aparece en la convocatoria para pensar que si corresponde a nuestro rubro?`

### Archivos de evidencia

- `outputs/tables/business_question_validation_biz002_compare.csv`
- `outputs/tables/business_question_validation_biz002_compare_metrics.csv`
- `outputs/tables/business_question_validation_biz002_compare_rubric.csv`

### Escenarios comparados

1. `keyword_base`
2. `hybrid_base`

### Hallazgos

1. `keyword_base` respondió con una justificación muy directa basada en el `objeto_contratacion`.
2. `keyword_base` identificó cinco convocatorias explícitamente alineadas con reactivos de laboratorio y citó el motivo de pertinencia en cada una.
3. `hybrid_base` también recuperó cinco convocatorias relevantes y construyó una respuesta compacta y enfocada en evidencia del rubro.
4. `hybrid_base` mostró un sesgo más técnico:
   - reactivos químicos;
   - química sanguínea;
   - hematología;
   - inmunología;
   - microbiología;
   - reactivos para equipos específicos.
5. En ambos escenarios:
   - `has_llm_answer = 1`
   - `answer_cuce_mentions = 5`
   - `supported_cuce_mentions = 5`
   - `grounded_cuce_precision = 1.0`
   - no hubo `llm_error`
6. `keyword_base` mencionó explícitamente entidades recuperadas; `hybrid_base` mantuvo grounding por CUCE, aunque la métrica automática de mención exacta de entidad quedó en `0`, probablemente por variación textual en la redacción.

### Interpretación para la monografía

Este caso es especialmente fuerte porque muestra:

1. buena recuperación inicial;
2. buena extracción de evidencia textual;
3. capacidad del RAG para transformar una lista de CUCE en una explicación comercialmente útil para un proveedor.

Además, este caso sugiere que en preguntas de rubro muy específico, la combinación `retrieval + RAG` sí entrega valor operativo claro.

## Síntesis parcial

Con los casos `biz_001` y `biz_002`, ya se observa un patrón consistente:

1. cuando el retrieval recupera convocatorias plausibles, Gemini puede producir respuestas útiles y bien aterrizadas;
2. el sistema RAG funciona mejor como capa de explicación y soporte a decisión que como mejora garantizada del ranking de búsqueda;
3. `keyword_base` tiende a respuestas más breves y selectivas;
4. `hybrid_base` tiende a respuestas más exhaustivas, potencialmente mejores para exploración de oportunidades.

## Caso 3. `biz_003` software para gestión clínica

### Pregunta

`Somos una empresa de software para gestion clinica. La convocatoria realmente pide software o solo equipamiento?`

### Archivos de evidencia

- `outputs/tables/business_question_validation_biz003_compare.csv`
- `outputs/tables/business_question_validation_biz003_compare_metrics.csv`
- `outputs/tables/business_question_validation_biz003_compare_rubric.csv`

### Escenarios comparados

1. `keyword_base`
2. `hybrid_base`

### Hallazgos

1. Ambos escenarios identificaron correctamente la convocatoria central:
   - `26-0046-38-1660991-1-1`
2. Ambos escenarios distinguieron que esa convocatoria sí pide software y no solo equipamiento.
3. `keyword_base` produjo una respuesta más explicativa:
   - resaltó la convocatoria correcta;
   - descartó explícitamente los otros CUCE recuperados como ruido o procesos no relacionados.
4. `hybrid_base` produjo una respuesta más corta y más tajante:
   - identificó un único CUCE verdaderamente relevante;
   - resumió el resto como equipamiento, formularios o medicamentos.
5. Métricas automáticas:
   - `keyword_base`: `grounded_cuce_precision = 1.0`, `answer_cuce_mentions = 5`
   - `hybrid_base`: `grounded_cuce_precision = 1.0`, `answer_cuce_mentions = 1`
6. Este caso muestra una diferencia cualitativa útil:
   - `keyword_base` explica mejor el ruido recuperado;
   - `hybrid_base` hace una priorización más agresiva y concentra la atención en el mejor candidato.

### Interpretación para la monografía

Este es uno de los casos más fuertes del estudio porque muestra que el RAG no solo resume, sino que ayuda a desambiguar:

1. identifica cuándo una convocatoria realmente pertenece al rubro software;
2. diferencia software de equipamiento o servicios no relacionados;
3. convierte un conjunto de resultados recuperados en una decisión interpretable para el proveedor.

En términos narrativos, este caso apoya muy bien la idea de que el aporte de RAG está en el análisis posterior al retrieval, no en reemplazar el motor inicial de búsqueda.

## Caso 4. `biz_004` resumen de requisitos para alcantarillado

### Pregunta

`Resume los puntos clave que un proveedor deberia revisar antes de postular a esta convocatoria de alcantarillado.`

### Archivos de evidencia

- `outputs/tables/business_question_validation_biz004_compare.csv`
- `outputs/tables/business_question_validation_biz004_compare_metrics.csv`
- `outputs/tables/business_question_validation_biz004_compare_rubric.csv`

### Escenarios comparados

1. `keyword_base`
2. `hybrid_base`

### Hallazgos

1. Ambos escenarios generaron respuestas útiles y sin error:
   - `has_llm_answer = 1`
   - `grounded_cuce_precision = 1.0`
2. `keyword_base` produjo una respuesta más extensa y más general.
3. `keyword_base` se apoyó sobre varios procesos vinculados a `Semapa` y al proyecto `Tanque Quenamari - Zona Maicas`, pero mezcló agua potable con la intención original de la consulta sobre alcantarillado.
4. `hybrid_base` fue más corto y más pertinente para la pregunta:
   - identificó explícitamente el CUCE `26-0253-00-1668448-1-1`;
   - resaltó que ese proceso sí menciona de forma directa `Sistema De Alcantarillado Sanitario`.
5. `hybrid_base` además respondió con mejor estructura orientada a postulación:
   - objeto de contratación;
   - entidad contratante;
   - tipo y modalidad;
   - fechas;
   - documentación esencial.
6. Métricamente:
   - `keyword_base` mencionó 3 CUCE soportados;
   - `hybrid_base` mencionó 1 CUCE soportado;
   - ambos mantuvieron grounding limpio.
7. Este caso muestra que una respuesta más larga no necesariamente es mejor:
   - `keyword_base` fue más abundante;
   - `hybrid_base` fue más enfocada y mejor alineada con la necesidad concreta del usuario.

### Interpretación para la monografía

Este caso es metodológicamente importante porque muestra un valor adicional del RAG:

1. no solo resume lo recuperado;
2. también ayuda a focalizar qué proceso parece realmente responder a la intención de la consulta;
3. en preguntas de requisitos, una estrategia de retrieval más precisa puede traducirse en una respuesta RAG más útil, aunque sea más breve.

En otras palabras, este caso ayuda a argumentar que la utilidad del RAG depende de la calidad del contexto recuperado y que la diferencia entre escenarios se refleja después en la calidad de la síntesis.

## Caso 5. `biz_008` alineación de rubro en obras sanitarias

### Pregunta

`Somos contratistas de obras sanitarias. Las convocatorias recuperadas realmente encajan con nuestro rubro o hay ruido en los resultados?`

### Archivos de evidencia

- `outputs/tables/business_question_validation_biz008_compare.csv`
- `outputs/tables/business_question_validation_biz008_compare_metrics.csv`
- `outputs/tables/business_question_validation_biz008_compare_rubric.csv`

### Escenarios comparados

1. `keyword_base`
2. `hybrid_base`

### Hallazgos

1. Ambos escenarios respondieron de forma útil y con grounding limpio:
   - `has_llm_answer = 1`
   - `grounded_cuce_precision = 1.0`
2. Ambos identificaron que la mayoría de resultados recuperados eran ruido para el rubro consultado.
3. `keyword_base` consideró como convocatoria más relevante:
   - `26-1201-00-1669879-1-1`
   - por su relación con `canalizado` y manejo de aguas.
4. `hybrid_base` seleccionó una convocatoria distinta y más claramente sanitaria:
   - `26-0802-00-1667864-1-1`
   - `Construccion Obras De Proteccion Sistema De Aduccion`
   - entidad `ELAPAS Sucre`
5. En ambos escenarios, el RAG hizo algo importante para la lógica del sistema:
   - no se limitó a enumerar resultados;
   - explicitó qué procesos eran ruido y por qué.
6. Este caso muestra que el RAG puede transformar un top-k parcialmente ruidoso en una respuesta más accionable para el usuario final.
7. También muestra una diferencia entre escenarios:
   - `keyword_base` encontró una obra potencialmente relacionada por el componente hidráulico;
   - `hybrid_base` encontró una obra más claramente vinculada al sector de agua potable y alcantarillado.

### Interpretación para la monografía

Este caso es muy valioso porque demuestra un escenario realista donde la búsqueda inicial no es pura ni perfecta, pero el RAG aún agrega valor:

1. filtra el ruido;
2. explica por qué algunos resultados no encajan;
3. orienta al proveedor hacia el proceso más defendible dentro del conjunto recuperado.

En términos argumentativos, este caso apoya la tesis de que el RAG puede ser útil incluso cuando el retrieval no es perfecto, siempre que el contexto contenga al menos una oportunidad razonablemente pertinente.

## Próximos casos recomendados

1. algún caso donde el contexto recuperado sea claramente ruidoso o insuficiente
2. una tabla comparativa final con 4 o 5 casos representativos
3. síntesis directamente convertible a tabla LaTeX
