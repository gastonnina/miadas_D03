from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.notifications import send_ntfy_notification
from src.run_reporting import save_run_summary

SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc"}
SUPPORTED_ARCHIVE_EXTENSIONS = {".rar"}
CUCE_PATTERN = re.compile(r"\b\d{2}-\d{4}-\d{2}-\d{7}-\d-\d\b")


@dataclass
class SourceItem:
    source_path: Path
    relative_source: Path
    extension: str
    archive_member: Path | None = None


@dataclass
class ExtractionResult:
    source_path: Path
    relative_source: Path
    output_path: Path
    extension: str
    extractor: str
    status: str
    char_count: int
    note: str
    archive_member: str
    filename_cuce: str
    content_cuce: str
    cuce_match: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extrae texto plano desde PDF/DOCX/DOC/RAR para construir un corpus "
            "enriquecido y trazable."
        )
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        help="Carpeta raíz con documentos originales descargados.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Carpeta destino para los .txt extraídos.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Ruta opcional del CSV resumen. Por defecto se crea en output-dir.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="No reprocesa archivos cuyo .txt ya exista.",
    )
    return parser.parse_args()


def require_command(command: str) -> str:
    executable = shutil.which(command)
    if executable is None:
        raise RuntimeError(f"No se encontró el ejecutable requerido: {command}")
    return executable


def build_target_relative_path(item: SourceItem) -> Path:
    if item.archive_member is None:
        return item.relative_source.with_suffix(".txt")
    archive_dir = item.relative_source.with_suffix("")
    member_name = item.archive_member.with_suffix(".txt").name
    return archive_dir / member_name


def iter_source_items(root: Path) -> list[SourceItem]:
    items: list[SourceItem] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in SUPPORTED_DOCUMENT_EXTENSIONS | SUPPORTED_ARCHIVE_EXTENSIONS:
            items.append(
                SourceItem(
                    source_path=path,
                    relative_source=path.relative_to(root),
                    extension=suffix,
                )
            )
    return items


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    text = text.replace("\f", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + ("\n" if text.strip() else "")


def extract_cuce_candidates(text: str) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for match in CUCE_PATTERN.findall(text):
        if match not in seen:
            ordered.append(match)
            seen.add(match)
    return ordered


def extract_filename_cuce(path: Path) -> str:
    candidates = extract_cuce_candidates(path.name)
    return candidates[0] if candidates else ""


def extract_pdf(source: Path, target: Path) -> str:
    require_command("pdftotext")
    subprocess.run(
        ["pdftotext", "-layout", str(source), str(target)],
        check=True,
        capture_output=True,
        text=True,
    )
    return "pdftotext"


def extract_docx(source: Path, target: Path) -> str:
    require_command("pandoc")
    subprocess.run(
        ["pandoc", str(source), "-t", "plain", "-o", str(target)],
        check=True,
        capture_output=True,
        text=True,
    )
    return "pandoc"


def extract_doc(source: Path, target: Path) -> str:
    require_command("libreoffice")
    with tempfile.TemporaryDirectory(prefix="dip03_doc_extract_") as tmpdir:
        tmp_path = Path(tmpdir)
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "txt:Text",
                "--outdir",
                str(tmp_path),
                str(source),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        generated = tmp_path / f"{source.stem}.txt"
        if not generated.exists():
            raise FileNotFoundError(f"LibreOffice no generó TXT para {source}")
        shutil.copy2(generated, target)
    return "libreoffice"


def extract_one(source: Path, target: Path) -> tuple[str, str]:
    extension = source.suffix.lower()
    if extension == ".pdf":
        extractor = extract_pdf(source, target)
    elif extension == ".docx":
        extractor = extract_docx(source, target)
    elif extension == ".doc":
        extractor = extract_doc(source, target)
    else:
        raise ValueError(f"Extensión no soportada: {extension}")

    raw_text = target.read_text(encoding="utf-8", errors="ignore")
    normalized = clean_text(raw_text)
    target.write_text(normalized, encoding="utf-8")
    return extractor, normalized


def extract_rar(item: SourceItem, output_dir: Path) -> list[ExtractionResult]:
    require_command("unrar")
    results: list[ExtractionResult] = []

    with tempfile.TemporaryDirectory(prefix="dip03_rar_extract_") as tmpdir:
        tmp_path = Path(tmpdir)
        subprocess.run(
            ["unrar", "x", "-o+", str(item.source_path), str(tmp_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        member_files = sorted(
            path
            for path in tmp_path.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_DOCUMENT_EXTENSIONS
        )
        if not member_files:
            results.append(
                ExtractionResult(
                    source_path=item.source_path,
                    relative_source=item.relative_source,
                    output_path=output_dir / item.relative_source.with_suffix(".txt"),
                    extension=item.extension,
                    extractor="unrar",
                    status="warning_no_supported_members",
                    char_count=0,
                    note="El archivo RAR no contiene documentos soportados.",
                    archive_member="",
                    filename_cuce=extract_filename_cuce(item.relative_source),
                    content_cuce="",
                    cuce_match="missing_content_cuce",
                )
            )
            return results

        for member in member_files:
            member_relative = member.relative_to(tmp_path)
            nested_item = SourceItem(
                source_path=member,
                relative_source=item.relative_source,
                extension=member.suffix.lower(),
                archive_member=member_relative,
            )
            target = output_dir / build_target_relative_path(nested_item)
            target.parent.mkdir(parents=True, exist_ok=True)

            status = "ok"
            note = ""
            extractor = ""
            char_count = 0
            content_cuce = ""

            try:
                extractor, extracted_text = extract_one(member, target)
                char_count = len(extracted_text.strip())
                candidates = extract_cuce_candidates(extracted_text)
                content_cuce = candidates[0] if candidates else ""
                if char_count < 40:
                    status = "warning_low_text"
                    note = (
                        "Se extrajo muy poco texto; probablemente el documento es "
                        "escaneado o requiere OCR."
                    )
            except Exception as exc:  # noqa: BLE001
                status = "error"
                note = str(exc)
                extractor = "failed"
                if target.exists():
                    target.unlink()

            filename_cuce = extract_filename_cuce(member_relative)
            cuce_match = "missing_content_cuce"
            if content_cuce and filename_cuce:
                cuce_match = "match" if content_cuce == filename_cuce else "mismatch"
            elif content_cuce:
                cuce_match = "missing_filename_cuce"

            results.append(
                ExtractionResult(
                    source_path=item.source_path,
                    relative_source=item.relative_source,
                    output_path=target,
                    extension=member.suffix.lower(),
                    extractor=f"unrar+{extractor}",
                    status=status,
                    char_count=char_count,
                    note=note,
                    archive_member=str(member_relative),
                    filename_cuce=filename_cuce,
                    content_cuce=content_cuce,
                    cuce_match=cuce_match,
                )
            )
    return results


def write_manifest(rows: list[ExtractionResult], path: Path) -> None:
    fieldnames = [
        "source_path",
        "relative_source",
        "output_path",
        "extension",
        "extractor",
        "status",
        "char_count",
        "note",
        "archive_member",
        "filename_cuce",
        "content_cuce",
        "cuce_match",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "source_path": str(row.source_path),
                    "relative_source": str(row.relative_source),
                    "output_path": str(row.output_path),
                    "extension": row.extension,
                    "extractor": row.extractor,
                    "status": row.status,
                    "char_count": row.char_count,
                    "note": row.note,
                    "archive_member": row.archive_member,
                    "filename_cuce": row.filename_cuce,
                    "content_cuce": row.content_cuce,
                    "cuce_match": row.cuce_match,
                }
            )


def main() -> dict[str, object]:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    manifest_path = (args.manifest or (output_dir / "extraction_manifest.csv")).resolve()

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe input-dir: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    items = iter_source_items(input_dir)
    if not items:
        raise ValueError(f"No se encontraron documentos soportados en: {input_dir}")

    results: list[ExtractionResult] = []

    progress = tqdm(
        items,
        total=len(items),
        desc="Extrayendo documentos",
        unit="archivo",
        dynamic_ncols=True,
        disable=not sys.stderr.isatty(),
    )

    for item in progress:
        progress.set_postfix_str(item.relative_source.name)
        if item.extension in SUPPORTED_ARCHIVE_EXTENSIONS:
            archive_results = extract_rar(item, output_dir)
            results.extend(archive_results)
            for result in archive_results:
                target_label = result.output_path.relative_to(output_dir)
                member_label = f"::{result.archive_member}" if result.archive_member else ""
                tqdm.write(
                    f"[{result.status.upper()}] "
                    f"{item.relative_source}{member_label} -> {target_label}"
                )
            continue

        relative_source = item.relative_source
        target = output_dir / build_target_relative_path(item)
        target.parent.mkdir(parents=True, exist_ok=True)

        if args.skip_existing and target.exists():
            existing_text = target.read_text(encoding="utf-8", errors="ignore")
            results.append(
                ExtractionResult(
                    source_path=item.source_path,
                    relative_source=relative_source,
                    output_path=target,
                    extension=item.extension,
                    extractor="skipped",
                    status="skipped_existing",
                    char_count=len(existing_text.strip()),
                    note="TXT ya existía y fue preservado.",
                    archive_member="",
                    filename_cuce=extract_filename_cuce(relative_source),
                    content_cuce="",
                    cuce_match="not_checked",
                )
            )
            tqdm.write(f"[SKIP] {relative_source}")
            continue

        status = "ok"
        note = ""
        extractor = ""
        char_count = 0
        content_cuce = ""

        try:
            extractor, extracted_text = extract_one(item.source_path, target)
            char_count = len(extracted_text.strip())
            candidates = extract_cuce_candidates(extracted_text)
            content_cuce = candidates[0] if candidates else ""
            if char_count < 40:
                status = "warning_low_text"
                note = (
                    "Se extrajo muy poco texto; probablemente el documento es escaneado "
                    "o requiere OCR."
                )
        except Exception as exc:  # noqa: BLE001
            status = "error"
            note = str(exc)
            extractor = "failed"
            if target.exists():
                target.unlink()

        results.append(
            ExtractionResult(
                source_path=item.source_path,
                relative_source=relative_source,
                output_path=target,
                extension=item.extension,
                extractor=extractor,
                status=status,
                char_count=char_count,
                note=note,
                archive_member="",
                filename_cuce=extract_filename_cuce(relative_source),
                content_cuce=content_cuce,
                cuce_match=(
                    "match"
                    if content_cuce and extract_filename_cuce(relative_source) == content_cuce
                    else "mismatch"
                    if content_cuce and extract_filename_cuce(relative_source)
                    else "missing_content_cuce"
                    if not content_cuce
                    else "missing_filename_cuce"
                ),
            )
        )

        if status != "ok":
            tqdm.write(f"[{status.upper()}] {relative_source} -> {target.relative_to(output_dir)}")

    write_manifest(results, manifest_path)
    print()
    print(f"Manifest generado en: {manifest_path}")
    status_counts: dict[str, int] = {}
    for row in results:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
    return {
        "script": Path(__file__).name,
        "items_total": len(items),
        "results_total": len(results),
        "status_counts": status_counts,
        "manifest_path": str(manifest_path),
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
                "Extraccion documental completada.\n"
                f"Duracion: {elapsed:.1f}s\n"
                f"Script: {summary['script']}\n"
                f"Items fuente: {summary['items_total']}\n"
                f"Resultados: {summary['results_total']}\n"
                f"Estados: {summary['status_counts']}\n"
                f"Manifest: {summary['manifest_path']}\n"
                f"Resumen JSON: {report.json_path}"
            ),
            title="SICOES pipeline OK",
            tags=["white_check_mark", "page_facing_up"],
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
                "Extraccion documental fallida.\n"
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
