"""
Orquestador de secuencias multi-máquina.

Ejecuta una lista de pasos en orden garantizado, donde cada paso
puede ser un comando simple o una tarea de medición periódica.

Cada paso se ejecuta solo después de que el anterior haya completado
correctamente. Si un paso falla, la secuencia se detiene.

El log de ejecución se escribe en tmp/orchestrator.log para validar
la secuencialidad.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from llm.clients.mock_generator_client import (
    GeneratorClientError,
    send_generator_command,
)
from llm.clients.mcp_client import MCPClientError, send_scpi_command
from llm.tasks.task_models import TaskPlan
from llm.tasks.task_executor import launch_task


_LOG_PATH = Path(__file__).parents[3] / "tmp" / "orchestrator.log"


def _write_log(entry: str) -> None:
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG_PATH, "a") as f:
        f.write(entry + "\n")


def _log(step: int, machine: str, action: str, detail: str, status: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    entry = (
        f"[{timestamp}] "
        f"step={step} "
        f"machine={machine} "
        f"action={action} "
        f"detail={detail!r} "
        f"status={status}"
    )
    _write_log(entry)
    print(f"[ORCHESTRATOR] {entry}")


# ---------------------------------------------------------------------------
# Modelos de pasos
# ---------------------------------------------------------------------------

@dataclass
class CommandStep:
    """Paso de comando simple — envía un comando y espera respuesta."""
    machine_id: str
    command: str
    machine_type: str = "hexylon"  # "hexylon" | "generator"


@dataclass
class TaskStep:
    """Paso de tarea periódica — lanza un TaskPlan y espera a que termine."""
    machine_id: str
    plan: TaskPlan


SequenceStep = CommandStep | TaskStep


# ---------------------------------------------------------------------------
# Orquestador
# ---------------------------------------------------------------------------

@dataclass
class SequenceResult:
    success: bool
    steps_completed: int
    steps_total: int
    error: str | None = None
    step_results: list[dict[str, Any]] = field(default_factory=list)


def run_sequence(steps: list[SequenceStep]) -> SequenceResult:
    """
    Ejecuta una lista de pasos en orden secuencial garantizado.

    Cada paso se ejecuta solo si el anterior tuvo éxito.
    Si un paso falla, la secuencia se detiene y se devuelve el error.

    Parameters
    ----------
    steps:
        Lista ordenada de pasos a ejecutar.

    Returns
    -------
    SequenceResult
        Resultado global de la secuencia.
    """
    step_results: list[dict[str, Any]] = []

    for i, step in enumerate(steps, start=1):
        if isinstance(step, CommandStep):
            _log(i, step.machine_id, "command", step.command, "STARTED")
            try:
                if step.machine_type == "generator":
                    response = send_generator_command(
                        step.command,
                        machine_id=step.machine_id,
                    )
                else:
                    response = send_scpi_command(
                        step.command,
                        machine_id=step.machine_id,
                    )

                _log(i, step.machine_id, "command", step.command, f"OK response={response!r}")
                step_results.append({
                    "step": i,
                    "type": "command",
                    "machine_id": step.machine_id,
                    "command": step.command,
                    "response": response,
                    "status": "ok",
                })

            except (MCPClientError, GeneratorClientError, Exception) as exc:
                _log(i, step.machine_id, "command", step.command, f"FAILED error={exc}")
                return SequenceResult(
                    success=False,
                    steps_completed=i - 1,
                    steps_total=len(steps),
                    error=f"Paso {i} falló ({step.machine_id} / {step.command}): {exc}",
                    step_results=step_results,
                )

        elif isinstance(step, TaskStep):
            _log(i, step.machine_id, "task", step.plan.task_id, "STARTED")
            try:
                # Lanzar en background — no bloquear con wait()
                launch_task(step.plan)

                _log(i, step.machine_id, "task", step.plan.task_id, "LAUNCHED")
                step_results.append({
                    "step": i,
                    "type": "task",
                    "machine_id": step.machine_id,
                    "task_id": step.plan.task_id,
                    "status": "launched",
                    "output_file": step.plan.output_file,
                })

            except Exception as exc:
                _log(i, step.machine_id, "task", step.plan.task_id, f"FAILED error={exc}")
                return SequenceResult(
                    success=False,
                    steps_completed=i - 1,
                    steps_total=len(steps),
                    error=f"Paso {i} falló (tarea {step.plan.task_id}): {exc}",
                    step_results=step_results,
                )
                
    return SequenceResult(
        success=True,
        steps_completed=len(steps),
        steps_total=len(steps),
        step_results=step_results,
    )