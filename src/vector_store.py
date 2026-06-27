"""Capa productiva de almacenamiento vectorial sobre PostgreSQL + pgvector."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from pgvector.sqlalchemy import Vector
except ModuleNotFoundError:  # pragma: no cover - depende del entorno local
    Vector = None

try:
    from sentence_transformers import SentenceTransformer
except ModuleNotFoundError:  # pragma: no cover - depende del entorno local
    SentenceTransformer = None

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    and_,
    create_engine,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.sql import Select

from src.config import (
    RAG_ID_COLUMN,
    RAG_PRIMARY_KEY,
    RAG_TEXT_COLUMN,
    ROOT_DIR,
    settings,
)

EMBEDDING_DIMENSION = 384
SQL_INIT_PATH = ROOT_DIR / "db" / "init" / "01_init_pgvector.sql"

metadata = MetaData()


def _require_pgvector() -> None:
    """Valida que la dependencia de pgvector este disponible."""
    if Vector is None:
        raise RuntimeError(
            "La dependencia `pgvector` no esta disponible en el entorno actual. "
            "Instala las dependencias del proyecto antes de usar `src.vector_store`."
        )


def _require_sentence_transformers() -> None:
    """Valida que sentence-transformers este disponible."""
    if SentenceTransformer is None:
        raise RuntimeError(
            "La dependencia `sentence-transformers` no esta disponible en el entorno actual. "
            "Instala las dependencias del proyecto antes de generar embeddings."
        )


def _validate_embedding_dimension(embedding: Sequence[float]) -> None:
    """Falla temprano si la dimension del embedding no coincide con el esquema."""
    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            "La dimension del embedding no coincide con el esquema pgvector. "
            f"Esperada: {EMBEDDING_DIMENSION}. Obtenida: {len(embedding)}. "
            "Revisa `EMBEDDING_MODEL` o ajusta el esquema de la columna `embedding`."
        )


convocatorias_table = Table(
    "convocatorias",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("document_id", Text, nullable=False, unique=True),
    Column("cuce", Text),
    Column("entidad", Text),
    Column("tipo_contratacion", Text),
    Column("modalidad", Text),
    Column("objeto_contratacion", Text),
    Column("estado", Text),
    Column("fecha_publicacion", Date, nullable=True),
    Column("fecha_presentacion", Date, nullable=True),
    Column("archivos_disponibles", Text, nullable=True),
    Column("ficha_url", Text, nullable=True),
    Column(RAG_TEXT_COLUMN, Text, nullable=False),
    Column("metadata_json", JSON, nullable=True),
    Column("embedding", Vector(EMBEDDING_DIMENSION) if Vector else Text, nullable=True),
    Column("created_at", DateTime, server_default=func.current_timestamp(), nullable=False),
    Index("ux_convocatorias_document_id", "document_id", unique=True),
    Index("ix_convocatorias_cuce", "cuce"),
    Index("ix_convocatorias_entidad", "entidad"),
    Index("ix_convocatorias_tipo_contratacion", "tipo_contratacion"),
    Index("ix_convocatorias_modalidad", "modalidad"),
    Index("ix_convocatorias_estado", "estado"),
)


def _parse_iso_date(value: Any) -> date | None:
    """Convierte una fecha ISO o vacia a `date`."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    cleaned_value = str(value).strip()
    if not cleaned_value:
        return None
    return date.fromisoformat(cleaned_value)


def _clean_optional_text(value: Any) -> str | None:
    """Normaliza strings vacios a `None` para almacenamiento relacional."""
    if value is None:
        return None
    cleaned_value = str(value).strip()
    return cleaned_value or None


def _coerce_metadata_filters(filters: dict[str, Any] | None) -> list[Any]:
    """Traduce filtros simples a expresiones SQLAlchemy."""
    if not filters:
        return []

    filter_expressions: list[Any] = []
    for field, value in filters.items():
        column = convocatorias_table.c.get(field)
        if column is None:
            raise ValueError(f"Filtro de metadata no soportado: {field}")

        if value is None:
            continue
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            values = [item for item in value if item is not None]
            if values:
                filter_expressions.append(column.in_(values))
            continue
        filter_expressions.append(column == value)

    return filter_expressions


def _build_search_payload(row: Any, score_field: str, score_value: float | None) -> dict[str, Any]:
    """Convierte una fila relacional en el payload comun de respuesta."""
    payload = {
        "id": row.id,
        "document_id": row.document_id,
        "cuce": row.cuce,
        "entidad": row.entidad,
        "tipo_contratacion": row.tipo_contratacion,
        "modalidad": row.modalidad,
        "objeto_contratacion": row.objeto_contratacion,
        "estado": row.estado,
        "fecha_publicacion": row.fecha_publicacion.isoformat() if row.fecha_publicacion else None,
        "fecha_presentacion": (
            row.fecha_presentacion.isoformat() if row.fecha_presentacion else None
        ),
        "archivos_disponibles": row.archivos_disponibles,
        "ficha_url": row.ficha_url,
        RAG_TEXT_COLUMN: getattr(row, RAG_TEXT_COLUMN),
        "metadata_json": row.metadata_json,
    }
    if score_value is not None:
        payload[score_field] = float(score_value)
    return payload


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str | None = None) -> SentenceTransformer:
    """Carga y cachea el modelo de embeddings configurado."""
    _require_sentence_transformers()
    resolved_model_name = model_name or settings.embedding_model
    return SentenceTransformer(resolved_model_name)


@lru_cache(maxsize=1)
def connect_db(database_url: str | None = None) -> Engine:
    """Crea y cachea el engine SQLAlchemy hacia PostgreSQL."""
    resolved_database_url = database_url or settings.database_url
    return create_engine(resolved_database_url, future=True)


def create_schema_if_needed(sql_init_path: str | Path = SQL_INIT_PATH) -> None:
    """Crea extension, tabla e indices si no existen."""
    _require_pgvector()
    engine = connect_db()
    init_sql = Path(sql_init_path).read_text(encoding="utf-8")
    statements = [statement.strip() for statement in init_sql.split(";") if statement.strip()]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Genera embeddings para una lista de textos."""
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    embedding_list = embeddings.tolist()
    if embedding_list:
        _validate_embedding_dimension(embedding_list[0])
    return embedding_list


def prepare_convocatoria_record(
    row: dict[str, Any],
    embedding: list[float] | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normaliza un registro del dataset RAG al esquema relacional."""
    if RAG_ID_COLUMN not in row:
        raise ValueError(f"Cada registro debe incluir `{RAG_ID_COLUMN}`.")
    if RAG_TEXT_COLUMN not in row:
        raise ValueError(f"Cada registro debe incluir `{RAG_TEXT_COLUMN}`.")

    inferred_metadata = metadata_json or {
        "source": "sicoes_rag_dataset",
        "cuce": row.get(RAG_PRIMARY_KEY),
        "estado": row.get("estado"),
        "tipo_contratacion": row.get("tipo_contratacion"),
        "modalidad": row.get("modalidad"),
    }

    return {
        "document_id": row[RAG_ID_COLUMN],
        "cuce": _clean_optional_text(row.get(RAG_PRIMARY_KEY)),
        "entidad": _clean_optional_text(row.get("entidad")),
        "tipo_contratacion": _clean_optional_text(row.get("tipo_contratacion")),
        "modalidad": _clean_optional_text(row.get("modalidad")),
        "objeto_contratacion": _clean_optional_text(row.get("objeto_contratacion")),
        "estado": _clean_optional_text(row.get("estado")),
        "fecha_publicacion": _parse_iso_date(row.get("fecha_publicacion_iso")),
        "fecha_presentacion": _parse_iso_date(row.get("fecha_presentacion_iso")),
        "archivos_disponibles": _clean_optional_text(row.get("archivos_disponibles")),
        "ficha_url": _clean_optional_text(row.get("ficha_url")),
        RAG_TEXT_COLUMN: str(row[RAG_TEXT_COLUMN]).strip(),
        "metadata_json": inferred_metadata,
        "embedding": embedding,
    }


def insert_convocatorias(
    rows: Iterable[dict[str, Any]],
    *,
    generate_missing_embeddings: bool = True,
    upsert: bool = True,
) -> int:
    """Inserta o actualiza convocatorias normalizadas en PostgreSQL."""
    _require_pgvector()
    normalized_rows = list(rows)
    if not normalized_rows:
        return 0

    embeddings_by_index: list[list[float] | None] = [None] * len(normalized_rows)
    pending_texts: list[str] = []
    pending_indices: list[int] = []

    for index, row in enumerate(normalized_rows):
        existing_embedding = row.get("embedding")
        if existing_embedding is not None:
            _validate_embedding_dimension(existing_embedding)
            embeddings_by_index[index] = existing_embedding
            continue
        if generate_missing_embeddings:
            pending_indices.append(index)
            pending_texts.append(str(row[RAG_TEXT_COLUMN]))

    if pending_texts:
        generated_embeddings = generate_embeddings(pending_texts)
        for row_index, embedding in zip(pending_indices, generated_embeddings, strict=True):
            embeddings_by_index[row_index] = embedding

    prepared_rows = [
        prepare_convocatoria_record(
            row,
            embedding=embeddings_by_index[index],
            metadata_json=row.get("metadata_json"),
        )
        for index, row in enumerate(normalized_rows)
    ]

    engine = connect_db()
    statement = insert(convocatorias_table).values(prepared_rows)
    if upsert:
        statement = statement.on_conflict_do_update(
            index_elements=["document_id"],
            set_={
                "cuce": statement.excluded.cuce,
                "entidad": statement.excluded.entidad,
                "tipo_contratacion": statement.excluded.tipo_contratacion,
                "modalidad": statement.excluded.modalidad,
                "objeto_contratacion": statement.excluded.objeto_contratacion,
                "estado": statement.excluded.estado,
                "fecha_publicacion": statement.excluded.fecha_publicacion,
                "fecha_presentacion": statement.excluded.fecha_presentacion,
                "archivos_disponibles": statement.excluded.archivos_disponibles,
                "ficha_url": statement.excluded.ficha_url,
                RAG_TEXT_COLUMN: statement.excluded.texto_rag,
                "metadata_json": statement.excluded.metadata_json,
                "embedding": statement.excluded.embedding,
            },
        )

    with engine.begin() as connection:
        connection.execute(statement)
    return len(prepared_rows)


def _apply_common_filters(
    statement: Select[Any],
    metadata_filters: dict[str, Any] | None,
) -> Select[Any]:
    """Aplica filtros de metadata comunes a una consulta."""
    filter_expressions = _coerce_metadata_filters(metadata_filters)
    if filter_expressions:
        statement = statement.where(and_(*filter_expressions))
    return statement


def semantic_search(
    query: str,
    k: int | None = None,
    metadata_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Ejecuta busqueda semantica usando distancia coseno de pgvector."""
    _require_pgvector()
    top_k = k or settings.retrieval_top_k
    query_embedding = generate_embeddings([query])[0]
    distance = convocatorias_table.c.embedding.cosine_distance(query_embedding)

    statement = (
        select(convocatorias_table, distance.label("distance"))
        .where(convocatorias_table.c.embedding.is_not(None))
        .order_by(distance.asc())
        .limit(top_k)
    )
    statement = _apply_common_filters(statement, metadata_filters)

    engine = connect_db()
    with engine.begin() as connection:
        rows = connection.execute(statement).all()

    return [_build_search_payload(row, "distance", row.distance) for row in rows]


def keyword_search(
    query: str,
    k: int | None = None,
    metadata_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Ejecuta busqueda keyword usando ILIKE sobre campos relevantes."""
    top_k = k or settings.retrieval_top_k
    search_pattern = f"%{query.strip()}%"

    statement = (
        select(convocatorias_table)
        .where(
            or_(
                convocatorias_table.c.texto_rag.ilike(search_pattern),
                convocatorias_table.c.objeto_contratacion.ilike(search_pattern),
                convocatorias_table.c.entidad.ilike(search_pattern),
                convocatorias_table.c.cuce.ilike(search_pattern),
            )
        )
        .order_by(convocatorias_table.c.fecha_publicacion.desc().nullslast())
        .limit(top_k)
    )
    statement = _apply_common_filters(statement, metadata_filters)

    engine = connect_db()
    with engine.begin() as connection:
        rows = connection.execute(statement).all()

    return [_build_search_payload(row, "score", None) for row in rows]
