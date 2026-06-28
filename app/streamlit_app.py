"""Aplicacion Streamlit funcional para consulta RAG sobre SICOES."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import settings
from src.rag_chain import answer_question, build_context, retrieve_documents


def _parse_metadata_filters(raw_filters: str) -> dict[str, Any] | None:
    """Parsea filtros simples desde texto libre."""
    stripped_filters = raw_filters.strip()
    if not stripped_filters:
        return None

    filters: dict[str, Any] = {}
    for item in stripped_filters.split(";"):
        if "=" not in item:
            continue
        key, raw_value = item.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key or not raw_value:
            continue
        if "|" in raw_value:
            filters[key] = [part.strip() for part in raw_value.split("|") if part.strip()]
        else:
            filters[key] = raw_value
    return filters or None


def _sources_to_frame(sources: list[dict[str, Any]]) -> pd.DataFrame:
    """Convierte fuentes recuperadas a tabla amigable para Streamlit."""
    if not sources:
        return pd.DataFrame()
    frame = pd.DataFrame(sources)
    preferred_columns = [
        "cuce",
        "entidad",
        "tipo_contratacion",
        "modalidad",
        "estado",
        "fecha_publicacion",
        "fecha_presentacion",
        "score",
        "distance",
        "objeto_contratacion",
        "ficha_url",
    ]
    available_columns = [column for column in preferred_columns if column in frame.columns]
    return frame[available_columns]


def _show_sidebar() -> tuple[str, int, dict[str, Any] | None, bool]:
    """Renderiza la configuracion lateral."""
    st.sidebar.header("Configuracion")
    retrieval_mode = st.sidebar.selectbox(
        "Modo de retrieval",
        options=["keyword", "semantic", "hybrid"],
        index=["keyword", "semantic", "hybrid"].index(settings.default_retrieval_mode),
        help="Selecciona la estrategia de recuperación usada antes de la respuesta RAG.",
    )
    top_k = st.sidebar.slider(
        "Top K",
        min_value=1,
        max_value=10,
        value=settings.retrieval_top_k,
        help="Cantidad maxima de convocatorias recuperadas.",
    )
    raw_filters = st.sidebar.text_input(
        "Metadata filters",
        value="",
        help="Formato: campo=valor;campo2=valor2 o modalidad=ANPE|CNC",
    )
    generate_rag = st.sidebar.checkbox(
        "Generar respuesta RAG",
        value=True,
        help="Si no hay API key configurada, puedes desactivar esta opcion y usar solo retrieval.",
    )

    st.sidebar.divider()
    st.sidebar.caption(f"LLM provider actual: `{settings.llm_provider}`")
    st.sidebar.caption(f"LLM model actual: `{settings.llm_model}`")
    st.sidebar.caption(f"Default retrieval: `{settings.default_retrieval_mode}`")

    return retrieval_mode, top_k, _parse_metadata_filters(raw_filters), generate_rag


def _show_configuration_warnings(generate_rag: bool) -> None:
    """Muestra advertencias de configuracion relevantes."""
    if not generate_rag:
        st.info(
            "La generacion RAG esta desactivada. La interfaz funcionara en modo retrieval puro."
        )
        return

    if settings.llm_provider == "gemini" and not settings.google_api_key:
        st.warning(
            "Falta `GOOGLE_API_KEY` en tu `.env`. Puedes seguir explorando retrieval o configurar "
            "la clave para generar respuestas RAG."
        )
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        st.warning(
            "Falta `OPENAI_API_KEY` en tu `.env`. Puedes seguir explorando retrieval o configurar "
            "la clave para generar respuestas RAG."
        )


def main() -> None:
    st.set_page_config(page_title="SICOES RAG", layout="wide")
    st.title("Sistema RAG para convocatorias del SICOES")
    st.caption(
        "Consulta convocatorias mediante retrieval keyword, semántico o híbrido, con respuesta "
        "RAG opcional y trazabilidad a las fuentes recuperadas."
    )

    retrieval_mode, top_k, metadata_filters, generate_rag = _show_sidebar()
    _show_configuration_warnings(generate_rag)

    default_question = "medicamentos para hospital en santa cruz"
    question = st.text_area(
        "Pregunta o necesidad de búsqueda",
        value=default_question,
        height=110,
        help="Ejemplo: reactivos de laboratorio para hospital o alcantarillado pluvial en la paz",
    )

    run_button = st.button("Consultar", type="primary", use_container_width=True)
    if not run_button:
        st.subheader("Capacidades")
        st.write(
            [
                "Búsqueda keyword mejorada por tokens",
                "Búsqueda semántica sobre pgvector",
                "Búsqueda híbrida con reranking semántico",
                "Construcción de contexto RAG con fuentes trazables",
                "Generación opcional de respuesta con Gemini u OpenAI",
            ]
        )
        return

    if not question.strip():
        st.error("La pregunta no puede estar vacía.")
        return

    try:
        with st.spinner("Recuperando convocatorias relevantes..."):
            sources = retrieve_documents(
                question,
                retrieval_mode=retrieval_mode,
                k=top_k,
                metadata_filters=metadata_filters,
            )
            context = build_context(
                question,
                retrieval_mode=retrieval_mode,
                k=top_k,
                metadata_filters=metadata_filters,
            )
    except Exception as exc:
        st.error(f"Fallo en retrieval: {exc}")
        return

    st.subheader("Fuentes recuperadas")
    st.caption(f"Modo usado: `{retrieval_mode}` | resultados: `{len(sources)}`")

    sources_frame = _sources_to_frame(sources)
    if sources_frame.empty:
        st.warning("No se recuperaron convocatorias para esta consulta.")
    else:
        st.dataframe(sources_frame, use_container_width=True, hide_index=True)

    with st.expander("Ver contexto RAG construido", expanded=False):
        st.text(context)

    if not generate_rag:
        return

    try:
        with st.spinner("Generando respuesta RAG..."):
            response = answer_question(
                question,
                retrieval_mode=retrieval_mode,
                k=top_k,
                metadata_filters=metadata_filters,
            )
    except Exception as exc:
        st.error(f"No fue posible generar la respuesta RAG: {exc}")
        return

    st.subheader("Respuesta RAG")
    st.write(response.answer)

    with st.expander("Ver fuentes normalizadas", expanded=False):
        st.json(response.sources)


if __name__ == "__main__":
    main()
