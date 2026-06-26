"""Configuracion central del proyecto."""

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RAG_DIR = DATA_DIR / "rag"

RAW_JSONL_PATH = RAW_DIR / "sicoes_convocatorias_raw.jsonl"
RAW_PARQUET_PATH = RAW_DIR / "sicoes_convocatorias_raw.parquet"
RAW_CSV_EXPORT_PATH = RAW_DIR / "sicoes_convocatorias_raw.csv"

PROCESSED_PARQUET_PATH = PROCESSED_DIR / "sicoes_convocatorias_clean.parquet"
PROCESSED_CSV_EXPORT_PATH = PROCESSED_DIR / "sicoes_convocatorias_clean.csv"

RAG_PARQUET_PATH = RAG_DIR / "sicoes_convocatorias_rag.parquet"
RAG_CSV_EXPORT_PATH = RAG_DIR / "sicoes_convocatorias_rag.csv"

VECTOR_STORE_DIR = ROOT_DIR / "outputs" / "vector_store"


@dataclass(slots=True)
class Settings:
    """Configuracion basada en variables de entorno."""

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/sicoes_rag",
    )
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")


settings = Settings()
