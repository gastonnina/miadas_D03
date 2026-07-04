"""Genera métricas automáticas y plantilla de rúbrica para validación cualitativa RAG."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from src.config import OUTPUTS_DIR

CUCE_PATTERN = re.compile(r"\b\d{2}-\d{3,4}-[\dA-Z]{2}-\d{6,7}-\d-\d\b")
UNCERTAINTY_PATTERNS = (
    "no se puede determinar",
    "no alcanza para responder",
    "no hay suficiente contexto",
    "no se recuperaron",
    "no es posible confirmar",
)
ACTIONABILITY_PATTERNS = (
    "recomiendo",
    "conviene",
    "deberia",
    "deberías",
    "sugiere",
    "viable",
    "riesgo",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-path",
        type=Path,
        default=OUTPUTS_DIR / "tables" / "business_question_validation_reproducible.csv",
    )
    parser.add_argument(
        "--metrics-output-path",
        type=Path,
        default=OUTPUTS_DIR / "tables" / "business_question_validation_quality_metrics.csv",
    )
    parser.add_argument(
        "--rubric-output-path",
        type=Path,
        default=OUTPUTS_DIR / "tables" / "business_question_validation_quality_rubric.csv",
    )
    return parser.parse_args()


def _split_pipe_values(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split("|") if part.strip()]


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _extract_cuces(value: str) -> list[str]:
    return list(dict.fromkeys(CUCE_PATTERN.findall(value or "")))


def _contains_any_pattern(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = (text or "").strip().lower()
    return any(pattern in lowered for pattern in patterns)


def main() -> None:
    args = parse_args()
    frame = pd.read_csv(args.input_path, encoding="utf-8-sig")

    metrics_rows: list[dict[str, object]] = []
    rubric_rows: list[dict[str, object]] = []

    for row in frame.to_dict(orient="records"):
        answer = _clean_text(row.get("llm_answer", ""))
        retrieved_cuces = _split_pipe_values(_clean_text(row.get("retrieved_cuces", "")))
        retrieved_entidades = _split_pipe_values(_clean_text(row.get("retrieved_entidades", "")))
        answer_cuces = _extract_cuces(answer)

        supported_cuces = [cuce for cuce in answer_cuces if cuce in retrieved_cuces]
        unsupported_cuces = [cuce for cuce in answer_cuces if cuce not in retrieved_cuces]
        mentioned_entities = [
            entidad for entidad in retrieved_entidades if entidad and entidad.lower() in answer.lower()
        ]

        metrics_rows.append(
            {
                "question_id": row["question_id"],
                "category": row["category"],
                "scenario": row["scenario"],
                "retrieval_mode": row["retrieval_mode"],
                "corpus_variant": row["corpus_variant"],
                "has_llm_answer": 1 if answer else 0,
                "answer_chars": len(answer),
                "answer_word_count": len(answer.split()) if answer else 0,
                "retrieved_count": row["retrieved_count"],
                "retrieved_cuce_count": len(retrieved_cuces),
                "retrieved_entity_count": len(retrieved_entidades),
                "answer_cuce_mentions": len(answer_cuces),
                "supported_cuce_mentions": len(supported_cuces),
                "unsupported_cuce_mentions": len(unsupported_cuces),
                "grounded_cuce_precision": (
                    len(supported_cuces) / len(answer_cuces) if answer_cuces else 0.0
                ),
                "mentions_any_retrieved_cuce": 1 if supported_cuces else 0,
                "mentions_any_retrieved_entity": 1 if mentioned_entities else 0,
                "uncertainty_signal": 1 if _contains_any_pattern(answer, UNCERTAINTY_PATTERNS) else 0,
                "actionability_signal": 1 if _contains_any_pattern(answer, ACTIONABILITY_PATTERNS) else 0,
                "llm_error": _clean_text(row.get("llm_error", "")),
            }
        )

        rubric_rows.append(
            {
                "question_id": row["question_id"],
                "category": row["category"],
                "scenario": row["scenario"],
                "retrieval_mode": row["retrieval_mode"],
                "corpus_variant": row["corpus_variant"],
                "question": row["question"],
                "retrieved_cuces": row["retrieved_cuces"],
                "llm_answer": answer,
                "relevance_1_5": "",
                "groundedness_1_5": "",
                "specificity_1_5": "",
                "actionability_1_5": "",
                "clarity_1_5": "",
                "hallucination_risk_1_5": "",
                "overall_1_5": "",
                "review_notes": "",
            }
        )

    metrics_frame = pd.DataFrame(metrics_rows)
    rubric_frame = pd.DataFrame(rubric_rows)

    args.metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
    args.rubric_output_path.parent.mkdir(parents=True, exist_ok=True)

    metrics_frame.to_csv(args.metrics_output_path, index=False, encoding="utf-8-sig")
    rubric_frame.to_csv(args.rubric_output_path, index=False, encoding="utf-8-sig")

    print(f"Metricas guardadas en: {args.metrics_output_path}")
    print(f"Rubrica guardada en: {args.rubric_output_path}")


if __name__ == "__main__":
    main()
