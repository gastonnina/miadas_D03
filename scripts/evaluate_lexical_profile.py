"""Evalua un perfil de expansion lexica contra el baseline actual."""

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
LEXICAL_PROFILE = "domain_expansion_v1"


def main() -> None:
    output_dir = OUTPUTS_DIR / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, object]] = []
    detail_frames: list[pd.DataFrame] = []

    for split in SPLITS:
        evaluations = {
            "keyword_base": evaluate_keyword_search(
                split=split,
                k=TOP_K,
                metadata_filters_extra={"corpus_variant": "base"},
                method_label="keyword_base",
            ),
            "keyword_base_lexexp_v1": evaluate_keyword_search(
                split=split,
                k=TOP_K,
                metadata_filters_extra={
                    "corpus_variant": "base",
                    "lexical_profile": LEXICAL_PROFILE,
                },
                method_label="keyword_base_lexexp_v1",
            ),
            "hybrid_base": evaluate_hybrid_search(
                split=split,
                k=TOP_K,
                metadata_filters_extra={"corpus_variant": "base"},
                method_label="hybrid_base",
            ),
            "hybrid_base_lexexp_v1": evaluate_hybrid_search(
                split=split,
                k=TOP_K,
                metadata_filters_extra={
                    "corpus_variant": "base",
                    "lexical_profile": LEXICAL_PROFILE,
                },
                method_label="hybrid_base_lexexp_v1",
            ),
        }

        for method_name, results in evaluations.items():
            summary = asdict(summarize_results(results))
            summary["split"] = split
            summary_rows.append(summary)

            detail_frame = results_to_frame(results)
            detail_frame["split"] = split
            detail_frames.append(detail_frame)

    summary_frame = pd.DataFrame(summary_rows)[
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
    ]
    detail_frame = pd.concat(detail_frames, ignore_index=True)

    summary_frame.to_csv(output_dir / "evaluation_lexical_profile_summary.csv", index=False)
    detail_frame.to_csv(output_dir / "evaluation_lexical_profile_detailed.csv", index=False)


if __name__ == "__main__":
    main()
