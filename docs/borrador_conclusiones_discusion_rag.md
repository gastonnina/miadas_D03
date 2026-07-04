# Borrador de Conclusiones y Discusión

## Conclusiones principales

1. El principal cuello de botella del sistema no fue el LLM, sino el retrieval.
2. El enriquecimiento con DBC no mejoró de manera consistente la recuperación de convocatorias relevantes.
3. Una parte importante del problema se explicó por:
   - desalineación entre `CUCE` y `DBC`;
   - documentos genéricos o plantilla;
   - baja cobertura útil de DBC correctos para el set de evaluación.
4. El baseline `keyword_base` se mantuvo como la estrategia más estable en términos de `precision@5`, `recall@5`, `MRR` y `hit@5`.
5. El `semantic retrieval` no mostró capacidad de mejora estructural sobre este corpus y se mantuvo cerca de cero en la mayoría de escenarios.
6. El valor del sistema RAG apareció principalmente en la fase posterior al retrieval:
   - explicación de pertinencia;
   - descarte de ruido;
   - resumen de requisitos;
   - priorización de oportunidades;
   - soporte a decisión preliminar para proveedores.

## Discusión metodológica

La hipótesis inicial planteaba que el uso de RAG podría mejorar la búsqueda de convocatorias públicas. Sin embargo, los resultados muestran que esa mejora no se manifestó de forma consistente en el ranking de recuperación. En cambio, la evidencia sugiere que el sistema RAG aporta valor en una etapa distinta del flujo: la interpretación de convocatorias ya recuperadas.

Esto implica una reformulación importante del aporte del sistema:

1. el retrieval cumple la función de detección inicial de candidatos;
2. el RAG cumple la función de análisis documental asistido.

En esta arquitectura, el éxito del sistema no depende de que el modelo generativo sustituya al buscador, sino de que ayude a convertir un conjunto de resultados recuperados en información accionable para el usuario final.

## Qué sí se puede afirmar

1. El sistema permite detectar convocatorias plausibles con un baseline léxico relativamente robusto.
2. El RAG mejora la utilidad práctica de esos resultados al justificarlos, resumirlos y contextualizarlos.
3. En dominios específicos como medicamentos, reactivos de laboratorio y software en salud, el sistema mostró buena capacidad para explicar la pertinencia de una convocatoria.
4. En escenarios con ruido parcial, el RAG aún puede agregar valor al filtrar resultados y orientar al usuario hacia el proceso más defendible.

## Qué no conviene afirmar

1. Que el RAG haya mejorado de forma consistente el ranking de búsqueda.
2. Que el corpus enriquecido con DBC haya fortalecido la recuperación sobre el benchmark utilizado.
3. Que el problema principal pueda resolverse con `fine-tuning` del modelo sin antes resolver calidad y cobertura del corpus.
4. Que `GraphRAG` sea una solución justificada para este problema en el estado actual de la evidencia.

## Limitaciones del estudio

1. El benchmark de evaluación fue pequeño.
2. La cobertura de DBC correctos sobre los CUCE evaluados fue limitada.
3. El corpus enriquecido presentó errores de asociación y contaminación documental.
4. La validación cualitativa con LLM se ejecutó sobre casos representativos, no sobre un universo exhaustivo.
5. Las conclusiones deben interpretarse dentro del contexto del corpus y del periodo analizado.

## Implicación práctica

La evidencia apunta a que, para un sistema de apoyo a proveedores en contratación pública, una arquitectura pragmática sería:

1. búsqueda inicial robusta y simple para detectar candidatos;
2. capa RAG para explicar, resumir y priorizar convocatorias recuperadas.

Esta formulación es metodológicamente más precisa que afirmar que RAG “mejora la búsqueda” en términos generales. En este estudio, su mayor contribución estuvo en la explicación asistida y no en la recuperación inicial.

## Trabajo futuro razonable

1. mejorar la calidad y cobertura del corpus documental;
2. probar estrategias léxicas más fuertes o combinadas, como `FTS + ILIKE`;
3. ampliar el benchmark con más consultas y más anotaciones relevantes;
4. extender la validación cualitativa con una rúbrica humana más amplia;
5. solo después de ello considerar técnicas de mayor costo como rerankers o modelos alternativos.
