# Protocolo Reproducible de Experimentos RAG y Retrieval

## Objetivo

Documentar un flujo reproducible para:

1. auditar la calidad del corpus enriquecido con DBC;
2. reconstruir variantes de corpus;
3. cargar variantes al índice/vector store;
4. ejecutar evaluaciones cuantitativas;
5. ejecutar validaciones orientadas a la monografía.

## Alcance

Este protocolo cubre las fases ya ejecutadas hasta el momento:

- Fase 1: auditoría manual del DBC en el set de evaluación;
- Fase 2: gate de calidad para DBC;
- Fase 3: focused chunking técnico;
- Fase 4: comparación controlada de variantes;
- Fase 5: análisis cuantitativo por categoría;
- Experimentos preliminares:
  - expansión léxica controlada;
  - FTS de PostgreSQL vs `ILIKE`.

## Prerrequisitos

1. Activar el entorno virtual del proyecto o usar directamente `.venv/bin/python`.
2. Tener Docker levantado con PostgreSQL/pgvector disponible.
3. Verificar `DATABASE_URL` en `.env` o usar el valor por defecto del proyecto.
4. Tener disponible el corpus base y los textos curados de documentos.

## Convención de ejecución

Todos los comandos de este documento asumen ejecución desde la raíz del repositorio:

```bash
cd /var/www/codigo/maestria_ia/umsa/diplomados_intermedios/dip_03
```

Cuando una ejecución depende de imports del proyecto, usar:

```bash
env PYTHONPATH=. .venv/bin/python <script>
```

## Paso 0. Verificación mínima del entorno

Compilar los scripts relevantes:

```bash
.venv/bin/python -m py_compile \
  scripts/audit_dbc_quality.py \
  scripts/build_enriched_corpus.py \
  scripts/build_focused_chunked_corpus.py \
  scripts/analyze_phase5_by_category.py \
  scripts/evaluate_lexical_profile.py \
  scripts/evaluate_keyword_strategy.py
```

Verificar conexión lógica a la base cuando Docker esté arriba ejecutando cualquiera de los scripts de evaluación.

## Paso 1. Auditoría automática de calidad DBC

Ejecutar:

```bash
env PYTHONPATH=. .venv/bin/python scripts/audit_dbc_quality.py
```

Salida principal esperada:

- `outputs/tables/dbc_quality_audit.csv`

Qué verificar:

1. distribución de `accept`, `review`, `reject`;
2. razones dominantes de rechazo;
3. CUCE problemáticos ya conocidos.

## Paso 2. Reconstrucción de corpus enriquecido filtrado

Ejecutar:

```bash
env PYTHONPATH=. .venv/bin/python scripts/build_enriched_corpus.py \
  --dbc-quality-report-path outputs/tables/dbc_quality_audit.csv
```

Salidas esperadas:

- `data/processed/curated/curated_corpus_enriched_qc_filtered.parquet`
- `data/processed/curated/curated_corpus_enriched_qc_filtered.csv`
- `data/processed/curated/curated_corpus_enriched_qc_filtered_unmatched.csv`

Qué verificar:

1. que los `reject` no se incorporen al enriquecido;
2. cuántos CUCE mantienen DBC útil;
3. si los casos auditados como erróneos desaparecen del corpus filtrado.

## Paso 3. Reconstrucción de focused chunking técnico

Ejecutar:

```bash
env PYTHONPATH=. .venv/bin/python scripts/build_focused_chunked_corpus.py \
  --input-path data/processed/curated/curated_corpus_enriched_qc_filtered.parquet \
  --output-path data/processed/curated/curated_corpus_focused_chunked_qc_filtered_v2.parquet \
  --selection-report-path data/processed/curated/curated_corpus_focused_chunked_qc_filtered_v2_selection_report.csv \
  --allowed-dbc-statuses accept,review \
  --allowed-dbc-review-reasons partial_object_alignment
```

Salidas esperadas:

- `data/processed/curated/curated_corpus_focused_chunked_qc_filtered_v2.parquet`
- `data/processed/curated/curated_corpus_focused_chunked_qc_filtered_v2.csv`
- `data/processed/curated/curated_corpus_focused_chunked_qc_filtered_v2_selection_report.csv`

Qué verificar:

1. cuántos CUCE generan chunks;
2. si los segmentos seleccionados son realmente técnicos;
3. si la cobertura sobre el set de evaluación sigue siendo suficiente.

## Paso 4. Carga de variantes al índice/vector store

Este paso requiere base PostgreSQL levantada y accesible.

La carga puede hacerse con el flujo del proyecto que inserta corpus por `corpus_variant`. Si se repite esta fase, validar primero que las constantes de rutas estén definidas en:

- `src/config.py`
- `src/data_loader.py`

Validación mínima recomendada:

1. contar filas por `corpus_variant`;
2. verificar que existan:
   - `base`
   - `enriched`
   - `enriched_qc_filtered`
   - `focused_chunked`
   - `focused_chunked_qc_filtered_v2`

## Paso 5. Evaluación cuantitativa por variantes

Artefacto ya generado en la fase 4:

- `outputs/evaluation_summary_phase4.csv`

Qué interpretar:

1. comparar `keyword_base` vs `keyword_enriched_qc_filtered`;
2. comparar `hybrid_base` vs `hybrid_enriched_qc_filtered`;
3. detectar si `focused_chunked_qc_filtered_v2` falla por ranking o por cobertura.

## Paso 6. Evaluación por categoría

Ejecutar:

```bash
env PYTHONPATH=. .venv/bin/python scripts/analyze_phase5_by_category.py
```

Salidas esperadas:

- `outputs/tables/evaluation_phase5_detailed.csv`
- `outputs/tables/evaluation_phase5_by_category.csv`
- `outputs/tables/evaluation_phase5_by_split_category.csv`

Qué interpretar:

1. en qué categorías el baseline keyword ya es fuerte;
2. dónde falla `hybrid`;
3. si el DBC aporta algo por tipo de consulta.

## Paso 7. Experimento de expansión léxica

Ejecutar:

```bash
env PYTHONPATH=. .venv/bin/python scripts/evaluate_lexical_profile.py
```

Salidas esperadas:

- `outputs/tables/evaluation_lexical_profile_summary.csv`
- `outputs/tables/evaluation_lexical_profile_detailed.csv`

Qué interpretar:

1. si la expansión mejora `MRR` o solo mueve el ranking;
2. si aumenta ruido en consultas ambiguas;
3. si vale la pena mantenerla.

Estado actual del hallazgo:

- no mostró mejora consistente;
- no se recomienda como siguiente línea prioritaria.

## Paso 8. Experimento de estrategia keyword `ILIKE` vs `FTS`

Ejecutar:

```bash
env PYTHONPATH=. .venv/bin/python scripts/evaluate_keyword_strategy.py
```

Salidas esperadas:

- `outputs/tables/evaluation_keyword_strategy_summary.csv`
- `outputs/tables/evaluation_keyword_strategy_detailed.csv`

Qué interpretar:

1. si `FTS` mejora recuperación temprana;
2. si mejora `hybrid`;
3. qué consultas rompen con `FTS`;
4. si conviene una mezcla `FTS + ILIKE`.

Estado actual del hallazgo:

- `FTS` no reemplaza directamente a `ILIKE`;
- pero sí mostró una mejora interesante en `hybrid` sobre `test`;
- merece una variante combinada en una siguiente iteración.

## Paso 9. Validación cualitativa para la monografía

Objetivo:

demostrar el valor de RAG no solo en ranking, sino en análisis de convocatorias recuperadas.

Preguntas sugeridas:

1. ¿La convocatoria encaja con el rubro del proveedor?
2. ¿Qué requisitos técnicos o administrativos son más importantes?
3. ¿Qué evidencia textual justifica el ajuste o descarte?
4. ¿Qué diferencias clave existen entre dos convocatorias candidatas?

Artefactos ya existentes:

- `outputs/tables/business_question_validation.csv`
- `outputs/tables/business_question_validation_focused_chunked.csv`

Qué documentar:

1. consulta del proveedor;
2. convocatorias recuperadas;
3. contexto enviado al modelo;
4. respuesta del RAG;
5. juicio cualitativo sobre utilidad real.

## Recomendación para documentación de monografía

Separar resultados en dos capas:

1. `Retrieval`
   - métricas `precision@5`, `recall@5`, `MRR`, `hit@5`;
   - comparación de corpus y estrategias.
2. `RAG aplicado`
   - utilidad para interpretar, resumir y justificar convocatorias ya recuperadas.

## Resumen ejecutivo reproducible

Si hubiera que repetir rápidamente el flujo mínimo hoy, el orden recomendado es:

```bash
env PYTHONPATH=. .venv/bin/python scripts/audit_dbc_quality.py
env PYTHONPATH=. .venv/bin/python scripts/build_enriched_corpus.py --dbc-quality-report-path outputs/tables/dbc_quality_audit.csv
env PYTHONPATH=. .venv/bin/python scripts/build_focused_chunked_corpus.py --input-path data/processed/curated/curated_corpus_enriched_qc_filtered.parquet --output-path data/processed/curated/curated_corpus_focused_chunked_qc_filtered_v2.parquet --selection-report-path data/processed/curated/curated_corpus_focused_chunked_qc_filtered_v2_selection_report.csv --allowed-dbc-statuses accept,review --allowed-dbc-review-reasons partial_object_alignment
env PYTHONPATH=. .venv/bin/python scripts/analyze_phase5_by_category.py
env PYTHONPATH=. .venv/bin/python scripts/evaluate_lexical_profile.py
env PYTHONPATH=. .venv/bin/python scripts/evaluate_keyword_strategy.py
```

## Archivos clave de referencia

- `docs/plan_mejoras_retrieval_rag.md`
- `docs/protocolo_validacion_cualitativa_rag.md`
- `outputs/evaluation_summary_phase4.csv`
- `outputs/tables/dbc_quality_audit.csv`
- `outputs/tables/evaluation_phase5_by_category.csv`
- `outputs/tables/evaluation_lexical_profile_summary.csv`
- `outputs/tables/evaluation_keyword_strategy_summary.csv`
