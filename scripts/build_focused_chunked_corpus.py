"""Construye un corpus controlado con DBC seleccionado y chunking fino."""

from __future__ import annotations

import argparse
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from tqdm.auto import tqdm

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import (
    CURATED_ENRICHED_PARQUET_PATH,
    CURATED_FOCUSED_CHUNKED_CSV_PATH,
    CURATED_FOCUSED_CHUNKED_PARQUET_PATH,
)
from src.notifications import send_ntfy_notification
from src.run_reporting import save_run_summary

STOPWORDS = {
    "a",
    "al",
    "con",
    "de",
    "del",
    "el",
    "en",
    "la",
    "las",
    "los",
    "para",
    "por",
    "se",
    "su",
    "sus",
    "un",
    "una",
    "y",
}

SIGNAL_TERMS = {
    "adquisicion",
    "alcance",
    "alcantarillado",
    "anatomia",
    "biomedico",
    "cemento",
    "clinica",
    "clinico",
    "cantidad",
    "caracteristica",
    "condicion",
    "entrega",
    "equipo",
    "especificacion",
    "farmacia",
    "funcional",
    "insumo",
    "item",
    "items",
    "laboratorio",
    "material",
    "medicamento",
    "medicamentos",
    "obra",
    "pluvial",
    "producto",
    "provision",
    "reactivo",
    "repuesto",
    "requerimiento",
    "software",
    "suministro",
    "tecnica",
    "tecnico",
    "terminos",
    "referencia",
    "entregable",
    "entregables",
    "ubicacion",
    "volumenes",
}

NEGATIVE_ADMIN_TERMS = {
    "alcance de la licitacion",
    "alcance de la licitación",
    "comprador",
    "comisión de calificación",
    "comision de calificacion",
    "apertura de propuestas",
    "comision de calificacion",
    "comision de evaluación",
    "comision de evaluacion",
    "contenido",
    "criterios de subsanabilidad",
    "declaratoria desierta",
    "expresiones de interes",
    "expresiones de interés",
    "firmas consultoras",
    "formulario",
    "garantia de seriedad",
    "garantía de seriedad",
    "reunion de aclaracion",
    "reunión de aclaración",
    "licitacion publica internacional",
    "licitación pública internacional",
    "normativa aplicable",
    "prestatario",
    "proponente",
    "propuesta economica",
    "propuesta económica",
    "cronograma de plazos",
    "solicitud de ofertas",
    "rechazo de la propuesta",
    "subsanacion",
    "tabla de contenido",
    "validez de la propuesta",
}

BOILERPLATE_PATTERNS = [
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in [
        r"estas instrucciones deber[aá]n ser suprimidas",
        r"modelo de documento base de contrataci[oó]n",
        r"decreto supremo n[°o]?\s*0181",
        r"normas b[aá]sicas del sistema de administraci[oó]n de bienes y servicios",
        r"estado plurinacional de bolivia",
        r"normativa aplicable al proceso de contrataci[oó]n",
        r"proponentes elegibles",
        r"actividades administrativas previas",
        r"condiciones generales del contrato",
        r"formulario [a-z0-9-]+",
        r"firmas consultoras",
        r"expresiones de inter[eé]s",
        r"anexo [0-9ivx]+",
        r"nb-sabs",
        r"solicitud de ofertas",
        r"licitaci[oó]n p[uú]blica internacional",
        r"banco interamericano de desarrollo",
        r"cliente:",
    ]
]

HEADING_HINTS = [
    "objeto de la contratacion",
    "objeto de contratación",
    "objeto del servicio",
    "alcance",
    "terminos de referencia",
    "términos de referencia",
    "especificaciones tecnicas",
    "especificaciones técnicas",
    "condiciones tecnicas",
    "condiciones técnicas",
    "entregables",
    "ubicacion de la obra",
    "ubicación de la obra",
    "tabla de volumenes de obra",
    "tabla de volúmenes de obra",
]

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9ÁÉÍÓÚáéíóúÑñÜü]+")
WHITESPACE_PATTERN = re.compile(r"[ \t]+")
MULTI_BREAK_PATTERN = re.compile(r"\n{3,}")
HEADER_PATTERN = re.compile(
    r"^\s*DOCUMENTO:\s*dbc\s+FUENTE_ARCHIVO:.*?CONTENIDO_EXTRAIDO:\s*",
    flags=re.IGNORECASE | re.DOTALL,
)


@dataclass(slots=True)
class Segment:
    index: int
    text: str
    score: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera un corpus focused_chunked a partir del corpus enriquecido con DBC."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=CURATED_ENRICHED_PARQUET_PATH,
        help="Parquet del corpus enriquecido.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=CURATED_FOCUSED_CHUNKED_PARQUET_PATH,
        help="Parquet de salida para el corpus focused_chunked.",
    )
    parser.add_argument(
        "--csv-output-path",
        type=Path,
        default=CURATED_FOCUSED_CHUNKED_CSV_PATH,
        help="CSV auxiliar opcional.",
    )
    parser.add_argument(
        "--selection-report-path",
        type=Path,
        default=None,
        help="CSV opcional con trazabilidad de segmentos seleccionados.",
    )
    parser.add_argument(
        "--target-chunk-chars",
        type=int,
        default=1400,
        help="Tamano objetivo por chunk.",
    )
    parser.add_argument(
        "--max-chunks-per-cuce",
        type=int,
        default=3,
        help="Maximo de chunks indexados por CUCE.",
    )
    parser.add_argument(
        "--selection-char-budget",
        type=int,
        default=4200,
        help="Maximo de caracteres DBC seleccionados por CUCE antes de chunking.",
    )
    parser.add_argument(
        "--allowed-dbc-statuses",
        default="accept,review",
        help="Estados de calidad DBC permitidos para generar chunks.",
    )
    parser.add_argument(
        "--allowed-dbc-review-reasons",
        default="partial_object_alignment",
        help="Razones de review permitidas para generar chunks.",
    )
    return parser.parse_args()


def normalize_spaces(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = HEADER_PATTERN.sub("", text)
    text = text.replace("\ufeff", " ")
    text = WHITESPACE_PATTERN.sub(" ", text)
    text = MULTI_BREAK_PATTERN.sub("\n\n", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
    return [token for token in tokens if len(token) > 2 and token not in STOPWORDS]


def split_segments(text: str) -> list[str]:
    by_paragraph = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(by_paragraph) >= 6:
        return by_paragraph

    coarse_parts = [part.strip() for part in re.split(r"(?<=[\.\:\;])\s{2,}", text) if part.strip()]
    if len(coarse_parts) >= 8:
        return coarse_parts

    sentences = [
        part.strip()
        for part in re.split(r"(?<=[\.\?\!])\s+(?=[A-ZÁÉÍÓÚÑ0-9])", text)
        if part.strip()
    ]
    grouped: list[str] = []
    buffer = ""
    for sentence in sentences:
        candidate = f"{buffer} {sentence}".strip() if buffer else sentence
        if len(candidate) <= 650:
            buffer = candidate
            continue
        if buffer:
            grouped.append(buffer)
        buffer = sentence
    if buffer:
        grouped.append(buffer)
    return grouped or [text]


def split_oversized_segment(segment: str, max_chars: int = 900) -> list[str]:
    """Parte segmentos excesivamente largos en subsegmentos mas tratables."""
    cleaned = segment.strip()
    if len(cleaned) <= max_chars:
        return [cleaned]

    delimiters = [
        r"\n(?=[A-Za-zÁÉÍÓÚÑÜ0-9][^\n]{0,80}:)",
        r"\n(?=[0-9]+\.)",
        r"\n(?=[a-z]\))",
        r"(?<=\.)\s+(?=[A-ZÁÉÍÓÚÑ0-9])",
        r"(?<=\;)\s+",
        r"(?<=\|)\s*",
    ]
    for delimiter in delimiters:
        parts = [part.strip() for part in re.split(delimiter, cleaned) if part.strip()]
        if len(parts) <= 1:
            continue
        buffer = ""
        chunks: list[str] = []
        for part in parts:
            candidate = f"{buffer} {part}".strip() if buffer else part
            if len(candidate) <= max_chars:
                buffer = candidate
                continue
            if buffer:
                chunks.append(buffer)
                buffer = ""
            if len(part) <= max_chars:
                buffer = part
                continue
            midpoint = max_chars
            while len(part) > max_chars:
                split_at = part.rfind(" ", 0, midpoint)
                if split_at < max_chars * 0.5:
                    split_at = midpoint
                chunks.append(part[:split_at].strip())
                part = part[split_at:].strip()
            if part:
                buffer = part
        if buffer:
            chunks.append(buffer)
        if chunks and max(len(chunk) for chunk in chunks) <= max_chars:
            return chunks

    hard_chunks: list[str] = []
    remaining = cleaned
    while len(remaining) > max_chars:
        split_at = remaining.rfind(" ", 0, max_chars)
        if split_at < max_chars * 0.5:
            split_at = max_chars
        hard_chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        hard_chunks.append(remaining)
    return hard_chunks


def _count_term_matches(text: str, terms: set[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


def _segment_overlap(segment_text: str, object_tokens: set[str]) -> int:
    return len(set(tokenize(segment_text)).intersection(object_tokens))


def score_segment(
    segment: str,
    *,
    object_tokens: set[str],
    modality: str,
    tipo_contratacion: str,
    position_index: int,
    total_segments: int,
) -> float:
    lowered = segment.lower()
    segment_tokens = set(tokenize(segment))
    overlap = len(segment_tokens.intersection(object_tokens))
    signal_hits = _count_term_matches(lowered, SIGNAL_TERMS)
    heading_hits = _count_term_matches(lowered, set(HEADING_HINTS))
    negative_hits = _count_term_matches(lowered, NEGATIVE_ADMIN_TERMS)
    modality_hits = 1 if modality and modality.lower() in lowered else 0
    tipo_hits = 1 if tipo_contratacion and tipo_contratacion.lower() in lowered else 0
    boilerplate_hits = sum(1 for pattern in BOILERPLATE_PATTERNS if pattern.search(segment))

    score = (
        overlap * 6.0
        + signal_hits * 1.5
        + heading_hits * 2.5
        + modality_hits * 1.0
        + tipo_hits * 1.0
    )

    if overlap == 0 and heading_hits == 0 and signal_hits < 2:
        score -= 4.0

    if lowered.startswith("contenido") or "alcance de la licitación" in lowered or "alcance de la licitacion" in lowered:
        score -= 10.0
    if "expresiones de interes" in lowered or "expresiones de interés" in lowered:
        score -= 10.0
    if "firmas consultoras" in lowered or "consultor individual" in lowered:
        score -= 8.0
    if "solicitud de ofertas" in lowered and overlap < 2:
        score -= 6.0
    if "licitación pública internacional" in lowered or "licitacion publica internacional" in lowered:
        score -= 6.0
    if "banco interamericano de desarrollo" in lowered:
        score -= 6.0

    if len(segment) < 120:
        score -= 1.0
    if len(segment) < 95 and heading_hits == 0:
        score -= 3.0
    if len(segment) > 1800:
        score -= 8.0
    if position_index <= max(2, math.floor(total_segments * 0.08)):
        score -= 1.5
    if negative_hits:
        score -= negative_hits * 4.0
    if boilerplate_hits:
        score -= boilerplate_hits * 6.0
    return score


def select_segments(
    dbc_text: str,
    *,
    objeto_contratacion: str,
    modalidad: str,
    tipo_contratacion: str,
    selection_char_budget: int,
) -> tuple[list[Segment], list[dict[str, object]]]:
    clean_text = normalize_spaces(dbc_text)
    raw_segments = []
    for segment in split_segments(clean_text):
        raw_segments.extend(split_oversized_segment(segment))
    object_tokens = set(tokenize(objeto_contratacion))
    if modalidad:
        object_tokens.update(tokenize(modalidad))
    if tipo_contratacion:
        object_tokens.update(tokenize(tipo_contratacion))

    scored_segments: list[Segment] = []
    report_rows: list[dict[str, object]] = []
    total_segments = len(raw_segments)

    for index, segment_text in enumerate(raw_segments):
        score = score_segment(
            segment_text,
            object_tokens=object_tokens,
            modality=modalidad,
            tipo_contratacion=tipo_contratacion,
            position_index=index,
            total_segments=total_segments,
        )
        scored_segments.append(Segment(index=index, text=segment_text, score=score))
        report_rows.append(
            {
                "segment_index": index,
                "segment_chars": len(segment_text),
                "segment_score": round(score, 3),
                "segment_preview": segment_text[:220],
            }
        )

    ranked = sorted(scored_segments, key=lambda item: (item.score, len(item.text)), reverse=True)
    selected: list[Segment] = []
    selected_chars = 0

    for segment in ranked:
        if segment.score <= 0:
            continue
        lowered = segment.text.lower()
        overlap = len(set(tokenize(segment.text)).intersection(object_tokens))
        has_heading = any(hint in lowered for hint in HEADING_HINTS)
        has_signal = any(term in lowered for term in SIGNAL_TERMS)
        has_negative = any(term in lowered for term in NEGATIVE_ADMIN_TERMS)
        starts_with_index = lowered.startswith("contenido") or lowered.startswith("indice")
        table_like = segment.text.count("|") >= 8 or "+---" in segment.text
        heading_only = len(segment.text) < 110 and "\n" not in segment.text
        if starts_with_index or table_like:
            continue
        if heading_only and overlap < 2:
            continue
        if overlap == 0 and not has_heading:
            continue
        if has_negative and overlap < 3:
            continue
        if not has_heading and not has_signal and overlap < 3:
            continue
        if selected_chars >= selection_char_budget:
            break
        selected.append(segment)
        selected_chars += len(segment.text)

    if not selected:
        fallback = [
            segment
            for segment in scored_segments
            if not any(pattern.search(segment.text) for pattern in BOILERPLATE_PATTERNS)
        ]
        selected = fallback[: max(1, min(4, len(fallback)))] or scored_segments[:1]

    vetted: list[Segment] = []
    for segment in selected:
        lowered = segment.text.lower()
        overlap = _segment_overlap(segment.text, object_tokens)
        has_heading = any(hint in lowered for hint in HEADING_HINTS)
        has_signal = any(term in lowered for term in SIGNAL_TERMS)
        if overlap >= 2:
            vetted.append(segment)
            continue
        if overlap >= 1 and has_heading:
            vetted.append(segment)
            continue
        if overlap >= 1 and has_signal and segment.score >= 6:
            vetted.append(segment)
            continue

    if vetted:
        selected = vetted
    else:
        selected = []

    selected = sorted(selected, key=lambda item: item.index)
    return selected, report_rows


def chunk_segments(
    segments: list[Segment],
    *,
    target_chunk_chars: int,
    max_chunks_per_cuce: int,
) -> list[str]:
    chunks: list[str] = []
    current_parts: list[str] = []
    current_chars = 0

    for segment in segments:
        candidate_size = current_chars + len(segment.text) + (2 if current_parts else 0)
        if current_parts and candidate_size > target_chunk_chars:
            chunks.append("\n\n".join(current_parts).strip())
            if len(chunks) >= max_chunks_per_cuce:
                return chunks
            overlap_parts = current_parts[-1:]
            current_parts = overlap_parts.copy()
            current_chars = len("\n\n".join(current_parts).strip())

        current_parts.append(segment.text)
        current_chars = len("\n\n".join(current_parts).strip())

    if current_parts and len(chunks) < max_chunks_per_cuce:
        chunks.append("\n\n".join(current_parts).strip())
    return chunks[:max_chunks_per_cuce]


def build_chunk_text(row: pd.Series, chunk_text: str, chunk_index: int, chunk_count: int) -> str:
    parts = [
        f"CUCE: {row.get('cuce', '')}",
        f"ENTIDAD: {row.get('entidad', '')}",
        f"TIPO_CONTRATACION: {row.get('tipo_contratacion', '')}",
        f"MODALIDAD: {row.get('modalidad', '')}",
        f"ESTADO: {row.get('estado', '')}",
        f"FECHA_PUBLICACION: {row.get('fecha_publicacion_iso', '')}",
        f"FECHA_PRESENTACION: {row.get('fecha_presentacion_iso', '')}",
        "",
        "OBJETO_CONTRATACION:",
        str(row.get("objeto_contratacion", "")).strip(),
        "",
        f"DBC_FOCUSED_CHUNK: {chunk_index}/{chunk_count}",
        chunk_text.strip(),
    ]
    return "\n".join(parts).strip() + "\n"


def should_include_row(
    row: pd.Series,
    *,
    allowed_statuses: set[str],
    allowed_review_reasons: set[str],
) -> bool:
    if not bool(row.get("has_dbc", False)):
        return False
    status = str(row.get("dbc_quality_status", "") or "").strip().lower()
    reason = str(row.get("dbc_quality_reason", "") or "").strip().lower()
    if status not in allowed_statuses:
        return False
    if status == "review" and reason not in allowed_review_reasons:
        return False
    return True


def main() -> dict[str, object]:
    args = parse_args()
    input_path = args.input_path.resolve()
    output_path = args.output_path.resolve()
    csv_output_path = args.csv_output_path.resolve() if args.csv_output_path else None
    selection_report_path = (
        args.selection_report_path.resolve()
        if args.selection_report_path
        else output_path.with_name(output_path.stem + "_selection_report.csv")
    )
    allowed_statuses = {
        part.strip().lower()
        for part in str(args.allowed_dbc_statuses).split(",")
        if part.strip()
    }
    allowed_review_reasons = {
        part.strip().lower()
        for part in str(args.allowed_dbc_review_reasons).split(",")
        if part.strip()
    }

    source_df = pd.read_parquet(input_path)
    source_df["has_dbc"] = source_df["has_dbc"].fillna(False).astype(bool)
    focused_df = source_df[
        source_df.apply(
            should_include_row,
            axis=1,
            allowed_statuses=allowed_statuses,
            allowed_review_reasons=allowed_review_reasons,
        )
    ].copy()

    records: list[dict[str, object]] = []
    selection_rows: list[dict[str, object]] = []

    progress = tqdm(
        focused_df.to_dict(orient="records"),
        total=len(focused_df),
        desc="Construyendo corpus focused_chunked",
        unit="cuce",
        dynamic_ncols=True,
        disable=not sys.stderr.isatty(),
    )

    cuces_with_chunks = 0
    total_chunks = 0

    for row_dict in progress:
        row = pd.Series(row_dict)
        cuce = str(row.get("cuce", "")).strip()
        progress.set_postfix_str(cuce)
        dbc_text = str(row.get("dbc_text", "") or "").strip()
        if not dbc_text:
            continue

        selected_segments, segment_report = select_segments(
            dbc_text,
            objeto_contratacion=str(row.get("objeto_contratacion", "") or ""),
            modalidad=str(row.get("modalidad", "") or ""),
            tipo_contratacion=str(row.get("tipo_contratacion", "") or ""),
            selection_char_budget=args.selection_char_budget,
        )
        chunks = chunk_segments(
            selected_segments,
            target_chunk_chars=args.target_chunk_chars,
            max_chunks_per_cuce=args.max_chunks_per_cuce,
        )
        if not chunks:
            continue

        cuces_with_chunks += 1
        total_chunks += len(chunks)

        for report_row in segment_report:
            report_row["cuce"] = cuce
            report_row["selected"] = any(
                item.index == report_row["segment_index"] for item in selected_segments
            )
            selection_rows.append(report_row)

        chunk_count = len(chunks)
        for chunk_index, chunk_text in enumerate(chunks, start=1):
            document_id = f"{cuce}::focused::{chunk_index:02d}"
            record = row_dict.copy()
            record["document_id"] = document_id
            record["texto_rag"] = build_chunk_text(row, chunk_text, chunk_index, chunk_count)
            record["texto_rag_focused"] = chunk_text
            record["source_text_column"] = "texto_rag"
            record["corpus_variant"] = "focused_chunked"
            record["chunk_index"] = chunk_index
            record["chunk_count_for_cuce"] = chunk_count
            record["chunk_chars"] = len(chunk_text)
            record["selected_segment_count"] = len(selected_segments)
            records.append(record)

    output_df = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_parquet(output_path, index=False)

    if csv_output_path is not None:
        csv_output_path.parent.mkdir(parents=True, exist_ok=True)
        output_df.to_csv(csv_output_path, index=False, encoding="utf-8-sig")

    selection_report_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(selection_rows).to_csv(selection_report_path, index=False, encoding="utf-8-sig")

    print("Corpus focused_chunked generado en:", output_path)
    if csv_output_path is not None:
        print("CSV auxiliar generado en:", csv_output_path)
    print("Reporte de seleccion generado en:", selection_report_path)
    print("Filas fuente con DBC:", len(focused_df))
    print("CUECs con chunks generados:", cuces_with_chunks)
    print("Chunks totales:", total_chunks)

    return {
        "script": Path(__file__).name,
        "input_rows": len(source_df),
        "dbc_rows": len(focused_df),
        "cuces_with_chunks": cuces_with_chunks,
        "chunk_rows": total_chunks,
        "output_path": str(output_path),
        "csv_output_path": str(csv_output_path) if csv_output_path else "",
        "selection_report_path": str(selection_report_path),
        "allowed_dbc_statuses": sorted(allowed_statuses),
        "allowed_dbc_review_reasons": sorted(allowed_review_reasons),
    }


if __name__ == "__main__":
    started_at = time.perf_counter()
    try:
        summary = main()
        elapsed = time.perf_counter() - started_at
        report = save_run_summary(
            script=summary["script"],
            success=True,
            elapsed_seconds=elapsed,
            summary=summary,
        )
        print(f"Resumen de corrida guardado en: {report.json_path}")
        send_ntfy_notification(
            (
                "Corpus focused_chunked generado.\n"
                f"Duracion: {elapsed:.1f}s\n"
                f"CUECs con chunks: {summary['cuces_with_chunks']}\n"
                f"Chunks totales: {summary['chunk_rows']}\n"
                f"Salida: {summary['output_path']}"
            ),
            title="SICOES focused_chunked listo",
            tags=["books", "test_tube", "postgres"],
            priority=3,
        )
    except Exception as exc:  # pragma: no cover - depende del entorno
        elapsed = time.perf_counter() - started_at
        report = save_run_summary(
            script=Path(__file__).name,
            success=False,
            elapsed_seconds=elapsed,
            error=str(exc),
        )
        print(f"Resumen de error guardado en: {report.json_path}")
        raise
