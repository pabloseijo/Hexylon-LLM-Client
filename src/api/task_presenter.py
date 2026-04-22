from __future__ import annotations

from typing import TYPE_CHECKING, Any

from llm.tasks.task_models import TaskResult

if TYPE_CHECKING:
    from llm.tasks.task_executor import TaskExecutor


def task_executor_to_api(task_id: str, executor: "TaskExecutor") -> dict[str, Any]:
    plan = executor.plan

    return {
        "task_id": task_id,
        "description": plan.description,
        "commands": plan.commands,
        "interval_seconds": plan.interval_seconds,
        "duration_seconds": plan.duration_seconds,
        "output_file": plan.output_file,
        "status": "active",
        "started_at": None,
        "finished_at": None,
        "measurements": None,
        "error": None,
        "stop_reason": None,
    }


def task_result_to_api(result: TaskResult) -> dict[str, Any]:
    plan = result.plan

    return {
        "task_id": plan.task_id,
        "description": plan.description,
        "commands": plan.commands,
        "interval_seconds": plan.interval_seconds,
        "duration_seconds": plan.duration_seconds,
        "output_file": result.output_file,
        "status": result.status.value,
        "started_at": (
            result.started_at.strftime("%Y-%m-%d %H:%M:%S")
            if result.started_at
            else None
        ),
        "finished_at": (
            result.finished_at.strftime("%Y-%m-%d %H:%M:%S")
            if result.finished_at
            else None
        ),
        "measurements": result.total_measurements,
        "error": result.error,
        "stop_reason": result.stop_reason,
    }


def task_history_entry_to_api(entry: dict[str, Any]) -> dict[str, Any]:
    raw_status = entry.get("status")

    if raw_status == "running":
        normalized_status = "failed"
        error = entry.get("error") or "Tarea huérfana de una sesión anterior"
    else:
        normalized_status = raw_status
        error = entry.get("error")

    return {
        "task_id": entry.get("task_id"),
        "description": entry.get("description", ""),
        "commands": entry.get("commands", []),
        "interval_seconds": entry.get("interval_seconds", 0.0),
        "duration_seconds": entry.get("duration_seconds", 0.0),
        "output_file": entry.get("output_file"),
        "status": normalized_status,
        "started_at": entry.get("started_at"),
        "finished_at": entry.get("finished_at"),
        "measurements": entry.get("measurements"),
        "error": error,
        "stop_reason": entry.get("stop_reason"),
    }