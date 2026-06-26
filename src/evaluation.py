"""Funciones base para evaluacion del sistema."""

from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationResult:
    """Estructura simple para resultados de evaluacion."""

    query: str
    method: str
    score: float


def evaluate_keyword_search() -> list[EvaluationResult]:
    """Evaluara la linea base keyword con SQL e ILIKE."""
    raise NotImplementedError("Evaluacion keyword pendiente de implementacion.")


def evaluate_semantic_search() -> list[EvaluationResult]:
    """Evaluara la busqueda semantica sobre pgvector."""
    raise NotImplementedError("Evaluacion semantica pendiente de implementacion.")


def precision_at_k(relevances: list[int], k: int) -> float:
    """Calcula Precision@k sobre una lista binaria de relevancia."""
    if k <= 0:
        raise ValueError("k debe ser mayor que cero.")
    top_k = relevances[:k]
    if not top_k:
        return 0.0
    return sum(top_k) / len(top_k)
