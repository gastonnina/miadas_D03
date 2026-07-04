"""Analiza resultados de retrieval por categoria de consulta para la fase 5."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import OUTPUTS_DIR
from src.data_loader import load_evaluation_queries
from src.evaluation import evaluate_search_method
from src.vector_store import hybrid_search, keyword_search, semantic_search


SEARCH_METHODS = {
    "keyword_base": (keyword_search, {"corpus_variant": "base"}),
    "semantic_base": (semantic_search, {"corpus_variant": "base"}),
    "hybrid_base": (hybrid_search, {"corpus_variant": "base"}),
    "keyword_enriched_qc_filtered": (keyword_search, {"corpus_variant": "enriched_qc_filtered"}),
    "semantic_enriched_qc_filtered": (semantic_search, {"corpus_variant": "enriched_qc_filtered"}),
    "hybrid_enriched_qc_filtered": (hybrid_search, {"corpus_variant": "enriched_qc_filtered"}),
    "keyword_focused_qc_filtered_v2": (
        keyword_search,
        {"corpus_variant": "focused_chunked_qc_filtered_v2"},
    ),
    "semantic_focused_qc_filtered_v2": (
        semantic_search,
        {"corpus_variant": "focused_chunked_qc_filtered_v2"},
    ),
    "hybrid_focused_qc_filtered_v2": (
        hybrid_search,
        {"corpus_variant": "focused_chunked_qc_filtered_v2"},
    ),
}

SPLITS = ("dev", "val", "test")
TOP_K = 5


def build_query_catalog() -> pd.DataFrame:
    """Unifica todos los splits de evaluacion con su categoria."""
    frames: list[pd.DataFrame] = []
    for split in SPLITS:
        frame = load_evaluation_queries(split).copy()
        frame["split"] = split
        if "categoria" not in frame.columns:
            frame["categoria"] = "sin_categoria"
        frames.append(frame[["query_id", "query_text", "categoria", "split"]])
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    output_dir = OUTPUTS_DIR / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)

    query_catalog = build_query_catalog()
    detailed_frames: list[pd.DataFrame] = []

    for split in SPLITS:
        for method_name, (search_fn, metadata_filters) in SEARCH_METHODS.items():
            results = evaluate_search_method(
                search_fn,
                method=method_name,
                split=split,
                k=TOP_K,
                metadata_filters_extra=metadata_filters,
            )
            frame = pd.DataFrame(
                {
                    "query_id": [item.query_id for item in results],
                    "query_text": [item.query_text for item in results],
                    "method": [item.method for item in results],
                    "k": [item.k for item in results],
                    "relevant_cuces": ["|".join(item.relevant_cuces) for item in results],
                    "retrieved_cuces": ["|".join(item.retrieved_cuces) for item in results],
                    "relevances": ["|".join(str(value) for value in item.relevances) for item in results],
                    "precision_at_k": [item.precision_at_k for item in results],
                    "recall_at_k": [item.recall_at_k for item in results],
                    "reciprocal_rank": [item.reciprocal_rank for item in results],
                    "hit_at_k": [item.hit_at_k for item in results],
                    "split": split,
                }
            )
            detailed_frames.append(frame)

    detailed = pd.concat(detailed_frames, ignore_index=True)
    detailed = detailed.merge(query_catalog, on=["query_id", "query_text", "split"], how="left")

    category_summary = (
        detailed.groupby(["categoria", "method"], dropna=False)
        .agg(
            query_count=("query_id", "count"),
            mean_precision_at_k=("precision_at_k", "mean"),
            mean_recall_at_k=("recall_at_k", "mean"),
            mean_reciprocal_rank=("reciprocal_rank", "mean"),
            hit_rate_at_k=("hit_at_k", "mean"),
        )
        .reset_index()
        .sort_values(["categoria", "mean_reciprocal_rank", "mean_recall_at_k"], ascending=[True, False, False])
    )

    split_category_summary = (
        detailed.groupby(["split", "categoria", "method"], dropna=False)
        .agg(
            query_count=("query_id", "count"),
            mean_precision_at_k=("precision_at_k", "mean"),
            mean_recall_at_k=("recall_at_k", "mean"),
            mean_reciprocal_rank=("reciprocal_rank", "mean"),
            hit_rate_at_k=("hit_at_k", "mean"),
        )
        .reset_index()
        .sort_values(
            ["split", "categoria", "mean_reciprocal_rank", "mean_recall_at_k"],
            ascending=[True, True, False, False],
        )
    )

    detailed.to_csv(output_dir / "evaluation_phase5_detailed.csv", index=False)
    category_summary.to_csv(output_dir / "evaluation_phase5_by_category.csv", index=False)
    split_category_summary.to_csv(output_dir / "evaluation_phase5_by_split_category.csv", index=False)


if __name__ == "__main__":
    main()
