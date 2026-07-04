# Resumen de Resultados Cualitativos RAG

## Lectura general

Los casos cualitativos evaluados muestran un patrón consistente:

1. el retrieval base suele recuperar al menos un candidato plausible;
2. el RAG agrega valor al explicar pertinencia, descartar ruido y priorizar oportunidades;
3. el principal aporte observado no está en mejorar el ranking inicial, sino en convertir resultados recuperados en una respuesta útil para toma de decisión.

## Tabla resumen

| Caso | Pregunta / foco | Escenarios | Hallazgo principal | Aporte observado del RAG | Utilidad para la monografía |
| --- | --- | --- | --- | --- | --- |
| `biz_001` | Medicamentos hospitalarios | `keyword_base` vs `hybrid_base` | Ambos escenarios recuperan oportunidades plausibles; `keyword` es más selectivo y `hybrid` más exhaustivo. | Explica por qué ciertos CUCE sí corresponden al rubro y descarta procesos no pertinentes. | Permite mostrar priorización de oportunidades y grounding limpio. |
| `biz_002` | Reactivos de laboratorio | `keyword_base` vs `hybrid_base` | Ambos escenarios recuperan procesos muy alineados; `hybrid` enfatiza mejor subáreas técnicas de laboratorio. | Transforma el top-k en evidencia comercialmente útil para un proveedor. | Caso fuerte para mostrar extracción de evidencia de rubro. |
| `biz_003` | Software en salud | `keyword_base` vs `hybrid_base` | Ambos escenarios identifican el único CUCE realmente de software; `keyword` explica mejor el ruido y `hybrid` prioriza con más fuerza. | Desambigua software real frente a equipamiento o servicios no relacionados. | Caso clave para mostrar valor interpretativo del RAG. |
| `biz_004` | Resumen de requisitos de alcantarillado | `keyword_base` vs `hybrid_base` | `keyword` mezcla procesos de agua potable; `hybrid` aterriza mejor en un CUCE explícito de alcantarillado sanitario. | Produce una síntesis más útil cuando el retrieval enfoca mejor la intención de la consulta. | Caso fuerte para mostrar dependencia del RAG respecto al contexto recuperado. |
| `biz_008` | Alineación de rubro en obras sanitarias | `keyword_base` vs `hybrid_base` | Ambos escenarios detectan mucho ruido; `hybrid` encuentra una obra más claramente sanitaria que `keyword`. | Filtra ruido y justifica cuál proceso vale la pena revisar. | Caso fuerte para mostrar valor del RAG incluso con top-k imperfecto. |

## Síntesis interpretativa

### Lo que sí se puede defender

1. El sistema RAG sí aporta valor cuando el retrieval recupera al menos una convocatoria razonablemente pertinente.
2. El RAG ayuda a:
   - explicar pertinencia;
   - resumir requisitos;
   - identificar ruido;
   - orientar una decisión preliminar del proveedor.
3. La calidad de la respuesta RAG depende directamente de la calidad del contexto recuperado.

### Lo que no conviene afirmar

1. Que el RAG haya mejorado de manera consistente el ranking de búsqueda.
2. Que el enriquecimiento con DBC haya mejorado el retrieval en este corpus.
3. Que el problema principal sea falta de fine-tuning.

## Conclusión operativa

La evidencia reunida sugiere una arquitectura más realista para el sistema:

1. `retrieval` para detección inicial de candidatos;
2. `RAG` para análisis documental, descarte de ruido y soporte a decisión.

## Archivos asociados

- `docs/hallazgos_validacion_cualitativa_rag.md`
- `outputs/tables/business_question_validation_case_summary.csv`
- `outputs/tables/business_question_validation_biz001_compare.csv`
- `outputs/tables/business_question_validation_biz002_compare.csv`
- `outputs/tables/business_question_validation_biz003_compare.csv`
- `outputs/tables/business_question_validation_biz004_compare.csv`
- `outputs/tables/business_question_validation_biz008_compare.csv`
