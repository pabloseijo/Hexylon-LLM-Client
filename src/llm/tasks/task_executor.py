"""
Ejecutor de tareas para el cliente LLM de Hexylon.

Recibe un TaskPlan y lo ejecuta en un hilo separado, enviando los comandos
SCPI al equipo a través del MCP en cada iteración y guardando los resultados
en un CSV de forma incremental.

El executor es completamente determinista — no invoca al LLM.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Callable

from llm.clients.mcp_client import send_scpi_command
from llm.tasks.csv_writer import CsvWriter
from llm.tasks.task_models import (
    TaskMeasurement,
    TaskPlan,
    TaskResult,
    TaskStatus,
)


class TaskExecutor:
    """
    Ejecuta un TaskPlan de forma asíncrona en un hilo separado.

    El hilo puede cancelarse en cualquier momento llamando a cancel().
    Al terminar notifica al caller mediante un callback opcional.

    Parameters
    ----------
    plan:
        El plan de tarea a ejecutar.
    on_complete:
        Callback opcional que recibe el TaskResult al finalizar la tarea.
        Se ejecuta desde el hilo de la tarea, no desde el hilo principal.
    """

    def __init__(
        self,
        plan: TaskPlan,
        on_complete: Callable[[TaskResult], None] | None = None,
    ) -> None:
        self.plan = plan
        self.on_complete = on_complete

        self._thread: threading.Thread | None = None
        self._cancel_event = threading.Event()
        self._result: TaskResult | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def result(self) -> TaskResult | None:
        return self._result

    def start(self) -> None:
        """
        Lanza la ejecución de la tarea en un hilo separado.

        Raises
        ------
        RuntimeError
            Si la tarea ya está en ejecución.
        """
        if self.is_running:
            raise RuntimeError(
                f"La tarea {self.plan.task_id} ya está en ejecución."
            )

        self._cancel_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"task-{self.plan.task_id}",
            daemon=True,
        )
        self._thread.start()

    def cancel(self) -> None:
        """Solicita la cancelación de la tarea en ejecución."""
        self._cancel_event.set()

    def wait(self, timeout: float | None = None) -> TaskResult | None:
        """
        Espera a que la tarea termine.

        Parameters
        ----------
        timeout:
            Tiempo máximo de espera en segundos. None = espera indefinida.

        Returns
        -------
        TaskResult | None
            El resultado de la tarea, o None si el timeout expiró.
        """
        if self._thread:
            self._thread.join(timeout=timeout)
        return self._result

    def _run(self) -> None:
        """Bucle principal de ejecución. Se ejecuta en el hilo de la tarea."""
        measurements: list[TaskMeasurement] = []
        started_at = datetime.now()
        writer = CsvWriter(self.plan.output_file, self.plan.commands)

        try:
            writer.open()
            iteration = 0
            end_time = time.monotonic() + self.plan.duration_seconds

            while time.monotonic() < end_time:
                if self._cancel_event.is_set():
                    self._result = TaskResult(
                        plan=self.plan,
                        status=TaskStatus.CANCELLED,
                        measurements=measurements,
                        output_file=self.plan.output_file,
                        started_at=started_at,
                        finished_at=datetime.now(),
                    )
                    if self.on_complete:
                        self.on_complete(self._result)
                    return

                iteration += 1
                timestamp = datetime.now()
                values: dict[str, str] = {}

                for command in self.plan.commands:
                    try:
                        response = send_scpi_command(command)
                        values[command] = response.strip()
                    except Exception as exc:
                        values[command] = f"ERROR: {exc}"

                measurement = TaskMeasurement(
                    timestamp=timestamp,
                    iteration=iteration,
                    values=values,
                )
                measurements.append(measurement)
                writer.write_row(measurement)

                # Esperar hasta el próximo intervalo, pero responder a cancel
                remaining = end_time - time.monotonic()
                wait_time = min(self.plan.interval_seconds, remaining)
                if wait_time > 0:
                    self._cancel_event.wait(timeout=wait_time)

            self._result = TaskResult(
                plan=self.plan,
                status=TaskStatus.COMPLETED,
                measurements=measurements,
                output_file=self.plan.output_file,
                started_at=started_at,
                finished_at=datetime.now(),
            )

        except Exception as exc:
            self._result = TaskResult(
                plan=self.plan,
                status=TaskStatus.FAILED,
                measurements=measurements,
                output_file=None,
                error=str(exc),
                started_at=started_at,
                finished_at=datetime.now(),
            )

        finally:
            writer.close()
            if self.on_complete and self._result:
                self.on_complete(self._result)


# ---------------------------------------------------------------------------
# Registro global de tareas activas
# ---------------------------------------------------------------------------

_active_tasks: dict[str, TaskExecutor] = {}
_lock = threading.Lock()


def launch_task(
    plan: TaskPlan,
    on_complete: Callable[[TaskResult], None] | None = None,
) -> TaskExecutor:
    """
    Lanza una tarea y la registra en el registro global.

    Parameters
    ----------
    plan:
        El plan de tarea a ejecutar.
    on_complete:
        Callback opcional que recibe el TaskResult al finalizar.

    Returns
    -------
    TaskExecutor
        El executor en ejecución.
    """
    def _on_complete_wrapper(result: TaskResult) -> None:
        with _lock:
            _active_tasks.pop(result.plan.task_id, None)
        if on_complete:
            on_complete(result)

    executor = TaskExecutor(plan, on_complete=_on_complete_wrapper)
    executor.start()

    with _lock:
        _active_tasks[plan.task_id] = executor

    return executor


def get_active_tasks() -> dict[str, TaskExecutor]:
    """Devuelve una copia del registro de tareas activas."""
    with _lock:
        return dict(_active_tasks)


def cancel_task(task_id: str) -> bool:
    """
    Cancela una tarea activa por su ID.

    Returns
    -------
    bool
        True si la tarea existía y fue cancelada, False si no se encontró.
    """
    with _lock:
        executor = _active_tasks.get(task_id)
    if executor:
        executor.cancel()
        return True
    return False