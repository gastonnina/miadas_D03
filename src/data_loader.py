"""Utilidades de carga de datasets del proyecto."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import (
    EVALUATION_DEV_PATH,
    EVALUATION_TEST_PATH,
    EVALUATION_VAL_PATH,
    PRIMARY_PROCESSED_PATH,
    PRIMARY_RAG_PATH,
    PROCESSED_CSV_EXPORT_PATH,
    RAG_CSV_EXPORT_PATH,
    RAG_ID_COLUMN,
    RAG_PRIMARY_KEY,
    RAG_TEXT_COLUMN,
)

PathLike = str | Path

RAG_REQUIRED_COLUMNS = {
    RAG_ID_COLUMN,
    RAG_PRIMARY_KEY,
    "entidad",
    "tipo_contratacion",
    "modalidad",
    "objeto_contratacion",
    "fecha_publicacion_iso",
    "fecha_presentacion_iso",
    "estado",
    RAG_TEXT_COLUMN,
}

EVALUATION_REQUIRED_COLUMNS = {"query_id", "query_text", "relevant_cuce"}


def load_csv(path: PathLike) -> pd.DataFrame:
    """Carga un archivo CSV en un DataFrame."""
    return pd.read_csv(path)


def load_parquet(path: PathLike) -> pd.DataFrame:
    """Carga un archivo Parquet en un DataFrame."""
    return pd.read_parquet(path)


def load_dataframe(path: PathLike) -> pd.DataFrame:
    """Carga un dataset segun su extension."""
    resolved_path = Path(path)
    if resolved_path.suffix.lower() == ".parquet":
        return load_parquet(resolved_path)
    if resolved_path.suffix.lower() == ".csv":
        return load_csv(resolved_path)
    raise ValueError(f"Formato de archivo no soportado: {resolved_path.suffix}")


def ensure_columns(frame: pd.DataFrame, required_columns: set[str], dataset_name: str) -> pd.DataFrame:
    """Valida que un DataFrame contenga las columnas requeridas."""
    missing_columns = sorted(required_columns.difference(frame.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"{dataset_name} no contiene las columnas requeridas: {missing}")
    return frame


def load_processed_dataset(path: PathLike = PRIMARY_PROCESSED_PATH) -> pd.DataFrame:
    """Carga el dataset limpio canonico, priorizando Parquet."""
    return load_dataframe(path)


def load_rag_dataset(path: PathLike = PRIMARY_RAG_PATH) -> pd.DataFrame:
    """Carga el dataset RAG principal, priorizando Parquet."""
    frame = load_dataframe(path)
    return ensure_columns(frame, RAG_REQUIRED_COLUMNS, "dataset RAG")


def load_retrieval_corpus(path: PathLike = PRIMARY_RAG_PATH) -> pd.DataFrame:
    """Carga el corpus que sera indexado para retrieval semantico."""
    return load_rag_dataset(path)


def load_evaluation_queries(split: str = "dev") -> pd.DataFrame:
    """Carga un split de consultas de evaluacion para retrieval."""
    evaluation_paths = {
        "dev": EVALUATION_DEV_PATH,
        "val": EVALUATION_VAL_PATH,
        "test": EVALUATION_TEST_PATH,
    }
    try:
        path = evaluation_paths[split]
    except KeyError as exc:
        valid_splits = ", ".join(evaluation_paths)
        raise ValueError(f"Split de evaluacion invalido: {split}. Usa uno de: {valid_splits}") from exc

    frame = load_dataframe(path)
    return ensure_columns(frame, EVALUATION_REQUIRED_COLUMNS, f"evaluation {split}")


def get_legacy_csv_paths() -> dict[str, Path]:
    """Expone los CSV auxiliares mantenidos por compatibilidad local."""
    return {
        "processed_csv": PROCESSED_CSV_EXPORT_PATH,
        "rag_csv": RAG_CSV_EXPORT_PATH,
    }
