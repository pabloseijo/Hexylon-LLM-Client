"""
Puente seguro entre código síncrono y el sistema de notificaciones del backend.

Este módulo NO debe emitir eventos de ciclo de vida de tarea si dichos eventos
ya se generan en task_executor.py, que es la fuente de verdad del estado de
ejecución.

Uso previsto:
- eventos auxiliares, por ejemplo task_alert
- puntos del sistema que necesiten publicar en la cola de notificaciones
  sin importar directamente server.py
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

NotifyFn = Callable[[dict[str, Any]], None]

_notify_fn: NotifyFn | None = None


def set_notify_fn(fn: NotifyFn) -> None:
    """Registra la función de notificación global del backend."""
    global _notify_fn
    _notify_fn = fn


def notify_event(event: dict[str, Any]) -> None:
    """
    Publica un evento de forma segura.

    La notificación nunca debe romper el flujo del hilo llamador.
    """
    if _notify_fn is None:
        logger.warning("No hay función de notificación registrada. Evento descartado: %s", event)
        return

    try:
        _notify_fn(event)
    except Exception:
        logger.exception("Error enviando evento de notificación: %s", event)


def notify_task_alert(task_id: str, alert_message: str) -> None:
    """Emite una alerta asociada a una tarea existente."""
    notify_event({
        "type": "task_alert",
        "task_id": task_id,
        "data": {
            "message": alert_message,
        },
    })