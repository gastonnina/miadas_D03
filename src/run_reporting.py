"""Persistencia reusable de resúmenes de ejecución."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import RUN_SUMMARIES_DIR


@dataclass(slots=True)
class RunSummaryResult:
    """Rutas generadas al persistir un resumen de corrida."""

    record: dict[str, Any]
    json_path: Path
    history_path: Path


def save_run_summary(
    *,
    script: str,
    success: bool,
    elapsed_seconds: float,
    summary: dict[str, Any] | None = None,
    error: str = "",
    output_dir: Path | None = None,
) -> RunSummaryResult:
    """Guarda un resumen timestamped y lo agrega a un histórico JSONL."""

    target_dir = output_dir or RUN_SUMMARIES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    hostname = socket.gethostname()
    safe_script = script.replace(".py", "").replace("/", "_")

    record = {
        "timestamp_utc": timestamp,
        "hostname": hostname,
        "script": script,
        "success": success,
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "summary": summary or {},
        "error": error,
    }

    json_path = target_dir / f"{timestamp}_{safe_script}.json"
    json_path.write_text(
        json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    history_path = target_dir / "history.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")

    latest_path = target_dir / f"{safe_script}_latest.json"
    latest_path.write_text(
        json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return RunSummaryResult(
        record=record,
        json_path=json_path,
        history_path=history_path,
    )
