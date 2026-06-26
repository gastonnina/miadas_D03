# Sistema RAG para SICOES

Proyecto de monografia de diplomado para construir un sistema inteligente de recuperacion semantica de convocatorias publicas del portal SICOES de Bolivia mediante NLP, embeddings, PostgreSQL + pgvector, LangChain y Retrieval-Augmented Generation.

## Descripcion

El proyecto busca comparar tres modos de consulta sobre convocatorias publicas:

* `keyword search`: busqueda tradicional con SQL e `ILIKE`.
* `semantic search`: busqueda por similitud vectorial usando embeddings almacenados en PostgreSQL con `pgvector`.
* `RAG answer generation`: recuperacion de contexto y respuesta generada por un LLM orquestado con LangChain.

## Arquitectura

```text
CSV RAG dataset
→ PostgreSQL Docker container
→ pgvector extension
→ embeddings almacenados en PostgreSQL
→ vector similarity search using pgvector
→ SQL baseline search using ILIKE
→ LangChain RAG chain
→ Streamlit app
```

LangChain se mantiene como capa de orquestacion para desacoplar la logica de recuperacion y permitir cambiar de proveedor de LLM con cambios minimos.

## Estructura

```text
.
├── app/
│   └── streamlit_app.py
├── db/
│   └── init/
│       └── 01_init_pgvector.sql
├── data/
│   ├── processed/
│   ├── rag/
│   └── raw/
├── docs/
├── notebooks/
│   ├── 01_extract_sicoes.ipynb
│   ├── 02_clean_transform_rag.ipynb
│   ├── 03_eda.ipynb
│   ├── 04_embeddings_pgvector.ipynb
│   └── 05_rag_evaluation.ipynb
├── outputs/
├── src/
├── .env.example
├── docker-compose.yml
├── pyproject.toml
└── requirements.txt
```

## Setup

1. Crear el entorno virtual con `uv`:

```bash
uv venv .venv
source .venv/bin/activate
uv sync
```

Nota para equipos sin GPU dedicada:

* Este proyecto fuerza `torch` desde el índice CPU-only de PyTorch cuando usas `uv sync`.
* Si ya viste descargas de paquetes `nvidia-*`, lo más probable es que correspondan a una instalación previa o a una resolución anterior del entorno.
* En ese caso conviene recrear el entorno:

```bash
rm -rf .venv
uv venv .venv
source .venv/bin/activate
uv sync --refresh
```

2. Alternativa compatible con `venv`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En instalación manual con `pip`, `sentence-transformers` puede arrastrar una variante de `torch` más pesada. Si tu equipo es CPU-only, prioriza el flujo con `uv`.

3. Crear variables de entorno:

```bash
cp .env.example .env
```

## PostgreSQL + pgvector

Levantar la base de datos:

```bash
docker compose up -d
```

La configuracion base es:

* base de datos: `sicoes_rag`
* usuario: `postgres`
* password: `postgres`
* puerto: `5432`

El script [db/init/01_init_pgvector.sql](/var/www/codigo/maestria_ia/umsa/diplomados_intermedios/dip_03/db/init/01_init_pgvector.sql) crea la extension `vector`, la tabla `convocatorias` y sus indices iniciales.

## Notebooks

Flujo sugerido:

1. [01_extract_sicoes.ipynb](/var/www/codigo/maestria_ia/umsa/diplomados_intermedios/dip_03/notebooks/01_extract_sicoes.ipynb): descarga y guarda el dataset crudo.
2. [02_clean_transform_rag.ipynb](/var/www/codigo/maestria_ia/umsa/diplomados_intermedios/dip_03/notebooks/02_clean_transform_rag.ipynb): limpieza, normalizacion y construccion de `texto_rag`.
3. [03_eda.ipynb](/var/www/codigo/maestria_ia/umsa/diplomados_intermedios/dip_03/notebooks/03_eda.ipynb): analisis exploratorio del dataset limpio.
4. [04_embeddings_pgvector.ipynb](/var/www/codigo/maestria_ia/umsa/diplomados_intermedios/dip_03/notebooks/04_embeddings_pgvector.ipynb): base para carga en PostgreSQL y generacion de embeddings.
5. [05_rag_evaluation.ipynb](/var/www/codigo/maestria_ia/umsa/diplomados_intermedios/dip_03/notebooks/05_rag_evaluation.ipynb): evaluacion comparativa de modos de busqueda.

Para abrir notebooks con el entorno del proyecto:

```bash
uv run jupyter lab
```

o

```bash
jupyter lab
```

## Streamlit

La aplicacion actual es un placeholder de scaffold. Para ejecutarla:

```bash
streamlit run app/streamlit_app.py
```

## Monografia en LaTeX

La documentacion academica vive en `docs/` y puede compilarse desde la raiz con `make`:

```bash
make quick
```

Targets utiles:

* `make quick`: compilacion rapida con `pdflatex`.
* `make all`: compilacion completa de la monografia.
* `make bib`: alias de compilacion completa.
* `make clean`: limpia auxiliares de LaTeX.
* `make logs`: muestra las ultimas lineas de `docs/main.log`.
* `make format`: formatea archivos `.tex` con `latexindent`.
* `make copy-pdf`: copia el PDF compilado a la raiz del proyecto.

Para depurar errores de LaTeX, el flujo recomendado es:

```bash
make quick
make logs
```

## Modos de busqueda

### Keyword search

Consulta tradicional basada en coincidencias textuales usando SQL e `ILIKE`.

### Semantic search

Consulta por similitud semantica usando embeddings y operadores vectoriales de `pgvector`.

### RAG answer generation

Recupera convocatorias relevantes, construye contexto y genera una respuesta con LangChain y un LLM configurable.

## Estado actual

Este repositorio contiene el scaffold academico y tecnico actualizado a PostgreSQL + pgvector. No implementa todavia la aplicacion final, pero deja preparada la siguiente fase para cargar el CSV RAG en PostgreSQL y generar embeddings.
