from __future__ import annotations

import argparse
import csv
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.notifications import send_ntfy_notification
from src.run_reporting import save_run_summary

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".rar"}


@dataclass
class LogEntry:
    timestamp: str
    page: str
    order_in_page: int
    cuce: str
    label: str
    url: str


@dataclass
class DownloadFile:
    path: Path
    extension: str
    mtime_ns: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Renombra descargas de SICOES usando el log CSV exportado por Tampermonkey "
            "y el orden temporal de los archivos descargados."
        )
    )
    parser.add_argument(
        "--downloads-dir",
        required=True,
        type=Path,
        help="Carpeta donde quedaron los archivos descargados con nombres aleatorios.",
    )
    parser.add_argument(
        "--log-csv",
        required=True,
        type=Path,
        help="CSV exportado por el userscript de Tampermonkey.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Carpeta destino para los archivos renombrados.",
    )
    parser.add_argument(
        "--document-slug",
        default="documento_base_contratacion",
        help="Slug que se usara en el nombre final del archivo.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copia archivos al destino. Si no se indica, mueve los archivos.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica cambios reales. Si no se indica, solo muestra un dry-run.",
    )
    parser.add_argument(
        "--strict-counts",
        action="store_true",
        help=(
            "Falla si la cantidad del log no coincide exactamente con los archivos "
            "descargados."
        ),
    )
    parser.add_argument(
        "--start-sequence",
        type=int,
        default=1,
        help=(
            "Numero de fila del log desde la cual continuar el procesamiento. "
            "Usa 1 para una corrida completa."
        ),
    )
    parser.add_argument(
        "--skip-existing-targets",
        action="store_true",
        help=(
            "Si el archivo destino ya existe, lo marca en el manifest y continua "
            "sin sobrescribir."
        ),
    )
    return parser.parse_args()


def load_log_entries(path: Path) -> list[LogEntry]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(
                LogEntry(
                    timestamp=(row.get("timestamp") or "").strip(),
                    page=(row.get("page") or "").strip(),
                    order_in_page=int((row.get("order_in_page") or "0").strip() or 0),
                    cuce=(row.get("cuce") or "").strip(),
                    label=(row.get("label") or "").strip(),
                    url=(row.get("url") or "").strip(),
                )
            )
    if not rows:
        raise ValueError(f"El log CSV no contiene filas: {path}")
    return rows


def iter_download_files(path: Path) -> Iterable[DownloadFile]:
    for child in path.iterdir():
        if not child.is_file():
            continue
        if child.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        stat = child.stat()
        yield DownloadFile(path=child, extension=child.suffix.lower(), mtime_ns=stat.st_mtime_ns)


def load_download_files(path: Path) -> list[DownloadFile]:
    files = sorted(
        iter_download_files(path),
        key=lambda item: (item.mtime_ns, item.path.name.lower()),
    )
    if not files:
        raise ValueError(f"No se encontraron archivos descargados compatibles en: {path}")
    return files


def sanitize_slug(value: str) -> str:
    return "_".join(part for part in value.strip().lower().split() if part)


def build_target_name(cuce: str, document_slug: str, extension: str) -> str:
    return f"{cuce}-{sanitize_slug(document_slug)}{extension}"


def write_manifest(rows: list[dict[str, str]], path: Path) -> None:
    fieldnames = [
        "sequence",
        "timestamp",
        "page",
        "order_in_page",
        "cuce",
        "label",
        "source_name",
        "target_name",
        "mode",
        "status",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> dict[str, object]:
    args = parse_args()
    if args.start_sequence < 1:
        raise ValueError("--start-sequence debe ser mayor o igual a 1.")

    all_log_entries = load_log_entries(args.log_csv)
    log_entries = all_log_entries[args.start_sequence - 1 :]
    download_files = load_download_files(args.downloads_dir)
    if args.strict_counts and len(log_entries) != len(download_files):
        raise ValueError(
            "Cantidad inconsistente entre log y archivos descargados: "
            f"log={len(log_entries)} archivos={len(download_files)}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, str]] = []
    pair_count = min(len(log_entries), len(download_files))
    missing_downloads = len(log_entries) - pair_count
    orphan_files = len(download_files) - pair_count

    print("Modo:", "APPLY" if args.apply else "DRY-RUN")
    print("Accion:", "copy" if args.copy else "move")
    print("Descargas:", args.downloads_dir)
    print("Log CSV:", args.log_csv)
    print("Salida:", args.output_dir)
    print("Inicio desde fila:", args.start_sequence)
    print("Registros en log desde inicio:", len(log_entries))
    print("Archivos descargados detectados:", len(download_files))
    print("Total de pares a procesar:", pair_count)
    if missing_downloads > 0:
        print(
            "Advertencia: faltan archivos descargados para "
            f"{missing_downloads} filas del log. Se marcaran como missing_download."
        )
    if orphan_files > 0:
        print(
            "Advertencia: sobran archivos descargados sin fila correspondiente en el log: "
            f"{orphan_files}. Se marcaran como orphan_download."
        )
    print()

    paired_entries = list(zip(log_entries[:pair_count], download_files[:pair_count]))
    progress = tqdm(
        paired_entries,
        total=pair_count,
        desc="Renombrando descargas",
        unit="archivo",
        dynamic_ncols=True,
        disable=not sys.stderr.isatty(),
    )

    for sequence, (entry, download) in enumerate(progress, start=args.start_sequence):
        progress.set_postfix_str(download.path.name)
        target_name = build_target_name(entry.cuce, args.document_slug, download.extension)
        target_path = args.output_dir / target_name

        if target_path.exists():
            if args.skip_existing_targets:
                tqdm.write(f"[{sequence:04d}] SKIPPED_EXISTING_TARGET -> {target_name}")
                manifest_rows.append(
                    {
                        "sequence": str(sequence),
                        "timestamp": entry.timestamp,
                        "page": entry.page,
                        "order_in_page": str(entry.order_in_page),
                        "cuce": entry.cuce,
                        "label": entry.label,
                        "source_name": download.path.name,
                        "target_name": target_name,
                        "mode": "copy" if args.copy else "move",
                        "status": "skipped_existing_target",
                    }
                )
                continue
            raise FileExistsError(f"El destino ya existe y no sera sobreescrito: {target_path}")

        status = "planned"
        if args.apply:
            if args.copy:
                shutil.copy2(download.path, target_path)
            else:
                shutil.move(str(download.path), str(target_path))
            status = "copied" if args.copy else "moved"

        manifest_rows.append(
            {
                "sequence": str(sequence),
                "timestamp": entry.timestamp,
                "page": entry.page,
                "order_in_page": str(entry.order_in_page),
                "cuce": entry.cuce,
                "label": entry.label,
                "source_name": download.path.name,
                "target_name": target_name,
                "mode": "copy" if args.copy else "move",
                "status": status,
            }
        )

    for offset, entry in enumerate(log_entries[pair_count:], start=args.start_sequence + pair_count):
        tqdm.write(f"[{offset:04d}] MISSING_DOWNLOAD -> {entry.cuce}")
        manifest_rows.append(
            {
                "sequence": str(offset),
                "timestamp": entry.timestamp,
                "page": entry.page,
                "order_in_page": str(entry.order_in_page),
                "cuce": entry.cuce,
                "label": entry.label,
                "source_name": "",
                "target_name": build_target_name(entry.cuce, args.document_slug, ""),
                "mode": "copy" if args.copy else "move",
                "status": "missing_download",
            }
        )

    for offset, download in enumerate(
        download_files[pair_count:],
        start=args.start_sequence + pair_count,
    ):
        tqdm.write(f"[{offset:04d}] ORPHAN_DOWNLOAD -> {download.path.name}")
        manifest_rows.append(
            {
                "sequence": str(offset),
                "timestamp": "",
                "page": "",
                "order_in_page": "",
                "cuce": "",
                "label": "",
                "source_name": download.path.name,
                "target_name": "",
                "mode": "copy" if args.copy else "move",
                "status": "orphan_download",
            }
        )

    manifest_path = args.output_dir / "rename_manifest.csv"
    write_manifest(manifest_rows, manifest_path)

    print()
    print(f"Manifest generado en: {manifest_path}")
    if not args.apply:
        print("No se aplicaron cambios. Usa --apply para ejecutar copia o movimiento real.")
    return {
        "script": Path(__file__).name,
        "mode": "apply" if args.apply else "dry-run",
        "start_sequence": args.start_sequence,
        "pair_count": pair_count,
        "missing_downloads": missing_downloads,
        "orphan_files": orphan_files,
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
                "Renombrado de descargas completado.\n"
                f"Duracion: {elapsed:.1f}s\n"
                f"Script: {summary['script']}\n"
                f"Modo: {summary['mode']}\n"
                f"Pares procesados: {summary['pair_count']}\n"
                f"Missing downloads: {summary['missing_downloads']}\n"
                f"Orphan files: {summary['orphan_files']}\n"
                f"Manifest: {summary['manifest_path']}\n"
                f"Resumen JSON: {report.json_path}"
            ),
            title="SICOES pipeline OK",
            tags=["white_check_mark", "file_folder"],
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
                "Renombrado de descargas fallido.\n"
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
