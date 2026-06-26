# Proyecto Diplomado 3 - Sistema RAG para SICOES

## 1. Nombre tentativo del proyecto

**Sistema inteligente de recuperacion semantica para convocatorias publicas del SICOES mediante embeddings, PostgreSQL + pgvector y Retrieval-Augmented Generation (RAG).**

## 2. Contexto

Este proyecto corresponde al Modulo 3 del Diplomado en Inteligencia Artificial Aplicada a los Negocios. El objetivo es construir un prototipo funcional que permita consultar convocatorias publicas del portal SICOES de Bolivia usando tecnicas de Procesamiento de Lenguaje Natural, embeddings, busqueda vectorial y RAG.

La arquitectura principal del proyecto se actualiza para usar **PostgreSQL + pgvector** como base de datos operacional y vectorial. **LangChain** se mantiene como capa de orquestacion para embeddings, retriever y generacion de respuestas, permitiendo cambiar de proveedor de LLM con bajo acoplamiento.

El proyecto debe incluir:

* Extraccion de datos publicos del SICOES.
* Almacenamiento de dataset crudo.
* Limpieza y transformacion del dataset.
* Generacion de un dataset optimizado para RAG.
* Carga del dataset RAG en PostgreSQL.
* Generacion y almacenamiento de embeddings en pgvector.
* Busqueda SQL tradicional y busqueda vectorial semantica.
* Interfaz de consulta tipo chatbot.
* Documentacion academica en LaTeX con formato APA.
* Figuras, diagramas, tablas y resultados experimentales.

## 3. Alcance del proyecto

### Incluido

* Trabajar con el listado publico de convocatorias vigentes del SICOES.
* Usar campos como CUCE, entidad, tipo de contratacion, modalidad, objeto de contratacion, fechas, estado, archivos disponibles y URL de ficha.
* Crear un pipeline reproducible:

```text
SICOES
→ dataset raw
→ dataset clean
→ dataset RAG
→ PostgreSQL
→ embeddings
→ pgvector
→ retriever
→ LLM
→ Streamlit
```

* Implementar una busqueda semantica de convocatorias.
* Implementar una linea base SQL con `ILIKE`.
* Evaluar busqueda tradicional, busqueda semantica y una opcion hibrida.
* Definir un diseno experimental reproducible para retrieval y RAG.
* Generar documentacion academica en LaTeX.

### No incluido en esta primera version

* Descarga masiva de PDFs protegidos por Cloudflare Turnstile.
* Resolucion automatica de CAPTCHA.
* Scraping profundo de documentos DBC.
* Entrenamiento o fine-tuning de modelos.
* Agentes complejos.

Los PDFs de ficha se consideran una mejora futura.

## 4. Estructura sugerida del repositorio

```text
sicoes-rag-ai/
│
├── README.md
├── PROJECT_CONTEXT.md
├── .gitignore
├── .env.example
├── pyproject.toml
├── uv.lock
├── docker-compose.yml
│
├── db/
│   └── init/
│       └── 01_init_pgvector.sql
│
├── data/
│   ├── raw/
│   │   ├── sicoes_convocatorias_raw.csv
│   │   └── sicoes_convocatorias_raw.parquet
│   ├── processed/
│   │   ├── sicoes_convocatorias_clean.csv
│   │   └── sicoes_convocatorias_clean.parquet
│   └── rag/
│       ├── sicoes_convocatorias_rag.csv
│       └── sicoes_convocatorias_rag.parquet
│
├── notebooks/
│   ├── 01_extract_sicoes.ipynb
│   ├── 02_clean_transform_rag.ipynb
│   ├── 03_eda.ipynb
│   ├── 04_embeddings_pgvector.ipynb
│   └── 05_rag_evaluation.ipynb
│
├── src/
│   ├── config.py
│   ├── data_loader.py
│   ├── vector_store.py
│   ├── rag_chain.py
│   └── evaluation.py
│
├── app/
│   └── streamlit_app.py
│
├── docs/
│   ├── main.tex
│   ├── references.bib
│   ├── sections/
│   └── figures/
│
└── outputs/
    ├── figures/
    ├── tables/
    └── evaluation_results.csv
```

## 5. Dataset

Se trabajara con tres niveles de datos:

### Dataset crudo

Archivos:

```text
data/raw/sicoes_convocatorias_raw.csv
data/raw/sicoes_convocatorias_raw.parquet
```

Debe conservar la respuesta original estructurada del endpoint del SICOES, sin aplicar transformaciones fuertes.

Objetivo:

* trazabilidad;
* reproducibilidad;
* evidencia de extraccion;
* posibilidad de reprocesamiento.

### Dataset limpio

Archivos:

```text
data/processed/sicoes_convocatorias_clean.csv
data/processed/sicoes_convocatorias_clean.parquet
```

Debe contener columnas normalizadas y listas para analisis exploratorio, control de calidad y carga posterior.

### Dataset RAG

Archivos:

```text
data/rag/sicoes_convocatorias_rag.csv
data/rag/sicoes_convocatorias_rag.parquet
```

Debe contener campos limpios y un campo `texto_rag` en lenguaje natural para embeddings, recuperacion semantica y generacion de respuestas.

### Dataset de evaluacion

Adicionalmente, el proyecto debe construir un dataset pequeno y curado de consultas para evaluacion de retrieval.

Archivos sugeridos:

```text
data/evaluation/queries_dev.csv
data/evaluation/queries_val.csv
data/evaluation/queries_test.csv
```

Cada registro de evaluacion deberia incluir al menos:

* `query_id`
* `query_text`
* `relevant_cuce` o lista de CUCE relevantes
* `notes`
* `categoria` opcional

Decision metodologica:

* En este proyecto no se usara una separacion clasica `train/val/test` de documentos como en clasificacion supervisada.
* El corpus indexado puede contener todas las convocatorias vigentes del alcance.
* La separacion principal para experimentacion se hara sobre consultas de evaluacion:
  * `dev`: exploracion de errores y ajustes iniciales;
  * `val`: comparacion de configuraciones e hiperparametros de retrieval;
  * `test`: reporte final congelado para la monografia.

Formato sugerido para `texto_rag`:

```text
Convocatoria publica del SICOES.

CUCE:
26-XXXX-XX-XXXXXXX-X-X

Entidad convocante:
Nombre de la entidad

Tipo de contratacion:
Bienes / Obras / Servicios Generales / Consultoria

Modalidad:
ANPE / CM / LP / OF / CNC

Objeto de contratacion:
Texto completo del objeto de contratacion.

Estado:
Vigente

Fecha de publicacion:
YYYY-MM-DD

Fecha limite de presentacion:
YYYY-MM-DD

Documentos disponibles:
Convocatoria, Documento Base de Contratacion, etc.
```

## 6. Arquitectura objetivo

```text
Parquet RAG dataset
→ PostgreSQL Docker container
→ pgvector extension
→ embeddings almacenados en PostgreSQL
→ busqueda vectorial por similitud
→ linea base SQL con ILIKE
→ LangChain RAG chain
→ Streamlit app
```

Notas:

* PostgreSQL + pgvector es la implementacion principal de base vectorial.
* ChromaDB puede citarse solo como alternativa academica o referencia comparativa, no como implementacion principal.
* LangChain se mantiene como capa de orquestacion para retriever y LLM.

## 7. Objetivo general

Disenar e implementar un sistema inteligente de recuperacion semantica para convocatorias publicas del SICOES mediante tecnicas de Procesamiento de Lenguaje Natural, embeddings, PostgreSQL + pgvector y Retrieval-Augmented Generation, orientado a facilitar la busqueda de oportunidades de contratacion publica para empresas y proveedores.

## 8. Objetivos especificos

1. Extraer convocatorias publicas vigentes del portal SICOES y almacenarlas en un dataset crudo reproducible.
2. Limpiar, normalizar y transformar los datos extraidos para construir un dataset optimizado para recuperacion semantica.
3. Generar representaciones vectoriales de las convocatorias utilizando modelos de embeddings.
4. Implementar PostgreSQL con pgvector para almacenar embeddings y realizar busquedas por similitud semantica.
5. Implementar una linea base de busqueda tradicional usando SQL e `ILIKE`.
6. Desarrollar un prototipo de consulta tipo chatbot mediante LangChain y RAG.
7. Evaluar el desempeno comparando busqueda SQL, busqueda semantica y opcion hibrida.
8. Documentar el desarrollo del proyecto en formato academico usando LaTeX y estilo APA.

## 9. Metodologia

Usar CRISP-DM como metodologia principal.

### 9.1 Business Understanding

Problema:

Los sistemas de busqueda tradicionales del SICOES dependen principalmente de coincidencias textuales, lo que dificulta encontrar convocatorias relevantes cuando el usuario expresa su necesidad con terminos distintos a los usados en el objeto de contratacion.

Ejemplo:

Un proveedor puede buscar "software para hospitales", pero una convocatoria podria estar escrita como "sistema informatico de gestion clinica" o "plataforma digital para administracion hospitalaria".

### 9.2 Data Understanding

Analizar:

* cantidad de convocatorias;
* tipos de contratacion;
* modalidades;
* entidades con mayor numero de procesos;
* longitud del objeto de contratacion;
* distribucion temporal;
* duplicados;
* calidad de datos.

### 9.3 Data Preparation

Procesos:

* limpieza de HTML;
* normalizacion de columnas;
* eliminacion de duplicados;
* conversion de fechas;
* creacion de `document_id`;
* construccion de `texto_rag`;
* generacion de metadata;
* exportacion de datasets en CSV y Parquet.

### 9.4 Modeling

Componentes:

* modelo de embeddings `sentence-transformers/all-MiniLM-L6-v2`;
* PostgreSQL;
* extension pgvector;
* retriever semantico;
* linea base SQL con `ILIKE`;
* opcion de busqueda hibrida con filtros SQL y similitud vectorial;
* LLM;
* cadena RAG con LangChain.

Nota metodologica:

* El proyecto no entrena un modelo supervisado propio.
* El equivalente al ciclo `train/val/test` de clasificacion se traslada aqui a:
  * definicion del corpus indexado;
  * construccion del dataset de consultas etiquetadas;
  * ajuste de retrieval sobre `dev` y `val`;
  * evaluacion final sobre `test`.

### 9.5 Evaluation

Comparar:

* busqueda por palabra clave con `ILIKE`;
* busqueda semantica con pgvector;
* generacion de respuesta con LangChain a partir del contexto recuperado;
* opcion hibrida combinando filtros SQL con similitud vectorial.

Estrategia experimental recomendada:

* Indexar el corpus completo de convocatorias vigentes dentro del alcance.
* No separar documentos en `train/val/test` salvo que se haga un experimento adicional de generalizacion temporal.
* Separar consultas etiquetadas en `dev`, `val` y `test`.
* Usar `dev` para inspeccion cualitativa.
* Usar `val` para elegir:
  * modelo de embeddings;
  * texto indexado (`objeto_contratacion` vs `texto_rag`);
  * `top-k`;
  * filtros por metadata;
  * estrategia baseline SQL vs semantic vs hybrid.
* Usar `test` solo para el reporte final de resultados.

Metricas sugeridas:

* Precision@5;
* Precision@10;
* Recall@K;
* MRR;
* accuracy de recuperacion;
* relevancia manual de resultados;
* ejemplos cualitativos;
* tiempo de respuesta;
* consistencia de la respuesta generada.

### 9.6 Deployment

Implementar un prototipo en Streamlit conectado a PostgreSQL mediante variables de entorno y servicios Docker.

## 10. Tecnologias principales

* Python
* PostgreSQL
* pgvector
* SQLAlchemy
* psycopg
* LangChain
* Sentence Transformers
* Streamlit
* Docker Compose
* LaTeX

## 11. Diagramas textuales para documentacion

1. Pipeline de datos:

```text
SICOES → Raw → Clean → RAG Dataset → PostgreSQL → Embeddings → pgvector
```

2. Arquitectura del sistema RAG:

```text
Usuario → Streamlit → SQL / Vector Search → PostgreSQL + pgvector → LangChain → LLM → Respuesta
```

3. Evaluacion:

```text
Queries dev/val/test → ILIKE baseline / pgvector semantic search / hybrid search → ranking → metricas + analisis de relevancia
```

## 12. Lineamientos de implementacion

* No mezclar extraccion, limpieza, embeddings y aplicacion en un solo notebook.
* Mantener trazabilidad entre dataset crudo, dataset limpio y dataset RAG.
* Usar Parquet como formato principal versionable para trabajo analitico y retrieval.
* Tratar los CSV generados como export auxiliares locales, no como formato canonico principal.
* No versionar artefactos pesados de bases vectoriales fuera de la base de datos si crecen demasiado.
* Mantener separado el texto canonico del dataset, la normalizacion de EDA y el contenido final usado para retrieval.
* Formalizar la evaluacion con consultas etiquetadas en `dev`, `val` y `test`.
* Mantener el enfoque academico, reproducible y mantenible.
