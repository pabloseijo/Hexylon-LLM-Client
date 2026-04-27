from __future__ import annotations

import re
from typing import Any

from llm.memory.session_memory import session_memory
from llm.memory.session_log import session_log, EventType
from llm.memory.task_history import task_history
from llm.memory.conversation_history import conversation_history
from llm.tasks.task_executor import (
    cancel_task,
    get_active_tasks,
    launch_task,
)
from llm.tasks.task_models import TaskResult, TaskStatus
from llm.tasks.task_planner import try_plan_task


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _get_sorted_active_tasks() -> list[tuple[str, object]]:
    active = get_active_tasks()
    return sorted(active.items(), key=lambda item: item[0])


def _extract_explicit_task_id(
    user_input: str,
    active_task_ids: list[str],
) -> str | None:
    text = user_input.lower()
    for task_id in active_task_ids:
        if task_id.lower() in text:
            return task_id
    return None


def _extract_ordinal_index(user_input: str) -> int | None:
    text = user_input.lower().strip()
    patterns = (
        r"\btarea\s+(\d+)\b",
        r"\bla\s+tarea\s+(\d+)\b",
        r"\btask\s+(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def _resolve_task_id_for_cancel(user_input: str) -> tuple[str | None, str | None]:
    sorted_active = _get_sorted_active_tasks()
    if not sorted_active:
        return None, "No hay ninguna tarea activa en este momento."

    active_task_ids = [task_id for task_id, _ in sorted_active]
    text = user_input.lower().strip()

    explicit_task_id = _extract_explicit_task_id(user_input, active_task_ids)
    if explicit_task_id:
        return explicit_task_id, None

    ordinal_index = _extract_ordinal_index(user_input)
    if ordinal_index is not None:
        if 1 <= ordinal_index <= len(sorted_active):
            return sorted_active[ordinal_index - 1][0], None
        return None, f"No existe la tarea {ordinal_index}."

    # fallback → última tarea
    if len(sorted_active) == 1:
        return sorted_active[0][0], None

    return sorted_active[-1][0], None


# ---------------------------------------------------------------------------
# Callback de finalización
# ---------------------------------------------------------------------------

def _on_task_complete(result: TaskResult) -> None:
    session_memory.set_last_completed_task(
        task_id=result.plan.task_id,
        output_file=result.output_file,
    )

    if result.status == TaskStatus.COMPLETED:
        task_history.record_completed(
            task_id=result.plan.task_id,
            output_file=result.output_file or "",
            measurements=result.total_measurements,
        )

    elif result.status == TaskStatus.CANCELLED:
        task_history.record_cancelled(
            task_id=result.plan.task_id,
            measurements=result.total_measurements,
        )

    elif result.status == TaskStatus.FAILED:
        task_history.record_failed(
            task_id=result.plan.task_id,
            error=result.error or "error desconocido",
        )

    conversation_history.add_assistant_message(
        f"[Sistema] Tarea {result.plan.task_id} finalizada con estado {result.status.value}."
    )


# ---------------------------------------------------------------------------
# Handlers públicos
# ---------------------------------------------------------------------------

def handle_launch_task(user_input: str) -> dict[str, Any] | str:
    plan_or_error = try_plan_task(user_input)

    if isinstance(plan_or_error, str):
        return plan_or_error

    plan = plan_or_error

    launch_task(plan, on_complete=_on_task_complete)

    session_memory.set_last_task_id(plan.task_id)

    task_history.record_launched(
        task_id=plan.task_id,
        description=plan.description,
        commands=plan.commands,
        interval_seconds=plan.interval_seconds,
        duration_seconds=plan.duration_seconds,
        output_file=plan.output_file,
    )

    return {
        "message": f"## Tarea lanzada\n\n- **ID**: `{plan.task_id}`\n- **Descripción**: {plan.description}",
        "task": {
            "task_id": plan.task_id,
            "description": plan.description,
            "commands": plan.commands,
            "interval_seconds": plan.interval_seconds,
            "duration_seconds": plan.duration_seconds,
            "output_file": plan.output_file,
            "status": "active",
        },
    }


def handle_cancel_task(user_input: str) -> str:
    target_id, error = _resolve_task_id_for_cancel(user_input)

    if error:
        return error

    cancelled = cancel_task(target_id)

    if not cancelled:
        return f"No se ha podido cancelar la tarea {target_id}."

    return f"Tarea {target_id} cancelada."


def handle_list_tasks() -> str:
    sorted_active = _get_sorted_active_tasks()

    if not sorted_active:
        return "No hay ninguna tarea activa."

    lines = [f"Tareas activas: {len(sorted_active)}"]

    for idx, (task_id, executor) in enumerate(sorted_active, start=1):
        plan = executor.plan
        lines.append(
            f"\n{idx}. {task_id} → {plan.description}"
        )

    return "\n".join(lines)