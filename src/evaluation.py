"""Utilidades de evaluacion para retrieval keyword y semantico."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Callable

import pandas as pd

from src.data_loader import load_evaluation_queries
from src.vector_store import keyword_search, semantic_search

SearchFunction = Callable[[str, int | None, dict[str, Any] | None], list[dict[str, Any]]]


@dataclass(slots=True)
class EvaluationResult:
    """Resultado detallado de evaluacion por consulta y metodo."""

    query_id: str
    query_text: str
    method: str
    k: int
    relevant_cuces: list[str]
    retrieved_cuces: list[str]
    relevances: list[int]
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    hit_at_k: float


@dataclass(slots=True)
class EvaluationSummary:
    """Resumen agregado de un metodo sobre un conjunto de consultas."""

    method: str
    query_count: int
    k: int
    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_reciprocal_rank: float
    hit_rate_at_k: float


def _normalize_cuce_list(value: Any) -> list[str]:
    """Convierte una celda de relevancia a lista canonica de CUCE."""
    if value is None:
        return []
    if isinstance(value, float) and pd.isna(value):
        return []
    if isinstance(value, str):
        parts = value.replace("|", ",").replace(";", ",").split(",")
        return [part.strip() for part in parts if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _normalize_metadata_filters(value: Any) -> dict[str, Any] | None:
    """Normaliza filtros opcionales serializados en el dataset de evaluacion."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        filters: dict[str, Any] = {}
        for item in stripped.split(";"):
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
    raise TypeError("metadata_filters debe ser dict, str o vacio.")


def precision_at_k(relevances: list[int], k: int) -> float:
    """Calcula Precision@k sobre una lista binaria de relevancia."""
    if k <= 0:
        raise ValueError("k debe ser mayor que cero.")
    top_k = relevances[:k]
    if not top_k:
        return 0.0
    return sum(top_k) / len(top_k)


def recall_at_k(relevances: list[int], relevant_count: int, k: int) -> float:
    """Calcula Recall@k dado el total de documentos relevantes esperados."""
    if k <= 0:
        raise ValueError("k debe ser mayor que cero.")
    if relevant_count < 0:
        raise ValueError("relevant_count no puede ser negativo.")
    if relevant_count == 0:
        return 0.0
    return sum(relevances[:k]) / relevant_count


def reciprocal_rank(relevances: list[int], k: int | None = None) -> float:
    """Calcula Reciprocal Rank para una consulta."""
    ranked_relevances = relevances[:k] if k is not None else relevances
    for index, is_relevant in enumerate(ranked_relevances, start=1):
        if is_relevant:
            return 1.0 / index
    return 0.0


def mean_reciprocal_rank(results: list[EvaluationResult]) -> float:
    """Calcula MRR a partir de resultados detallados."""
    if not results:
        return 0.0
    return mean(result.reciprocal_rank for result in results)


def evaluate_single_query(
    *,
    query_id: str,
    query_text: str,
    relevant_cuces: list[str],
    search_results: list[dict[str, Any]],
    method: str,
    k: int,
) -> EvaluationResult:
    """Evalua una sola consulta contra una lista de documentos recuperados."""
    canonical_relevant_cuces = list(dict.fromkeys(relevant_cuces))
    relevant_set = set(canonical_relevant_cuces)
    retrieved_cuces = [
        str(item.get("cuce", "")).strip()
        for item in search_results[:k]
        if str(item.get("cuce", "")).strip()
    ]
    relevances = [1 if cuce in relevant_set else 0 for cuce in retrieved_cuces]
    if len(relevances) < k:
        relevances.extend([0] * (k - len(relevances)))

    return EvaluationResult(
        query_id=query_id,
        query_text=query_text,
        method=method,
        k=k,
        relevant_cuces=canonical_relevant_cuces,
        retrieved_cuces=retrieved_cuces,
        relevances=relevances,
        precision_at_k=precision_at_k(relevances, k),
        recall_at_k=recall_at_k(relevances, len(relevant_set), k),
        reciprocal_rank=reciprocal_rank(relevances, k),
        hit_at_k=1.0 if any(relevances[:k]) else 0.0,
    )


def summarize_results(results: list[EvaluationResult]) -> EvaluationSummary:
    """Agrega metricas de evaluacion por metodo."""
    if not results:
        raise ValueError("No hay resultados para resumir.")
    method = results[0].method
    k = results[0].k
    return EvaluationSummary(
        method=method,
        query_count=len(results),
        k=k,
        mean_precision_at_k=mean(result.precision_at_k for result in results),
        mean_recall_at_k=mean(result.recall_at_k for result in results),
        mean_reciprocal_rank=mean_reciprocal_rank(results),
        hit_rate_at_k=mean(result.hit_at_k for result in results),
    )


def results_to_frame(results: list[EvaluationResult]) -> pd.DataFrame:
    """Convierte resultados detallados a DataFrame."""
    return pd.DataFrame(
        [
            {
                "query_id": result.query_id,
                "query_text": result.query_text,
                "method": result.method,
                "k": result.k,
                "relevant_cuces": ",".join(result.relevant_cuces),
                "retrieved_cuces": ",".join(result.retrieved_cuces),
                "relevances": ",".join(str(value) for value in result.relevances),
                "precision_at_k": result.precision_at_k,
                "recall_at_k": result.recall_at_k,
                "reciprocal_rank": result.reciprocal_rank,
                "hit_at_k": result.hit_at_k,
            }
            for result in results
        ]
    )


def summary_to_frame(summary: EvaluationSummary) -> pd.DataFrame:
    """Convierte un resumen agregado a DataFrame."""
    return pd.DataFrame(
        [
            {
                "method": summary.method,
                "query_count": summary.query_count,
                "k": summary.k,
                "mean_precision_at_k": summary.mean_precision_at_k,
                "mean_recall_at_k": summary.mean_recall_at_k,
                "mean_reciprocal_rank": summary.mean_reciprocal_rank,
                "hit_rate_at_k": summary.hit_rate_at_k,
            }
        ]
    )


def evaluate_search_method(
    search_fn: SearchFunction,
    *,
    method: str,
    split: str = "dev",
    k: int = 5,
) -> list[EvaluationResult]:
    """Ejecuta una evaluacion completa sobre un split de consultas."""
    if k <= 0:
        raise ValueError("k debe ser mayor que cero.")

    queries = load_evaluation_queries(split)
    results: list[EvaluationResult] = []
    for row in queries.to_dict(orient="records"):
        query_text = str(row["query_text"]).strip()
        query_id = str(row["query_id"]).strip()
        relevant_cuces = _normalize_cuce_list(row.get("relevant_cuce"))
        metadata_filters = _normalize_metadata_filters(row.get("metadata_filters"))
        search_results = search_fn(query_text, k, metadata_filters)
        results.append(
            evaluate_single_query(
                query_id=query_id,
                query_text=query_text,
                relevant_cuces=relevant_cuces,
                search_results=search_results,
                method=method,
                k=k,
            )
        )
    return results


def evaluate_keyword_search(split: str = "dev", k: int = 5) -> list[EvaluationResult]:
    """Evalua la linea base keyword con SQL e ILIKE."""
    return evaluate_search_method(keyword_search, method="keyword", split=split, k=k)


def evaluate_semantic_search(split: str = "dev", k: int = 5) -> list[EvaluationResult]:
    """Evalua la busqueda semantica sobre pgvector."""
    return evaluate_search_method(semantic_search, method="semantic", split=split, k=k)
