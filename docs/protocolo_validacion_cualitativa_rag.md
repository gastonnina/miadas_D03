# Protocolo Reproducible de Validación Cualitativa RAG

## Objetivo

Evaluar el valor práctico del sistema RAG no solo como buscador, sino como asistente de análisis sobre convocatorias ya recuperadas.

## Hipótesis

Aunque el RAG no mejore de forma consistente el ranking de recuperación, sí puede aportar valor en:

1. interpretación de requisitos;
2. explicación de alineación con el rubro del proveedor;
3. síntesis de señales de riesgo documental o técnico;
4. apoyo a una decisión preliminar.

## Prerrequisitos

1. PostgreSQL/pgvector disponible y corpus cargado.
2. Entorno virtual listo.
3. Si se desean respuestas reales del modelo:
   - `GOOGLE_API_KEY` o `OPENAI_API_KEY` configurada.

## Paso 1. Generar ejemplos reproducibles de preguntas de negocio

Sin respuestas LLM:

```bash
env PYTHONPATH=. .venv/bin/python scripts/generate_business_question_validation.py
```

Con respuestas LLM:

```bash
env PYTHONPATH=. .venv/bin/python scripts/generate_business_question_validation.py --generate-llm-answers
```

Salida esperada:

- `outputs/tables/business_question_validation_reproducible.csv`

Contenido esperado:

1. pregunta;
2. escenario;
3. CUCE recuperados;
4. entidades recuperadas;
5. preview del contexto;
6. respuesta LLM, si fue posible generarla.

## Paso 2. Calcular métricas automáticas y preparar rúbrica

Ejecutar:

```bash
env PYTHONPATH=. .venv/bin/python scripts/score_business_question_validation.py
```

Salidas esperadas:

- `outputs/tables/business_question_validation_quality_metrics.csv`
- `outputs/tables/business_question_validation_quality_rubric.csv`

## Métricas automáticas generadas

Las métricas automáticas no reemplazan la evaluación humana, pero ayudan a detectar señales básicas de calidad:

1. `has_llm_answer`
   - indica si hubo respuesta generada.
2. `answer_chars`
   - longitud de la respuesta.
3. `answer_word_count`
   - longitud en palabras.
4. `answer_cuce_mentions`
   - cuántos CUCE menciona la respuesta.
5. `supported_cuce_mentions`
   - cuántos CUCE mencionados sí estaban en las fuentes recuperadas.
6. `unsupported_cuce_mentions`
   - cuántos CUCE mencionados no estaban en las fuentes recuperadas.
7. `grounded_cuce_precision`
   - proporción de CUCE mencionados que sí vienen del contexto.
8. `mentions_any_retrieved_entity`
   - si la respuesta reutiliza entidades efectivamente recuperadas.
9. `uncertainty_signal`
   - si la respuesta expresa cautela ante falta de contexto.
10. `actionability_signal`
   - si la respuesta sugiere una conclusión o recomendación útil.

## Rúbrica manual recomendada

Cada respuesta debe evaluarse manualmente de `1` a `5` en:

1. `relevance_1_5`
   - si responde la pregunta planteada.
2. `groundedness_1_5`
   - si se apoya en el contexto recuperado.
3. `specificity_1_5`
   - si da detalles concretos y no solo generalidades.
4. `actionability_1_5`
   - si ayuda a decidir o priorizar.
5. `clarity_1_5`
   - si la respuesta es clara y legible.
6. `hallucination_risk_1_5`
   - mayor puntaje significa menor riesgo de alucinación.
7. `overall_1_5`
   - juicio global de utilidad.

## Escenarios recomendados a comparar

Actualmente el script reproduce estos escenarios:

1. `keyword_base`
2. `hybrid_base`
3. `keyword_enriched_qc_filtered`
4. `hybrid_enriched_qc_filtered`
5. `keyword_focused_qc_filtered_v2`

## Preguntas de negocio incluidas

Las preguntas reproducibles cubren estas categorías:

1. `fit_proveedor`
2. `resumen_requisitos`
3. `decision_preliminar`
4. `alineacion_rubro`

## Qué ejemplos conviene mostrar en la monografía

Seleccionar al menos:

1. un caso donde `keyword_base` recupera bien y el RAG explica bien;
2. un caso donde `enriched_qc_filtered` aporta más detalle útil;
3. un caso donde el contexto recuperado es ruidoso y el RAG no ayuda;
4. un caso donde el modelo responde con cautela porque el contexto no alcanza.

## Cómo reportar resultados

Separar el análisis en dos niveles:

### Nivel 1. Calidad del retrieval

- ¿La convocatoria relevante fue recuperada?
- ¿El top-k tiene poco ruido o mucho ruido?

### Nivel 2. Calidad de la respuesta RAG

- ¿La respuesta usa evidencia del contexto?
- ¿La respuesta es útil para un proveedor?
- ¿Resume bien requisitos, riesgos o ajuste al rubro?

## Limitación actual del entorno

Estado actual del entorno:

1. el pipeline reproducible ya está preparado;
2. ya se validó ejecución con Gemini `2.5 Flash` en free tier;
3. por las limitaciones del free tier, conviene ejecutar lotes pequeños y priorizar casos representativos sobre barridos masivos.

## Archivos clave

- `scripts/generate_business_question_validation.py`
- `scripts/score_business_question_validation.py`
- `docs/hallazgos_validacion_cualitativa_rag.md`
- `outputs/tables/business_question_validation_reproducible.csv`
- `outputs/tables/business_question_validation_quality_metrics.csv`
- `outputs/tables/business_question_validation_quality_rubric.csv`
