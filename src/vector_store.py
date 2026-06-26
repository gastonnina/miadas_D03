"""Placeholders para almacenamiento vectorial en PostgreSQL + pgvector."""

from collections.abc import Iterable
from typing import Any


def connect_db() -> Any:
    """Creara la conexion a PostgreSQL en una etapa posterior."""
    raise NotImplementedError("Conexion a PostgreSQL pendiente de implementacion.")


def create_schema_if_needed() -> None:
    """Creara extension, tablas e indices si no existen."""
    raise NotImplementedError("Creacion de esquema pgvector pendiente de implementacion.")


def insert_convocatorias(rows: Iterable[dict[str, Any]]) -> None:
    """Insertara convocatorias normalizadas en PostgreSQL."""
    raise NotImplementedError("Insercion de convocatorias pendiente de implementacion.")


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generara embeddings para los textos del dataset."""
    raise NotImplementedError("Generacion de embeddings pendiente de implementacion.")


def semantic_search(query: str, k: int = 5) -> list[dict[str, Any]]:
    """Ejecutara busqueda semantica usando pgvector."""
    raise NotImplementedError("Busqueda semantica con pgvector pendiente de implementacion.")


def keyword_search(query: str, k: int = 5) -> list[dict[str, Any]]:
    """Ejecutara busqueda tradicional con SQL e ILIKE."""
    raise NotImplementedError("Busqueda keyword con ILIKE pendiente de implementacion.")
