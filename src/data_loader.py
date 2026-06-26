"""Utilidades base para carga de datos."""

from pathlib import Path

import pandas as pd

from src.config import RAG_CSV_EXPORT_PATH


def load_csv(path: str | Path) -> pd.DataFrame:
    """Carga un archivo CSV en un DataFrame."""
    return pd.read_csv(path)


def load_parquet(path: str | Path) -> pd.DataFrame:
    """Carga un archivo Parquet en un DataFrame."""
    return pd.read_parquet(path)


def load_rag_dataset(path: str | Path = RAG_CSV_EXPORT_PATH) -> pd.DataFrame:
    """Carga el dataset RAG principal desde CSV."""
    return pd.read_csv(path)
