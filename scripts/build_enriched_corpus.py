from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
import sys
import time

import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PRIMARY_RAG_PATH
from src.notifications import send_ntfy_notification
from src.run_reporting import save_run_summary


CUCE_PATTERN = re.compile(r"\d{2}-\d{3,4}-\d{2}-\d{6,}-\d-\d")
DOCUMENT_TYPE_PATTERNS = {
    "dbc": [
        "documento_base_contratacion",
        "documento-base-de-contratacion",
        "documento_base_de_contratacion",
    ],
    "convocatoria": ["convocatoria"],
    "ficha": ["ficha"],
    "especificaciones": ["especificaciones_tecnicas", "especificaciones-tecnicas"],
    "planos": ["planos", "plano"],
}


@dataclass(slots=True)
class DocumentText:
    cuce: str
    document_type: str
    source_name: str
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Construye un corpus enriquecido a partir del dataset RAG base y textos "
            "extraídos desde documentos anexos por CUCE."
        )
    )
    parser.add_argument(
        "--base-rag-path",
        type=Path,
        default=PRIMARY_RAG_PATH,
        help="Dataset RAG base en parquet o csv.",
    )
    parser.add_argument(
        "--texts-dir",
        required=True,
        type=Path,
        help="Carpeta raíz con .txt extraídos de los documentos curados.",
    )
    parser.add_argument(
        "--output-path",
        required=True,
        type=Path,
        help="Ruta del parquet enriquecido a generar.",
    )
    parser.add_argument(
        "--csv-output-path",
        type=Path,
        default=None,
        help="Ruta opcional para exportar también CSV auxiliar.",
    )
    parser.add_argument(
        "--max-chars-per-doc",
        type=int,
        default=25000,
        help="Máximo de caracteres a conservar por documento extraído.",
    )
    parser.add_argument(
        "--include-unmatched",
        action="store_true",
        help="Incluye en el reporte interno documentos cuyo CUCE no exista en el corpus base.",
    )
    return parser.parse_args()


def load_base_rag(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError(f"Formato no soportado para base RAG: {path.suffix}")

    required = {"cuce", "texto_rag", "entidad", "objeto_contratacion"}
    missing = required.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"El dataset base no contiene columnas requeridas: {missing_text}")

    return frame


def infer_document_type(stem_without_cuce: str) -> str:
    normalized = stem_without_cuce.strip("_-").lower()
    for document_type, candidates in DOCUMENT_TYPE_PATTERNS.items():
        if any(token in normalized for token in candidates):
            return document_type
    return "otro"


def extract_cuce_and_suffix(value: str) -> tuple[str | None, str]:
    match = CUCE_PATTERN.search(value)
    if match is None:
        return None, ""

    cuce = match.group(0)
    suffix = value[match.end() :]
    return cuce, suffix


def extract_cuce_and_type(path: Path) -> tuple[str | None, str]:
    candidates = [path.stem]
    candidates.extend(parent.name for parent in path.parents)

    fallback_type = "otro"
    for candidate in candidates:
        cuce, suffix = extract_cuce_and_suffix(candidate)
        inferred_type = infer_document_type(suffix or candidate)
        if inferred_type != "otro" and fallback_type == "otro":
            fallback_type = inferred_type
        if cuce is not None:
            return cuce, inferred_type

    return None, fallback_type


def iter_document_texts(texts_dir: Path, max_chars_per_doc: int) -> tuple[list[DocumentText], list[dict[str, str]]]:
    documents: list[DocumentText] = []
    unmatched: list[dict[str, str]] = []
    paths = sorted(texts_dir.rglob("*.txt"))
    progress = tqdm(
        paths,
        total=len(paths),
        desc="Leyendo textos extraidos",
        unit="archivo",
        dynamic_ncols=True,
        disable=not sys.stderr.isatty(),
    )

    for path in progress:
        progress.set_postfix_str(path.name)
        cuce, document_type = extract_cuce_and_type(path)
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            unmatched.append(
                {
                    "path": str(path),
                    "reason": "empty_text",
                    "document_type": document_type,
                    "cuce": cuce or "",
                }
            )
            continue

        truncated = text[:max_chars_per_doc].strip()
        if cuce is None:
            unmatched.append(
                {
                    "path": str(path),
                    "reason": "cuce_not_detected",
                    "document_type": document_type,
                    "cuce": "",
                }
            )
            continue

        documents.append(
            DocumentText(
                cuce=cuce,
                document_type=document_type,
                source_name=path.name,
                text=truncated,
            )
        )

    return documents, unmatched


def concat_documents(documents: list[DocumentText]) -> dict[str, str]:
    grouped: dict[str, list[DocumentText]] = {}
    for document in documents:
        grouped.setdefault(document.document_type, []).append(document)

    output: dict[str, str] = {}
    for document_type, items in grouped.items():
        chunks = []
        for item in items:
            chunks.append(
                "\n".join(
                    [
                        f"DOCUMENTO: {document_type}",
                        f"FUENTE_ARCHIVO: {item.source_name}",
                        "CONTENIDO_EXTRAIDO:",
                        item.text,
                    ]
                ).strip()
            )
        output[document_type] = "\n\n".join(chunks).strip()
    return output


def build_enriched_text(row: pd.Series) -> str:
    sections = [
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
        "RESUMEN_BASE:",
        str(row.get("texto_rag_base", "")).strip(),
        "",
        "DOCUMENTOS_DISPONIBLES:",
    ]

    available = []
    for label, column in [
        ("ficha", "ficha_text"),
        ("convocatoria", "convocatoria_text"),
        ("documento_base_contratacion", "dbc_text"),
        ("especificaciones", "especificaciones_text"),
        ("planos", "planos_text"),
        ("otros_anexos", "otros_anexos_text"),
    ]:
        if str(row.get(column, "")).strip():
            available.append(f"- {label}")

    sections.extend(available or ["- ninguno"])

    for title, column in [
        ("FICHA", "ficha_text"),
        ("CONVOCATORIA", "convocatoria_text"),
        ("DOCUMENTO_BASE_CONTRATACION", "dbc_text"),
        ("ESPECIFICACIONES", "especificaciones_text"),
        ("PLANOS", "planos_text"),
        ("OTROS_ANEXOS", "otros_anexos_text"),
    ]:
        content = str(row.get(column, "")).strip()
        if content:
            sections.extend(["", title + ":", content])

    return "\n".join(sections).strip() + "\n"


def main() -> dict[str, object]:
    args = parse_args()

    base_rag = load_base_rag(args.base_rag_path)
    documents, unmatched = iter_document_texts(args.texts_dir.resolve(), args.max_chars_per_doc)

    docs_by_cuce: dict[str, list[DocumentText]] = {}
    for document in documents:
        docs_by_cuce.setdefault(document.cuce, []).append(document)

    base_rag = base_rag.copy()
    base_rag["texto_rag_base"] = base_rag["texto_rag"]
    base_rag["ficha_text"] = ""
    base_rag["convocatoria_text"] = ""
    base_rag["dbc_text"] = ""
    base_rag["especificaciones_text"] = ""
    base_rag["planos_text"] = ""
    base_rag["otros_anexos_text"] = ""

    known_cuces = set(base_rag["cuce"].astype(str))

    progress = tqdm(
        docs_by_cuce.items(),
        total=len(docs_by_cuce),
        desc="Integrando documentos al corpus",
        unit="cuce",
        dynamic_ncols=True,
        disable=not sys.stderr.isatty(),
    )

    for cuce, items in progress:
        progress.set_postfix_str(cuce)
        if cuce not in known_cuces:
            unmatched.append(
                {
                    "path": "",
                    "reason": "cuce_not_found_in_base_rag",
                    "document_type": ",".join(sorted({item.document_type for item in items})),
                    "cuce": cuce,
                }
            )
            continue

        grouped = concat_documents(items)
        mask = base_rag["cuce"].astype(str) == cuce
        base_rag.loc[mask, "ficha_text"] = grouped.get("ficha", "")
        base_rag.loc[mask, "convocatoria_text"] = grouped.get("convocatoria", "")
        base_rag.loc[mask, "dbc_text"] = grouped.get("dbc", "")
        base_rag.loc[mask, "especificaciones_text"] = grouped.get("especificaciones", "")
        base_rag.loc[mask, "planos_text"] = grouped.get("planos", "")
        other_parts = [
            grouped[key]
            for key in sorted(grouped)
            if key not in {"ficha", "convocatoria", "dbc", "especificaciones", "planos"}
        ]
        base_rag.loc[mask, "otros_anexos_text"] = "\n\n".join(part for part in other_parts if part).strip()

    for column in ["ficha_text", "convocatoria_text", "dbc_text", "especificaciones_text", "planos_text", "otros_anexos_text"]:
        base_rag[f"has_{column.replace('_text', '')}"] = base_rag[column].astype(str).str.strip().ne("")

    tqdm.write("Construyendo texto_rag_enriched...")
    base_rag["texto_rag_enriched"] = base_rag.apply(build_enriched_text, axis=1)

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    base_rag.to_parquet(args.output_path, index=False)

    if args.csv_output_path is not None:
        args.csv_output_path.parent.mkdir(parents=True, exist_ok=True)
        base_rag.to_csv(args.csv_output_path, index=False, encoding="utf-8-sig")

    unmatched_path = args.output_path.with_name(args.output_path.stem + "_unmatched.csv")
    unmatched_df = pd.DataFrame(unmatched)
    unmatched_df.to_csv(unmatched_path, index=False, encoding="utf-8-sig")

    print("Corpus enriquecido generado en:", args.output_path)
    if args.csv_output_path is not None:
        print("CSV auxiliar generado en:", args.csv_output_path)
    print("Reporte de no emparejados en:", unmatched_path)
    print("Filas base:", len(base_rag))
    print("Documentos extraidos reconocidos:", len(documents))
    print("CUECs con DBC:", int(base_rag["has_dbc"].sum()))

    if unmatched and not args.include_unmatched:
        print("Advertencia: hay documentos no emparejados; revisa el reporte CSV.")
    return {
        "script": Path(__file__).name,
        "base_rows": len(base_rag),
        "documents_recognized": len(documents),
        "cuces_with_dbc": int(base_rag["has_dbc"].sum()),
        "unmatched_count": len(unmatched),
        "output_path": str(args.output_path),
        "csv_output_path": str(args.csv_output_path) if args.csv_output_path is not None else "",
        "unmatched_path": str(unmatched_path),
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
                "Construccion de corpus enriquecido completada.\n"
                f"Duracion: {elapsed:.1f}s\n"
                f"Script: {summary['script']}\n"
                f"Filas base: {summary['base_rows']}\n"
                f"Documentos reconocidos: {summary['documents_recognized']}\n"
                f"CUECs con DBC: {summary['cuces_with_dbc']}\n"
                f"No emparejados: {summary['unmatched_count']}\n"
                f"Parquet: {summary['output_path']}\n"
                f"CSV unmatched: {summary['unmatched_path']}\n"
                f"Resumen JSON: {report.json_path}"
            ),
            title="SICOES pipeline OK",
            tags=["white_check_mark", "books"],
            priority=3,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        report = save_run_summary(
            script=Path(__file__).name,
            success=False,
            elapsed_seconds=elapsed,
            summary={},
            error=str(exc),
        )
        print(f"Resumen de error guardado en: {report.json_path}")
        send_ntfy_notification(
            (
                "Construccion de corpus enriquecido fallida.\n"
                f"Duracion: {elapsed:.1f}s\n"
                f"Script: {Path(__file__).name}\n"
                f"Error: {exc}\n"
                f"Resumen JSON: {report.json_path}"
            ),
            title="SICOES pipeline ERROR",
            tags=["warning", "x"],
            priority=4,
        )
        raise
