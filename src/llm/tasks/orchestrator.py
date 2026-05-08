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

SequenceStep = CommandStep | TaskStep | SweepStep


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

        elif isinstance(step, SweepStep):
            import time
            import csv
            from pathlib import Path as P

            freq = step.freq_start_hz
            freqs = []
            while freq <= step.freq_stop_hz + 1:
                freqs.append(freq)
                freq += step.freq_step_hz

            _log(i, step.machine_id_generator, "sweep",
                f"{step.freq_start_hz/1e6:.0f}-{step.freq_stop_hz/1e6:.0f}MHz "
                f"step={step.freq_step_hz/1e6:.0f}MHz points={len(freqs)}",
                "STARTED")

            # Preparar CSV
            output_path = P(step.output_file) if step.output_file else (
                P(__file__).parents[3] / "output" /
                f"sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)

            rows = []
            failed_at = None

            with open(output_path, "w", newline="") as csvfile:
                fieldnames = ["timestamp", "frequency_hz", "frequency_mhz"] + step.commands
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for freq_hz in freqs:
                    freq_mhz = freq_hz / 1e6
                    freq_cmd = f"FREQ {freq_mhz:.3f} MHz"

                    # 1. Configurar frecuencia en el generador
                    _log(i, step.machine_id_generator, "sweep_freq", freq_cmd, "SETTING")
                    try:
                        send_generator_command(freq_cmd, machine_id=step.machine_id_generator)
                    except (GeneratorClientError, Exception) as exc:
                        failed_at = f"Error configurando {freq_cmd}: {exc}"
                        break

                    # 2. Esperar dwell_seconds
                    time.sleep(step.dwell_seconds)

                    # 3. Medir en el Hexylon
                    row = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "frequency_hz": freq_hz,
                        "frequency_mhz": freq_mhz,
                    }
                    for cmd in step.commands:
                        try:
                            value = send_scpi_command(cmd, machine_id=step.machine_id_hexylon)
                            row[cmd] = value.strip()
                        except Exception as exc:
                            row[cmd] = f"ERROR: {exc}"

                    writer.writerow(row)
                    csvfile.flush()
                    rows.append(row)

                    _log(i, step.machine_id_generator, "sweep_freq", freq_cmd,
                        f"OK measurements={row}")

            if failed_at:
                return SequenceResult(
                    success=False,
                    steps_completed=i - 1,
                    steps_total=len(steps),
                    error=f"Barrido interrumpido en paso {i}: {failed_at}",
                    step_results=step_results,
                )

            # Registrar en historial
            from llm.memory.task_history import task_history
            from llm.memory.session_memory import session_memory

            sweep_task_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            task_history.record_launched(
                task_id=sweep_task_id,
                description=(
                    f"Barrido de frecuencia "
                    f"{step.freq_start_hz/1e6:.0f} MHz a "
                    f"{step.freq_stop_hz/1e6:.0f} MHz "
                    f"en pasos de {step.freq_step_hz/1e6:.0f} MHz"
                ),
                commands=step.commands,
                interval_seconds=step.dwell_seconds,
                duration_seconds=len(freqs) * step.dwell_seconds,
                output_file=str(output_path),
            )
            
            task_history.record_completed(
                task_id=sweep_task_id,
                output_file=str(output_path),
                measurements=len(rows),
            )
            
            session_memory.set_last_completed_task(
                task_id=sweep_task_id,
                output_file=str(output_path),
            )

            _log(i, step.machine_id_generator, "sweep",
                f"points={len(rows)} output={output_path}", "COMPLETED")

            step_results.append({
                "step": i,
                "type": "sweep",
                "machine_id_generator": step.machine_id_generator,
                "machine_id_hexylon": step.machine_id_hexylon,
                "freq_start_mhz": step.freq_start_hz / 1e6,
                "freq_stop_mhz": step.freq_stop_hz / 1e6,
                "freq_step_mhz": step.freq_step_hz / 1e6,
                "points": len(rows),
                "output_file": str(output_path),
                "status": "ok",
            })  
            
            
    return SequenceResult(
        success=True,
        steps_completed=len(steps),
        steps_total=len(steps),
        step_results=step_results,
    )