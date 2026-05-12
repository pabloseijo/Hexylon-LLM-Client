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

from llm.clients.generator_client import (
    GeneratorClientError,
    send_generator_command,
)

from llm.clients.mcp_client import MCPClientError, send_scpi_command
from llm.tasks.task_models import TaskPlan, TaskStatus
from llm.tasks.task_executor import launch_task
from llm.tasks.sweep_executor import SweepPlan, launch_sweep
from llm.tasks.matrix_sweep_executor import MatrixSweepPlan, launch_matrix_sweep

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

@dataclass
class SweepStep:
    """Barrido de frecuencias — configura el generador en cada paso y mide en el Hexylon."""
    machine_id_generator: str
    machine_id_hexylon: str
    freq_start_hz: float
    freq_stop_hz: float
    freq_step_hz: float
    commands: list[str]           # comandos a medir en el Hexylon en cada paso
    dwell_seconds: float = 5.0    # tiempo de espera en cada frecuencia antes de medir
    output_file: str = ""

@dataclass
class MatrixSweepStep:
    machine_id_generator: str
    machine_ids_hexylon: list[str]
    freq_start_hz: float
    freq_stop_hz: float
    freq_step_hz: float
    power_start_dbm: float
    power_stop_dbm: float
    power_step_dbm: float
    commands: list[str]
    dwell_seconds: float = 5.0
    output_file: str = ""
    
SequenceStep = CommandStep | TaskStep | SweepStep | MatrixSweepStep
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

                # Actualizar session_memory con la máquina usada
                from llm.memory.session_memory import session_memory
                session_memory.set_last_machine_id(step.machine_id)

                _log(i, step.machine_id, "command", step.command, f"OK response={response!r}")
                step_results.append({
                    "step": i,
                    "type": "command",
                    "machine_id": step.machine_id,
                    "command": step.command,
                    "response": response,
                    "status": "ok",
                })
            except (MCPClientError, GeneratorClientError) as exc:
                _log(i, step.machine_id, "command", step.command, f"FAILED error={exc}")

                return SequenceResult(
                    success=False,
                    steps_completed=i - 1,
                    steps_total=len(steps),
                    error=f"Paso {i} falló al ejecutar comando: {exc}",
                    step_results=step_results,
                )

        elif isinstance(step, TaskStep):
            _log(i, step.machine_id, "task", step.plan.task_id, "STARTED")

            try:
                from llm.memory.task_history import task_history
                from llm.memory.session_memory import session_memory

                task_history.record_launched(
                    task_id=step.plan.task_id,
                    description=step.plan.description,
                    commands=step.plan.commands,
                    interval_seconds=step.plan.interval_seconds,
                    duration_seconds=step.plan.duration_seconds,
                    output_file=step.plan.output_file,
                )

                session_memory.set_last_task_id(step.plan.task_id)

                def _on_complete(result):
                    session_memory.set_last_completed_task(
                        task_id=result.plan.task_id,
                        output_file=result.output_file,
                    )

                    if result.status == TaskStatus.COMPLETED:
                        task_history.record_completed(
                            task_id=result.plan.task_id,
                            output_file=result.output_file or "",
                            measurements=result.total_measurements,
                            stop_reason=result.stop_reason,
                        )
                    elif result.status == TaskStatus.CANCELLED:
                        task_history.record_cancelled(
                            task_id=result.plan.task_id,
                            measurements=result.total_measurements,
                            stop_reason=result.stop_reason,
                        )
                    elif result.status == TaskStatus.FAILED:
                        task_history.record_failed(
                            task_id=result.plan.task_id,
                            error=result.error or "error desconocido",
                        )

                launch_task(step.plan, on_complete=_on_complete)

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
                _log(
                    i,
                    step.machine_id,
                    "task",
                    step.plan.task_id,
                    f"FAILED error={exc}",
                )

                return SequenceResult(
                    success=False,
                    steps_completed=i - 1,
                    steps_total=len(steps),
                    error=f"Paso {i} falló (tarea {step.plan.task_id}): {exc}",
                    step_results=step_results,
                )

        elif isinstance(step, SweepStep):
            from pathlib import Path as P

            freq = step.freq_start_hz
            freqs = []

            while freq <= step.freq_stop_hz + 1:
                freqs.append(freq)
                freq += step.freq_step_hz

            output_path = P(step.output_file) if step.output_file else (
                P(__file__).parents[3] / "output" /
                f"sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)

            sweep_task_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            sweep_plan = SweepPlan(
                task_id=sweep_task_id,
                machine_id_generator=step.machine_id_generator,
                machine_id_hexylon=step.machine_id_hexylon,
                freq_start_hz=step.freq_start_hz,
                freq_stop_hz=step.freq_stop_hz,
                freq_step_hz=step.freq_step_hz,
                commands=step.commands,
                dwell_seconds=step.dwell_seconds,
                output_file=str(output_path),
                description=(
                    f"Barrido de frecuencia "
                    f"{step.freq_start_hz/1e6:.0f} MHz a "
                    f"{step.freq_stop_hz/1e6:.0f} MHz "
                    f"en pasos de {step.freq_step_hz/1e6:.0f} MHz"
                ),
            )

            try:
                launch_sweep(sweep_plan)

                _log(
                    i,
                    step.machine_id_generator,
                    "sweep",
                    f"{step.freq_start_hz/1e6:.0f}-{step.freq_stop_hz/1e6:.0f}MHz "
                    f"step={step.freq_step_hz/1e6:.0f}MHz points={len(freqs)} "
                    f"task_id={sweep_task_id}",
                    "LAUNCHED",
                )

                step_results.append({
                    "step": i,
                    "type": "sweep",
                    "machine_id_generator": step.machine_id_generator,
                    "machine_id_hexylon": step.machine_id_hexylon,
                    "task_id": sweep_task_id,
                    "freq_start_mhz": step.freq_start_hz / 1e6,
                    "freq_stop_mhz": step.freq_stop_hz / 1e6,
                    "freq_step_mhz": step.freq_step_hz / 1e6,
                    "points": len(freqs),
                    "output_file": str(output_path),
                    "status": "launched",
                })

            except Exception as exc:
                _log(
                    i,
                    step.machine_id_generator,
                    "sweep",
                    str(output_path),
                    f"FAILED error={exc}",
                )

                return SequenceResult(
                    success=False,
                    steps_completed=i - 1,
                    steps_total=len(steps),
                    error=f"Paso {i} falló al lanzar el barrido: {exc}",
                    step_results=step_results,
                )

        elif isinstance(step, MatrixSweepStep):
            from pathlib import Path as P

            freqs = []
            freq = step.freq_start_hz
            while freq <= step.freq_stop_hz + 1:
                freqs.append(freq)
                freq += step.freq_step_hz

            powers = []
            power = step.power_start_dbm
            if step.power_step_dbm > 0:
                while power <= step.power_stop_dbm + 1e-9:
                    powers.append(power)
                    power += step.power_step_dbm
            else:
                while power >= step.power_stop_dbm - 1e-9:
                    powers.append(power)
                    power += step.power_step_dbm

            output_path = P(step.output_file) if step.output_file else (
                P(__file__).parents[3] / "output" /
                f"matrix_sweep_{int(step.freq_start_hz/1e6)}-{int(step.freq_stop_hz/1e6)}MHz"
                f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)

            task_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            matrix_plan = MatrixSweepPlan(
                task_id=task_id,
                machine_id_generator=step.machine_id_generator,
                machine_ids_hexylon=step.machine_ids_hexylon,
                freq_start_hz=step.freq_start_hz,
                freq_stop_hz=step.freq_stop_hz,
                freq_step_hz=step.freq_step_hz,
                power_start_dbm=step.power_start_dbm,
                power_stop_dbm=step.power_stop_dbm,
                power_step_dbm=step.power_step_dbm,
                commands=step.commands,
                dwell_seconds=step.dwell_seconds,
                output_file=str(output_path),
                description=(
                    f"Barrido matricial frecuencia/potencia: "
                    f"{step.freq_start_hz/1e6:.0f}-{step.freq_stop_hz/1e6:.0f} MHz "
                    f"paso {step.freq_step_hz/1e6:.0f} MHz; "
                    f"{step.power_start_dbm:g} a {step.power_stop_dbm:g} dBm "
                    f"paso {step.power_step_dbm:g} dB; "
                    f"equipos {', '.join(step.machine_ids_hexylon)}"
                ),
            )

            try:
                launch_matrix_sweep(matrix_plan)

                _log(
                    i,
                    step.machine_id_generator,
                    "matrix_sweep",
                    f"freq_points={len(freqs)} power_points={len(powers)} "
                    f"total={len(freqs) * len(powers)} task_id={task_id}",
                    "LAUNCHED",
                )

                step_results.append({
                    "step": i,
                    "type": "matrix_sweep",
                    "task_id": task_id,
                    "machine_id_generator": step.machine_id_generator,
                    "machine_ids_hexylon": step.machine_ids_hexylon,
                    "freq_start_mhz": step.freq_start_hz / 1e6,
                    "freq_stop_mhz": step.freq_stop_hz / 1e6,
                    "freq_step_mhz": step.freq_step_hz / 1e6,
                    "power_start_dbm": step.power_start_dbm,
                    "power_stop_dbm": step.power_stop_dbm,
                    "power_step_dbm": step.power_step_dbm,
                    "freq_points": len(freqs),
                    "power_points": len(powers),
                    "points": len(freqs) * len(powers),
                    "output_file": str(output_path),
                    "status": "launched",
                })

            except Exception as exc:
                _log(
                    i,
                    step.machine_id_generator,
                    "matrix_sweep",
                    str(output_path),
                    f"FAILED error={exc}",
                )

                return SequenceResult(
                    success=False,
                    steps_completed=i - 1,
                    steps_total=len(steps),
                    error=f"Paso {i} falló al lanzar el barrido matricial: {exc}",
                    step_results=step_results,
                )
                
    return SequenceResult(
        success=True,
        steps_completed=len(steps),
        steps_total=len(steps),
        step_results=step_results,
    )