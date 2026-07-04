"""Genera validaciones de preguntas de negocio con o sin respuestas LLM."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.config import OUTPUTS_DIR
from src.rag_chain import answer_question, build_context, retrieve_documents

QUESTIONS = [
    {
        "question_id": "biz_001",
        "category": "fit_proveedor",
        "question": "Mi empresa provee medicamentos hospitalarios. Que convocatorias recuperadas parecen mas alineadas y por que?",
    },
    {
        "question_id": "biz_002",
        "category": "fit_proveedor",
        "question": "Mi empresa vende reactivos de laboratorio. Que evidencia aparece en la convocatoria para pensar que si corresponde a nuestro rubro?",
    },
    {
        "question_id": "biz_003",
        "category": "fit_proveedor",
        "question": "Somos una empresa de software para gestion clinica. La convocatoria realmente pide software o solo equipamiento?",
    },
    {
        "question_id": "biz_004",
        "category": "resumen_requisitos",
        "question": "Resume los puntos clave que un proveedor deberia revisar antes de postular a esta convocatoria de alcantarillado.",
    },
    {
        "question_id": "biz_005",
        "category": "resumen_requisitos",
        "question": "Que insumos o materiales principales se solicitan realmente en esta convocatoria mas alla del titulo corto?",
    },
    {
        "question_id": "biz_006",
        "category": "decision_preliminar",
        "question": "Esta convocatoria parece viable para una empresa pequena o sugiere una carga documental y tecnica alta?",
    },
    {
        "question_id": "biz_007",
        "category": "decision_preliminar",
        "question": "Que senales del texto indican que esta oportunidad puede requerir requisitos formales, garantias o mayor experiencia previa?",
    },
    {
        "question_id": "biz_008",
        "category": "alineacion_rubro",
        "question": "Somos contratistas de obras sanitarias. Las convocatorias recuperadas realmente encajan con nuestro rubro o hay ruido en los resultados?",
    },
]

SCENARIOS = [
    {"scenario": "keyword_base", "retrieval_mode": "keyword", "corpus_variant": "base"},
    {"scenario": "hybrid_base", "retrieval_mode": "hybrid", "corpus_variant": "base"},
    {
        "scenario": "keyword_enriched_qc_filtered",
        "retrieval_mode": "keyword",
        "corpus_variant": "enriched_qc_filtered",
    },
    {
        "scenario": "hybrid_enriched_qc_filtered",
        "retrieval_mode": "hybrid",
        "corpus_variant": "enriched_qc_filtered",
    },
    {
        "scenario": "keyword_focused_qc_filtered_v2",
        "retrieval_mode": "keyword",
        "corpus_variant": "focused_chunked_qc_filtered_v2",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-path",
        type=Path,
        default=OUTPUTS_DIR / "tables" / "business_question_validation_reproducible.csv",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--generate-llm-answers",
        action="store_true",
    )
    parser.add_argument(
        "--question-ids",
        type=str,
        default="",
        help="Lista separada por comas de question_id a ejecutar.",
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        default="",
        help="Lista separada por comas de escenarios a ejecutar.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    selected_question_ids = {
        item.strip() for item in args.question_ids.split(",") if item.strip()
    }
    selected_scenarios = {
        item.strip() for item in args.scenarios.split(",") if item.strip()
    }

    rows: list[dict[str, object]] = []
    for question_row in QUESTIONS:
        if selected_question_ids and question_row["question_id"] not in selected_question_ids:
            continue
        question = question_row["question"]
        for scenario in SCENARIOS:
            if selected_scenarios and scenario["scenario"] not in selected_scenarios:
                continue
            metadata_filters = {"corpus_variant": scenario["corpus_variant"]}
            sources = retrieve_documents(
                question,
                retrieval_mode=scenario["retrieval_mode"],
                k=args.top_k,
                metadata_filters=metadata_filters,
            )
            context = build_context(
                question,
                retrieval_mode=scenario["retrieval_mode"],
                k=args.top_k,
                metadata_filters=metadata_filters,
            )

            llm_answer = ""
            llm_error = ""
            if args.generate_llm_answers:
                try:
                    response = answer_question(
                        question,
                        retrieval_mode=scenario["retrieval_mode"],
                        k=args.top_k,
                        metadata_filters=metadata_filters,
                    )
                    llm_answer = response.answer
                except Exception as exc:  # pragma: no cover - depende del entorno y credenciales
                    llm_error = f"{type(exc).__name__}: {exc}"

            rows.append(
                {
                    "question_id": question_row["question_id"],
                    "category": question_row["category"],
                    "scenario": scenario["scenario"],
                    "retrieval_mode": scenario["retrieval_mode"],
                    "corpus_variant": scenario["corpus_variant"],
                    "question": question,
                    "retrieved_count": len(sources),
                    "retrieved_cuces": " | ".join(
                        [str(item.get("cuce", "")) for item in sources if item.get("cuce")]
                    ),
                    "retrieved_entidades": " | ".join(
                        [str(item.get("entidad", "")) for item in sources if item.get("entidad")]
                    ),
                    "context_chars": len(context),
                    "context_preview": context[:1200],
                    "llm_answer": llm_answer,
                    "llm_error": llm_error,
                }
            )

    pd.DataFrame(rows).to_csv(args.output_path, index=False, encoding="utf-8-sig")
    print(f"Resultados guardados en: {args.output_path}")


if __name__ == "__main__":
    main()
