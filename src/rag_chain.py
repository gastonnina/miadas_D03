"""Placeholders para la cadena RAG sobre LangChain."""

from typing import Any


def get_chat_model() -> Any:
    """Instanciara el proveedor de chat configurado."""
    raise NotImplementedError("Seleccion de modelo de chat pendiente de implementacion.")


def build_context(question: str) -> str:
    """Construira el contexto recuperado para una pregunta."""
    raise NotImplementedError("Construccion de contexto RAG pendiente de implementacion.")


def answer_question(question: str) -> str:
    """Generara una respuesta usando LangChain y contexto recuperado."""
    raise NotImplementedError(f"Respuesta RAG pendiente de implementacion para: {question}")
