"""Cadena RAG productiva sobre retrieval configurable y LangChain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ModuleNotFoundError:  # pragma: no cover - depende del entorno local
    ChatGoogleGenerativeAI = None

try:
    from langchain_openai import ChatOpenAI
except ModuleNotFoundError:  # pragma: no cover - depende del entorno local
    ChatOpenAI = None

from src.config import settings
from src.vector_store import hybrid_search, keyword_search, semantic_search

SearchFunction = Callable[[str, int | None, dict[str, Any] | None], list[dict[str, Any]]]

SYSTEM_PROMPT = """
Eres un asistente academico y tecnico especializado en convocatorias publicas del SICOES.
Responde solo con base en el contexto recuperado.
Si el contexto no alcanza para responder con seguridad, dilo explicitamente.
No inventes CUCE, entidades, fechas ni modalidades.
Resume con claridad y cita los CUCE usados como soporte.
""".strip()


@dataclass(slots=True)
class RAGResponse:
    """Respuesta estructurada de la cadena RAG."""

    question: str
    retrieval_mode: str
    answer: str
    context: str
    sources: list[dict[str, Any]]


def _resolve_retrieval_mode(retrieval_mode: str | None = None) -> str:
    """Valida y normaliza el modo de retrieval configurado."""
    resolved_mode = (retrieval_mode or settings.default_retrieval_mode).strip().lower()
    valid_modes = {"keyword", "semantic", "hybrid"}
    if resolved_mode not in valid_modes:
        valid_values = ", ".join(sorted(valid_modes))
        raise ValueError(f"Modo de retrieval invalido: {resolved_mode}. Usa uno de: {valid_values}")
    return resolved_mode


def _get_search_function(retrieval_mode: str | None = None) -> SearchFunction:
    """Mapea el modo de retrieval a la funcion productiva correspondiente."""
    resolved_mode = _resolve_retrieval_mode(retrieval_mode)
    search_functions: dict[str, SearchFunction] = {
        "keyword": keyword_search,
        "semantic": semantic_search,
        "hybrid": hybrid_search,
    }
    return search_functions[resolved_mode]


def _normalize_source(item: dict[str, Any]) -> dict[str, Any]:
    """Reduce el payload de retrieval al subconjunto necesario para RAG."""
    return {
        "cuce": item.get("cuce"),
        "entidad": item.get("entidad"),
        "tipo_contratacion": item.get("tipo_contratacion"),
        "modalidad": item.get("modalidad"),
        "objeto_contratacion": item.get("objeto_contratacion"),
        "estado": item.get("estado"),
        "fecha_publicacion": item.get("fecha_publicacion"),
        "fecha_presentacion": item.get("fecha_presentacion"),
        "ficha_url": item.get("ficha_url"),
        "texto_rag": item.get("texto_rag"),
        "score": item.get("score"),
        "distance": item.get("distance"),
    }


def retrieve_documents(
    question: str,
    *,
    retrieval_mode: str | None = None,
    k: int | None = None,
    metadata_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Recupera documentos usando el modo configurado."""
    if not question.strip():
        raise ValueError("La pregunta no puede estar vacia.")
    search_fn = _get_search_function(retrieval_mode)
    results = search_fn(question.strip(), k, metadata_filters)
    return [_normalize_source(item) for item in results]


def format_sources_as_context(sources: list[dict[str, Any]]) -> str:
    """Transforma resultados recuperados en un contexto textual para el LLM."""
    if not sources:
        return "No se recuperaron convocatorias relevantes para esta consulta."

    context_blocks: list[str] = []
    for index, source in enumerate(sources, start=1):
        block = "\n".join(
            [
                f"Documento {index}",
                f"CUCE: {source.get('cuce') or 'N/D'}",
                f"Entidad: {source.get('entidad') or 'N/D'}",
                f"Tipo de contratacion: {source.get('tipo_contratacion') or 'N/D'}",
                f"Modalidad: {source.get('modalidad') or 'N/D'}",
                f"Estado: {source.get('estado') or 'N/D'}",
                f"Fecha de publicacion: {source.get('fecha_publicacion') or 'N/D'}",
                f"Fecha de presentacion: {source.get('fecha_presentacion') or 'N/D'}",
                f"Objeto de contratacion: {source.get('objeto_contratacion') or 'N/D'}",
                f"Ficha URL: {source.get('ficha_url') or 'N/D'}",
                f"Texto RAG: {source.get('texto_rag') or 'N/D'}",
            ]
        )
        context_blocks.append(block)

    context = "\n\n".join(context_blocks)
    return context[: settings.rag_max_context_chars]


def build_context(
    question: str,
    *,
    retrieval_mode: str | None = None,
    k: int | None = None,
    metadata_filters: dict[str, Any] | None = None,
) -> str:
    """Construye el contexto RAG a partir de documentos recuperados."""
    sources = retrieve_documents(
        question,
        retrieval_mode=retrieval_mode,
        k=k,
        metadata_filters=metadata_filters,
    )
    return format_sources_as_context(sources)


def get_chat_model(
    *,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    temperature: float | None = None,
) -> Any:
    """Instancia el proveedor de chat configurado."""
    provider = (llm_provider or settings.llm_provider).strip().lower()
    model = llm_model or settings.llm_model
    resolved_temperature = settings.llm_temperature if temperature is None else temperature

    if provider == "gemini":
        if ChatGoogleGenerativeAI is None:
            raise RuntimeError(
                "langchain-google-genai no esta disponible en el entorno actual."
            )
        if not settings.google_api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY no esta configurada. Define la variable en tu `.env`."
            )
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=resolved_temperature,
            google_api_key=settings.google_api_key,
        )

    if provider == "openai":
        if ChatOpenAI is None:
            raise RuntimeError("langchain-openai no esta disponible en el entorno actual.")
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY no esta configurada. Define la variable en tu `.env`."
            )
        return ChatOpenAI(
            model=model,
            temperature=resolved_temperature,
            api_key=settings.openai_api_key,
        )

    raise ValueError(f"Proveedor LLM no soportado: {provider}")


def build_prompt_template() -> ChatPromptTemplate:
    """Construye el prompt base de la cadena RAG."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                (
                    "Pregunta del usuario:\n{question}\n\n"
                    "Modo de retrieval usado: {retrieval_mode}\n\n"
                    "Contexto recuperado:\n{context}\n\n"
                    "Responde en espanol. Si es posible, incluye una lista breve de convocatorias "
                    "relevantes con su CUCE y explica por que son pertinentes."
                ),
            ),
        ]
    )


def answer_question(
    question: str,
    *,
    retrieval_mode: str | None = None,
    k: int | None = None,
    metadata_filters: dict[str, Any] | None = None,
) -> RAGResponse:
    """Genera una respuesta RAG usando retrieval configurable y un LLM."""
    resolved_mode = _resolve_retrieval_mode(retrieval_mode)
    sources = retrieve_documents(
        question,
        retrieval_mode=resolved_mode,
        k=k,
        metadata_filters=metadata_filters,
    )
    context = format_sources_as_context(sources)
    prompt = build_prompt_template()
    chat_model = get_chat_model()
    chain = prompt | chat_model | StrOutputParser()
    answer = chain.invoke(
        {
            "question": question.strip(),
            "retrieval_mode": resolved_mode,
            "context": context,
        }
    )
    return RAGResponse(
        question=question.strip(),
        retrieval_mode=resolved_mode,
        answer=answer,
        context=context,
        sources=sources,
    )
