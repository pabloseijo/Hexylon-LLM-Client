"""
Puente entre el pipeline síncrono y el servidor WebSocket asyncio.

El pipeline corre en hilos síncronos pero necesita notificar al frontend
React cuando una tarea termina. Este módulo actúa como puente.

Uso en pipeline.py — modificar _on_task_complete():

    from llm.api.task_notifier import notify_task_completed, notify_task_alert

    def _on_task_complete(result: TaskResult) -> None:
        # ... código existente ...
        notify_task_completed(result)
"""

from __future__ import annotations

from llm.tasks.task_models import TaskResult, TaskStatus


# Referencia al notify_task_event del servidor.
# Se inyecta cuando el servidor arranca para evitar import circular.
_notify_fn = None


def set_notify_fn(fn) -> None:
    """Llamado desde server.py al arrancar para registrar la función de notificación."""
    global _notify_fn
    _notify_fn = fn


def _notify(event: dict) -> None:
    if _notify_fn is not None:
        _notify_fn(event)


def notify_task_completed(result: TaskResult) -> None:
    if result.status == TaskStatus.COMPLETED:
        _notify({
            "type": "task_completed",
            "task_id": result.plan.task_id,
            "data": {
                "description": result.plan.description,
                "measurements": result.total_measurements,
                "output_file": result.output_file or "",
                "stop_reason": result.stop_reason or None,
            },
        })
    elif result.status == TaskStatus.CANCELLED:
        _notify({
            "type": "task_cancelled",
            "task_id": result.plan.task_id,
            "data": {
                "description": result.plan.description,
                "measurements": result.total_measurements,
            },
        })
    elif result.status == TaskStatus.FAILED:
        _notify({
            "type": "task_failed",
            "task_id": result.plan.task_id,
            "data": {
                "description": result.plan.description,
                "error": result.error or "error desconocido",
            },
        })


def notify_task_alert(task_id: str, alert_message: str) -> None:
    _notify({
        "type": "task_alert",
        "task_id": task_id,
        "data": {"message": alert_message},
    })