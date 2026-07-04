from __future__ import annotations

import argparse
import re
import sys
import time
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import PRIMARY_RAG_PATH, TABLES_DIR
from src.notifications import send_ntfy_notification
from src.run_reporting import save_run_summary

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9ÁÉÍÓÚáéíóúÑñÜü]+")
STOPWORDS = {
    "a",
    "al",
    "con",
    "contra",
    "de",
    "del",
    "el",
    "en",
    "la",
    "las",
    "los",
    "para",
    "por",
    "que",
    "se",
    "sin",
    "sus",
    "una",
    "uno",
    "un",
    "y",
}
OBJECT_STOPWORDS = STOPWORDS | {
    "adquisicion",
    "apoyo",
    "basado",
    "bienes",
    "codigo",
    "compra",
    "construccion",
    "contratacion",
    "diseno",
    "equipamiento",
    "gestion",
    "implementacion",
    "mantenimiento",
    "pedido",
    "proceso",
    "productos",
    "proyecto",
    "reconstruccion",
    "refaccion",
    "segundo",
    "servicio",
    "servicios",
    "soluciones",
    "sistema",
    "tecnica",
}
ENTITY_STOPWORDS = STOPWORDS | {
    "autonomo",
    "autonomo",
    "caja",
    "centro",
    "clinico",
    "clinica",
    "clinicas",
    "de",
    "del",
    "departamental",
    "el",
    "gobierno",
    "gestion",
    "hospital",
    "la",
    "los",
    "ministerio",
    "municipal",
    "nacional",
    "programa",
    "proyecto",
    "proyectos",
    "regional",
    "relaciones",
    "salud",
    "san",
    "santa",
    "servicio",
    "sistema",
    "unidad",
    "exteriores",
}
GENERIC_PATTERNS = [
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in [
        r"modelo de documento base de contrataci[oó]n",
        r"normativa aplicable al proceso de contrataci[oó]n",
        r"proponentes elegibles",
        r"garant[ií]as",
        r"declaratoria desierta",
        r"resoluciones recurribles",
        r"presentaci[oó]n de propuestas",
        r"formulario [a-z0-9-]+",
        r"documentos de la propuesta",
        r"cronograma de plazos",
        r"licitaci[oó]n p[uú]blica",
        r"servicios generales",
        r"contrato administrativo",
        r"expresiones de inter[eé]s",
        r"firma[s]? consultora[s]?",
        r"decreto supremo n[°o]?\s*0181",
        r"nb-sabs",
    ]
]
DOMAIN_KEYWORDS = {
    "software": {"software", "codigo", "abierto", "informatica", "informatico", "sistema", "gestion", "clinica", "clinico"},
    "farmaceutico": {"medicamento", "medicamentos", "farmacia", "farmaceutico", "farmaceuticos", "amoxicilina", "insumo", "insumos"},
    "reactivos": {"reactivo", "reactivos", "hematologico", "laboratorio", "anatomia", "patologica", "contador"},
    "obras": {"obra", "obras", "alcantarillado", "pluvial", "cemento", "camaras", "refaccion", "reconstruccion", "construccion", "vias"},
    "rescate": {"rescate", "aeronaves", "incendios", "estructurales", "herramientas", "entrada", "forzada", "ssei"},
    "papel": {"papel", "equipamiento", "sub", "alcaldia", "funcionamiento"},
}


@dataclass(slots=True)
class AuditResult:
    cuce: str
    source_name: str
    status: str
    reason: str
    object_token_overlap: float
    entity_token_overlap: float
    generic_score: int
    base_domain: str
    text_domain: str
    object_keywords_present: str
    entity_keywords_present: str
    preview: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita la calidad de DBC extraídos por CUCE.")
    parser.add_argument(
        "--base-rag-path",
        type=Path,
        default=PRIMARY_RAG_PATH,
        help="Dataset base RAG en parquet o csv.",
    )
    parser.add_argument(
        "--texts-dir",
        type=Path,
        default=ROOT / "data" / "intermediate" / "curated_docs_text",
        help="Carpeta con DBC extraídos en .txt.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=TABLES_DIR / "dbc_quality_audit.csv",
        help="CSV de salida con el resultado de la auditoría.",
    )
    return parser.parse_args()


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_accents.lower()


def tokenize(value: str, *, entity_mode: bool = False) -> list[str]:
    tokens = [normalize_text(token) for token in TOKEN_PATTERN.findall(value or "")]
    stopwords = ENTITY_STOPWORDS if entity_mode else STOPWORDS
    return [token for token in tokens if len(token) > 2 and token not in stopwords]


def load_base_rag(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError(f"Formato no soportado para base RAG: {path.suffix}")
    return frame


def infer_domain(tokens: set[str]) -> str:
    best_domain = "unknown"
    best_score = 0
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = len(tokens.intersection(keywords))
        if score > best_score:
            best_domain = domain
            best_score = score
    return best_domain


def compute_generic_score(text: str) -> int:
    return sum(1 for pattern in GENERIC_PATTERNS if pattern.search(text))


def overlap_ratio(expected_tokens: list[str], observed_tokens: set[str]) -> tuple[float, list[str]]:
    unique_expected = list(dict.fromkeys(expected_tokens))
    if not unique_expected:
        return 0.0, []
    matched = [token for token in unique_expected if token in observed_tokens]
    return len(matched) / len(unique_expected), matched


def select_object_tokens(objeto: str) -> list[str]:
    tokens = [token for token in tokenize(objeto) if token not in OBJECT_STOPWORDS]
    if not tokens:
        return []
    counts = Counter(tokens)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _ in ranked[:12]]


def select_entity_tokens(entidad: str) -> list[str]:
    tokens = tokenize(entidad, entity_mode=True)
    if not tokens:
        return []
    return list(dict.fromkeys(tokens))[:6]


def classify_result(
    *,
    object_overlap: float,
    entity_overlap: float,
    generic_score: int,
    base_domain: str,
    text_domain: str,
    normalized_text: str,
) -> tuple[str, str]:
    domain_mismatch = (
        base_domain != "unknown"
        and text_domain != "unknown"
        and base_domain != text_domain
    )
    if base_domain == "software" and (
        "contrato de obras" in normalized_text
        or "ejecucion de obra" in normalized_text
        or "personal de la obra" in normalized_text
    ):
        return "reject", "software_vs_obras_contradiction"
    if base_domain == "obras" and (
        "productos farmaceuticos" in normalized_text
        or "medicamentos" in normalized_text
        or "farmacia institucional" in normalized_text
    ):
        return "reject", "obras_vs_farmaceutico_contradiction"
    if base_domain in {"farmaceutico", "reactivos"} and (
        "expresiones de interes" in normalized_text
        or "firmas consultoras" in normalized_text
        or "consultor individual" in normalized_text
    ):
        return "reject", "salud_vs_consultoria_contradiction"
    if domain_mismatch and object_overlap < 0.25:
        return "reject", "domain_mismatch"
    if object_overlap == 0 and entity_overlap == 0 and generic_score >= 2:
        return "reject", "generic_without_alignment"
    if generic_score >= 8 and entity_overlap == 0 and object_overlap < 0.5:
        return "reject", "high_generic_low_alignment"
    if entity_overlap == 0 and object_overlap < 0.2 and generic_score >= 3:
        return "reject", "weak_alignment_and_generic"
    if object_overlap >= 0.45 and entity_overlap >= 0.2 and generic_score <= 5:
        return "accept", "aligned_object_and_entity"
    if object_overlap >= 0.25 and not domain_mismatch:
        return "review", "partial_object_alignment"
    return "review", "manual_review_recommended"


def main() -> dict[str, object]:
    args = parse_args()
    base_rag = load_base_rag(args.base_rag_path)
    base_rag = base_rag.drop_duplicates("cuce").copy()
    base_by_cuce = base_rag.set_index("cuce").to_dict(orient="index")

    results: list[AuditResult] = []
    txt_paths = sorted(args.texts_dir.glob("*-documento_base_contratacion.txt"))
    missing_in_base = 0

    for path in txt_paths:
        cuce = path.name.split("-documento_base_contratacion", 1)[0]
        row = base_by_cuce.get(cuce)
        if row is None:
            missing_in_base += 1
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        normalized_text = normalize_text(text)
        text_tokens = set(tokenize(text))

        object_tokens = select_object_tokens(str(row.get("objeto_contratacion", "")))
        entity_tokens = select_entity_tokens(str(row.get("entidad", "")))

        object_overlap, object_matched = overlap_ratio(object_tokens, text_tokens)
        entity_overlap, entity_matched = overlap_ratio(entity_tokens, text_tokens)
        generic_score = compute_generic_score(text)

        base_domain = infer_domain(set(object_tokens))
        text_domain = infer_domain(text_tokens)
        status, reason = classify_result(
            object_overlap=object_overlap,
            entity_overlap=entity_overlap,
            generic_score=generic_score,
            base_domain=base_domain,
            text_domain=text_domain,
            normalized_text=normalized_text,
        )

        preview_lines = [line.strip() for line in text.splitlines() if line.strip()]
        preview = " | ".join(preview_lines[:8])[:350]
        results.append(
            AuditResult(
                cuce=cuce,
                source_name=path.name,
                status=status,
                reason=reason,
                object_token_overlap=round(object_overlap, 4),
                entity_token_overlap=round(entity_overlap, 4),
                generic_score=generic_score,
                base_domain=base_domain,
                text_domain=text_domain,
                object_keywords_present="|".join(object_matched),
                entity_keywords_present="|".join(entity_matched),
                preview=preview,
            )
        )

    output_frame = pd.DataFrame([asdict(result) for result in results]).sort_values(
        ["status", "reason", "cuce"]
    )
    output_frame["entidad"] = output_frame["cuce"].map(
        lambda cuce: str(base_by_cuce.get(cuce, {}).get("entidad", ""))
    )
    output_frame["objeto_contratacion"] = output_frame["cuce"].map(
        lambda cuce: str(base_by_cuce.get(cuce, {}).get("objeto_contratacion", ""))
    )
    output_frame["tipo_contratacion"] = output_frame["cuce"].map(
        lambda cuce: str(base_by_cuce.get(cuce, {}).get("tipo_contratacion", ""))
    )
    output_frame["modalidad"] = output_frame["cuce"].map(
        lambda cuce: str(base_by_cuce.get(cuce, {}).get("modalidad", ""))
    )

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    output_frame.to_csv(args.output_path, index=False, encoding="utf-8-sig")

    status_counts = output_frame["status"].value_counts().to_dict()
    print("Auditoria DBC guardada en:", args.output_path)
    print("DBC auditados:", len(output_frame))
    print("DBC sin base asociada:", missing_in_base)
    print("Conteo por estado:", status_counts)

    return {
        "script": Path(__file__).name,
        "audited_dbc": len(output_frame),
        "missing_in_base": missing_in_base,
        "status_counts": status_counts,
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
                "Auditoria automatica de calidad DBC completada.\n"
                f"Duracion: {elapsed:.1f}s\n"
                f"DBC auditados: {summary['audited_dbc']}\n"
                f"Sin base asociada: {summary['missing_in_base']}\n"
                f"Salida CSV: {summary['output_path']}\n"
                f"Resumen JSON: {report.json_path}"
            ),
            title="SICOES DBC audit OK",
            tags=["mag", "white_check_mark"],
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
                "Auditoria automatica de calidad DBC fallida.\n"
                f"Duracion: {elapsed:.1f}s\n"
                f"Error: {exc}\n"
                f"Resumen JSON: {report.json_path}"
            ),
            title="SICOES DBC audit ERROR",
            tags=["warning", "x"],
            priority=4,
        )
        raise
