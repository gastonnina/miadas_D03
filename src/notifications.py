"""Utilidades reutilizables de notificacion para ejecuciones largas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from src.config import settings


@dataclass(slots=True)
class NotificationResult:
    """Resultado de una notificacion remota."""

    enabled: bool
    attempted: bool
    success: bool
    status_code: int | None
    endpoint: str | None
    detail: str


def ntfy_is_configured() -> bool:
    """Indica si hay configuracion suficiente para enviar notificaciones."""

    return settings.ntfy_enabled and bool(settings.ntfy_topic)


def send_ntfy_notification(
    message: str,
    *,
    title: str | None = None,
    tags: list[str] | tuple[str, ...] | None = None,
    priority: int | None = None,
    markdown: bool = False,
    click: str | None = None,
    actions: list[dict[str, Any]] | None = None,
    timeout_seconds: float = 10.0,
) -> NotificationResult:
    """Envia una notificacion a ntfy/ntf.sh usando variables de entorno del proyecto.

    La funcion es tolerante a errores: nunca lanza excepciones de red y devuelve
    un objeto con el estado final para que el caller decida si registrar o ignorar.
    """

    if not settings.ntfy_enabled:
        return NotificationResult(
            enabled=False,
            attempted=False,
            success=False,
            status_code=None,
            endpoint=None,
            detail="NTFY_ENABLED esta desactivado.",
        )

    if not settings.ntfy_topic:
        return NotificationResult(
            enabled=True,
            attempted=False,
            success=False,
            status_code=None,
            endpoint=None,
            detail="NTFY_TOPIC no esta configurado.",
        )

    endpoint = f"{settings.ntfy_server}/{settings.ntfy_topic}"
    headers = {"Content-Type": "text/plain; charset=utf-8"}

    if title:
        headers["Title"] = title
    if tags:
        headers["Tags"] = ",".join(str(tag).strip() for tag in tags if str(tag).strip())
    if priority is not None:
        headers["Priority"] = str(priority)
    if markdown:
        headers["Markdown"] = "yes"
    if click:
        headers["Click"] = click
    if actions:
        headers["Actions"] = "; ".join(_format_action(action) for action in actions)
    if settings.ntfy_token:
        headers["Authorization"] = f"Bearer {settings.ntfy_token}"

    try:
        response = requests.post(
            endpoint,
            data=message.encode("utf-8"),
            headers=headers,
            timeout=timeout_seconds,
        )
        success = response.ok
        detail = "ok" if success else response.text.strip() or response.reason
        return NotificationResult(
            enabled=True,
            attempted=True,
            success=success,
            status_code=response.status_code,
            endpoint=endpoint,
            detail=detail,
        )
    except requests.RequestException as exc:
        return NotificationResult(
            enabled=True,
            attempted=True,
            success=False,
            status_code=None,
            endpoint=endpoint,
            detail=str(exc),
        )


def _format_action(action: dict[str, Any]) -> str:
    """Serializa una accion simple para el header `Actions` de ntfy."""

    action_name = str(action.get("action", "")).strip()
    label = str(action.get("label", "")).strip()
    url = str(action.get("url", "")).strip()
    clear = str(action.get("clear", "")).strip()

    parts = [action_name, label, url]
    if clear:
        parts.append(f"clear={clear}")
    return ", ".join(part for part in parts if part)
