from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.notifications import send_ntfy_notification
from src.run_reporting import save_run_summary

CUCE_PATTERN = re.compile(r"\b\d{2}-\d{4}-\d{2}-\d{7}-\d-\d\b")


@dataclass(slots=True)
class RenameRow:
    sequence: str
    cuce: str
    source_name: str
    target_name: str
    status: str


@dataclass(slots=True)
class ExtractionRow:
    relative_source: str
    archive_member: str
    status: str
    filename_cuce: str
    content_cuce: str
    cuce_match: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audita descargas curadas cruzando rename_manifest y extraction_manifest "
            "para detectar coincidencias, faltantes y posibles desalineaciones."
        )
    )
    parser.add_argument(
        "--rename-manifest",
        required=True,
        type=Path,
        help="CSV generado por rename_sicoes_downloads.py.",
    )
    parser.add_argument(
        "--extraction-manifest",
        required=True,
        type=Path,
        help="CSV generado por extract_documents_to_text.py.",
    )
    parser.add_argument(
        "--output-path",
        required=True,
        type=Path,
        help="CSV de auditoria resultante.",
    )
    return parser.parse_args()


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    if not rows:
        raise ValueError(f"CSV vacio o sin filas: {path}")
    return rows


def load_rename_rows(path: Path) -> list[RenameRow]:
    rows = []
    for row in load_csv_rows(path):
        rows.append(
            RenameRow(
                sequence=row.get("sequence", ""),
                cuce=row.get("cuce", ""),
                source_name=row.get("source_name", ""),
                target_name=row.get("target_name", ""),
                status=row.get("status", ""),
            )
        )
    return rows


def load_extraction_rows(path: Path) -> list[ExtractionRow]:
    rows = []
    for row in load_csv_rows(path):
        rows.append(
            ExtractionRow(
                relative_source=row.get("relative_source", ""),
                archive_member=row.get("archive_member", ""),
                status=row.get("status", ""),
                filename_cuce=row.get("filename_cuce", ""),
                content_cuce=row.get("content_cuce", ""),
                cuce_match=row.get("cuce_match", ""),
            )
        )
    return rows


def extract_cuce_from_name(value: str) -> str:
    match = CUCE_PATTERN.search(value)
    return match.group(0) if match else ""


def build_extraction_index(
    extraction_rows: list[ExtractionRow],
) -> tuple[dict[str, list[ExtractionRow]], dict[str, list[ExtractionRow]]]:
    by_source_name: dict[str, list[ExtractionRow]] = {}
    by_filename_cuce: dict[str, list[ExtractionRow]] = {}

    for row in extraction_rows:
        source_name = Path(row.relative_source).name
        by_source_name.setdefault(source_name, []).append(row)
        if row.filename_cuce:
            by_filename_cuce.setdefault(row.filename_cuce, []).append(row)
    return by_source_name, by_filename_cuce


def summarize_audit_status(
    rename_status: str,
    extraction_statuses: list[str],
    expected_cuce: str,
    content_cuces: list[str],
) -> tuple[str, str]:
    if rename_status == "missing_download":
        return "missing_download", "Fila del log sin archivo descargado asociado."
    if rename_status == "orphan_download":
        return "orphan_download", "Archivo descargado sin fila correspondiente en el log."
    if not extraction_statuses:
        return "missing_extraction", "No se encontro evidencia del archivo en extraction_manifest."
    if any(status == "error" for status in extraction_statuses):
        return "extraction_error", "La extraccion del documento fallo."
    if any(status == "warning_low_text" for status in extraction_statuses):
        return "warning_low_text", "El documento extrajo poco texto; puede requerir OCR."

    unique_content = [cuce for cuce in dict.fromkeys(content_cuces) if cuce]
    if expected_cuce and unique_content:
        if expected_cuce in unique_content:
            return "content_match", "El CUCE esperado aparece dentro del contenido extraido."
        return (
            "content_mismatch",
            "El contenido expone un CUCE distinto al esperado; revisar posible desalineacion.",
        )
    if expected_cuce and not unique_content:
        return (
            "content_cuce_missing",
            "No se detecto CUCE en el contenido; el documento puede venir como plantilla.",
        )
    return "review_needed", "No hay CUCE esperado suficiente para auditoria automatica."


def main() -> dict[str, object]:
    args = parse_args()
    rename_rows = load_rename_rows(args.rename_manifest.resolve())
    extraction_rows = load_extraction_rows(args.extraction_manifest.resolve())
    by_source_name, by_filename_cuce = build_extraction_index(extraction_rows)

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sequence",
        "expected_cuce",
        "rename_status",
        "source_name",
        "target_name",
        "target_cuce",
        "matched_extractions",
        "extraction_statuses",
        "content_cuces",
        "audit_status",
        "note",
    ]

    summary: dict[str, int] = {}
    with args.output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        progress = tqdm(
            rename_rows,
            total=len(rename_rows),
            desc="Auditando descargas",
            unit="fila",
            dynamic_ncols=True,
            disable=not sys.stderr.isatty(),
        )

        for rename_row in progress:
            progress.set_postfix_str(rename_row.target_name or rename_row.source_name or rename_row.cuce)
            matched: list[ExtractionRow] = []
            if rename_row.source_name:
                matched.extend(by_source_name.get(rename_row.source_name, []))

            target_cuce = extract_cuce_from_name(rename_row.target_name)
            if target_cuce:
                for candidate in by_filename_cuce.get(target_cuce, []):
                    if candidate not in matched:
                        matched.append(candidate)

            extraction_statuses = [row.status for row in matched]
            content_cuces = [row.content_cuce for row in matched if row.content_cuce]
            audit_status, note = summarize_audit_status(
                rename_status=rename_row.status,
                extraction_statuses=extraction_statuses,
                expected_cuce=rename_row.cuce or target_cuce,
                content_cuces=content_cuces,
            )
            summary[audit_status] = summary.get(audit_status, 0) + 1

            writer.writerow(
                {
                    "sequence": rename_row.sequence,
                    "expected_cuce": rename_row.cuce,
                    "rename_status": rename_row.status,
                    "source_name": rename_row.source_name,
                    "target_name": rename_row.target_name,
                    "target_cuce": target_cuce,
                    "matched_extractions": " | ".join(
                        sorted(
                            {
                                row.relative_source
                                + (f"::{row.archive_member}" if row.archive_member else "")
                                for row in matched
                            }
                        )
                    ),
                    "extraction_statuses": " | ".join(extraction_statuses),
                    "content_cuces": " | ".join(dict.fromkeys(content_cuces)),
                    "audit_status": audit_status,
                    "note": note,
                }
            )

    print(f"Auditoria generada en: {args.output_path}")
    print("Resumen:")
    for key in sorted(summary):
        print(f"- {key}: {summary[key]}")
    return {
        "script": Path(__file__).name,
        "rows_total": len(rename_rows),
        "summary": summary,
        "output_path": str(args.output_path),
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
                "Auditoria de descargas completada.\n"
                f"Duracion: {elapsed:.1f}s\n"
                f"Script: {summary['script']}\n"
                f"Filas auditadas: {summary['rows_total']}\n"
                f"Resumen: {summary['summary']}\n"
                f"Salida: {summary['output_path']}\n"
                f"Resumen JSON: {report.json_path}"
            ),
            title="SICOES pipeline OK",
            tags=["white_check_mark", "mag"],
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
                "Auditoria de descargas fallida.\n"
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
