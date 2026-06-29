"""Configuracion central del proyecto."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RAG_DIR = DATA_DIR / "rag"
EVALUATION_DIR = DATA_DIR / "evaluation"
OUTPUTS_DIR = ROOT_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
TABLES_DIR = OUTPUTS_DIR / "tables"
RUN_SUMMARIES_DIR = OUTPUTS_DIR / "run_summaries"

RAW_JSONL_PATH = RAW_DIR / "sicoes_convocatorias_raw.jsonl"
RAW_PARQUET_PATH = RAW_DIR / "sicoes_convocatorias_raw.parquet"
RAW_CSV_EXPORT_PATH = RAW_DIR / "sicoes_convocatorias_raw.csv"

PROCESSED_PARQUET_PATH = PROCESSED_DIR / "sicoes_convocatorias_clean.parquet"
PROCESSED_CSV_EXPORT_PATH = PROCESSED_DIR / "sicoes_convocatorias_clean.csv"

RAG_PARQUET_PATH = RAG_DIR / "sicoes_convocatorias_rag.parquet"
RAG_CSV_EXPORT_PATH = RAG_DIR / "sicoes_convocatorias_rag.csv"

EVALUATION_DEV_PATH = EVALUATION_DIR / "queries_dev.csv"
EVALUATION_VAL_PATH = EVALUATION_DIR / "queries_val.csv"
EVALUATION_TEST_PATH = EVALUATION_DIR / "queries_test.csv"

PRIMARY_RAW_PATH = RAW_PARQUET_PATH
PRIMARY_PROCESSED_PATH = PROCESSED_PARQUET_PATH
PRIMARY_RAG_PATH = RAG_PARQUET_PATH

RAG_TEXT_COLUMN = "texto_rag"
RAG_ID_COLUMN = "document_id"
RAG_PRIMARY_KEY = "cuce"


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
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    default_retrieval_mode: str = os.getenv("DEFAULT_RETRIEVAL_MODE", "keyword")
    rag_max_context_chars: int = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "12000"))
    ntfy_enabled: bool = os.getenv("NTFY_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    ntfy_server: str = os.getenv("NTFY_SERVER", "https://ntf.sh").rstrip("/")
    ntfy_topic: str = os.getenv("NTFY_TOPIC", "").strip()
    ntfy_token: str = os.getenv("NTFY_TOKEN", "").strip()


settings = Settings()
