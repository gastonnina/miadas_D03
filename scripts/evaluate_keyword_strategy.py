"""Compara estrategias keyword sobre el corpus base."""

from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from src.config import OUTPUTS_DIR
from src.evaluation import (
    evaluate_hybrid_search,
    evaluate_keyword_search,
    results_to_frame,
    summarize_results,
)

SPLITS = ("dev", "val", "test")
TOP_K = 5


def main() -> None:
    output_dir = OUTPUTS_DIR / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, object]] = []
    detail_frames: list[pd.DataFrame] = []

    for split in SPLITS:
        evaluations = {
            "keyword_base_ilike": evaluate_keyword_search(
                split=split,
                k=TOP_K,
                metadata_filters_extra={"corpus_variant": "base", "keyword_strategy": "ilike"},
                method_label="keyword_base_ilike",
            ),
            "keyword_base_fts": evaluate_keyword_search(
                split=split,
                k=TOP_K,
                metadata_filters_extra={"corpus_variant": "base", "keyword_strategy": "fts"},
                method_label="keyword_base_fts",
            ),
            "hybrid_base_ilike": evaluate_hybrid_search(
                split=split,
                k=TOP_K,
                metadata_filters_extra={"corpus_variant": "base", "keyword_strategy": "ilike"},
                method_label="hybrid_base_ilike",
            ),
            "hybrid_base_fts": evaluate_hybrid_search(
                split=split,
                k=TOP_K,
                metadata_filters_extra={"corpus_variant": "base", "keyword_strategy": "fts"},
                method_label="hybrid_base_fts",
            ),
        }

        for results in evaluations.values():
            summary = asdict(summarize_results(results))
            summary["split"] = split
            summary_rows.append(summary)

            detail_frame = results_to_frame(results)
            detail_frame["split"] = split
            detail_frames.append(detail_frame)

    pd.DataFrame(summary_rows)[
        [
            "split",
            "method",
            "query_count",
            "k",
            "mean_precision_at_k",
            "mean_recall_at_k",
            "mean_reciprocal_rank",
            "hit_rate_at_k",
        ]
    ].to_csv(output_dir / "evaluation_keyword_strategy_summary.csv", index=False)

    pd.concat(detail_frames, ignore_index=True).to_csv(
        output_dir / "evaluation_keyword_strategy_detailed.csv",
        index=False,
    )


if __name__ == "__main__":
    main()
