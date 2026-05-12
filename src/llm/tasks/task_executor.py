"""
Ejecutor de tareas para el cliente LLM de Hexylon.

Recibe un TaskPlan y lo ejecuta en un hilo separado, enviando los comandos
SCPI al equipo a través del MCP en cada iteración y guardando los resultados
en un CSV de forma incremental.

Soporta:
- cancelación manual
- condiciones de alerta
- condiciones de parada automática

El executor es completamente determinista — no invoca al LLM.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Callable

from api.task_presenter import task_executor_to_api, task_result_to_api
from api.task_notifier import notify_event
from llm.clients.mcp_client import send_scpi_command
from llm.tasks.condition_evaluator import (
    ConditionEvaluationError,
    evaluate_condition,
)
from llm.tasks.csv_writer import CsvWriter
from llm.tasks.task_models import (
    TaskCondition,
    TaskMeasurement,
    TaskPlan,
    TaskResult,
    TaskStatus,
    TriggeredAlert,
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
        self._triggered_alert_keys: set[str] = set()

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

    def _evaluate_alert_conditions(
        self,
        measurement_values: dict[str, str],
        triggered_alerts: list[TriggeredAlert],
        iteration: int,
        timestamp: datetime,
    ) -> None:
        """
        Evalúa condiciones de alerta y acumula solo las nuevas.
        """
        for condition in self.plan.alert_conditions:
            matched, message = self._safe_evaluate_condition(
                condition=condition,
                measurement_values=measurement_values,
            )

            if not matched:
                continue

            current_value = measurement_values.get(condition.command, "N/D")

            alert_key = (
                f"{condition.command}|{condition.operator}|"
                f"{condition.threshold_raw}|{condition.action}"
            )

            if alert_key in self._triggered_alert_keys:
                continue

            self._triggered_alert_keys.add(alert_key)

            alert = TriggeredAlert(
                timestamp=timestamp,
                iteration=iteration,
                command=condition.command,
                current_value=current_value,
                operator=condition.operator,
                threshold_raw=condition.threshold_raw,
                message=message or condition.description or str(condition),
            )
            triggered_alerts.append(alert)

            notify_event({
                "type": "task_alert",
                "task_id": self.plan.task_id,
                "data": {
                    "message": alert.message,
                    "command": alert.command,
                    "current_value": alert.current_value,
                    "iteration": alert.iteration,
                },
            })

            ts = timestamp.strftime("%H:%M:%S")
            print("\n")
            print("!" * 60)
            print(
                f"[{ts}] ALERTA iteración {iteration} — "
                f"{condition.command} = {current_value} "
                f"{condition.operator} {condition.threshold_raw}"
            )
            print("!" * 60)
            print(">>> ", end="", flush=True)

    def _evaluate_stop_conditions(
        self,
        measurement_values: dict[str, str],
    ) -> str | None:
        """
        Evalúa condiciones de parada.

        Returns
        -------
        str | None
            Motivo de parada si se cumple alguna condición, o None.
        """
        for condition in self.plan.stop_conditions:
            matched, message = self._safe_evaluate_condition(
                condition=condition,
                measurement_values=measurement_values,
            )
            if matched:
                return message or str(condition)
        return None

    def _safe_evaluate_condition(
        self,
        condition: TaskCondition,
        measurement_values: dict[str, str],
    ) -> tuple[bool, str | None]:
        """
        Evalúa una condición capturando errores de comparación para no romper
        la tarea completa.
        """
        try:
            return evaluate_condition(condition, measurement_values)
        except ConditionEvaluationError as exc:
            return False, (
                f"No se pudo evaluar la condición '{condition}': {exc}"
            )

    def _run(self) -> None:
        """Bucle principal de ejecución. Se ejecuta en el hilo de la tarea."""
        measurements: list[TaskMeasurement] = []
        triggered_alerts: list[TriggeredAlert] = []
        stop_reason: str | None = None

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
                        triggered_alerts=triggered_alerts,
                        stop_reason=stop_reason,
                    )
                    return

                iteration += 1
                timestamp = datetime.now()
                values: dict[str, str] = {}

                for command in self.plan.commands:
                    try:
                        response = send_scpi_command(command, machine_id=self.plan.machine_id)
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
                
                # Emitir progreso por WebSocket
                total_iterations = max(
                    1,
                    int(self.plan.duration_seconds / self.plan.interval_seconds),
                )

                notify_event({
                    "type": "task_progress",
                    "task_id": self.plan.task_id,
                    "data": {
                        "current_step": iteration,
                        "total_steps": total_iterations,
                        "percent": min(
                            100,
                            round(iteration / total_iterations * 100),
                        ),
                        "elapsed_seconds": round(
                            (datetime.now() - started_at).total_seconds(),
                            1,
                        ),
                    },
                })

                self._evaluate_alert_conditions(
                    measurement_values=values,
                    triggered_alerts=triggered_alerts,
                    iteration=iteration,
                    timestamp=timestamp,
                )

                stop_reason = self._evaluate_stop_conditions(
                    measurement_values=values,
                )
                if stop_reason:
                    self._result = TaskResult(
                        plan=self.plan,
                        status=TaskStatus.COMPLETED,
                        measurements=measurements,
                        output_file=self.plan.output_file,
                        started_at=started_at,
                        finished_at=datetime.now(),
                        triggered_alerts=triggered_alerts,
                        stop_reason=stop_reason,
                    )
                    return

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
                triggered_alerts=triggered_alerts,
                stop_reason=stop_reason,
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
                triggered_alerts=triggered_alerts,
                stop_reason=stop_reason,
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

        api_task = task_result_to_api(result)

        if result.status == TaskStatus.COMPLETED:
            notify_event({
                "type": "task_completed",
                "task_id": result.plan.task_id,
                "data": api_task,
            })

        elif result.status == TaskStatus.CANCELLED:
            notify_event({
                "type": "task_cancelled",
                "task_id": result.plan.task_id,
                "data": api_task,
            })

        elif result.status == TaskStatus.FAILED:
            notify_event({
                "type": "task_failed",
                "task_id": result.plan.task_id,
                "data": api_task,
            })

        if on_complete:
            on_complete(result)

    executor = TaskExecutor(plan, on_complete=_on_complete_wrapper)
    executor.start()

    with _lock:
        _active_tasks[plan.task_id] = executor

    notify_event({
        "type": "task_created",
        "task_id": plan.task_id,
        "data": task_executor_to_api(plan.task_id, executor),
    })

    return executor

def get_active_tasks() -> dict[str, TaskExecutor]:
    """Devuelve una copia del registro de tareas activas."""
    from llm.tasks.sweep_executor import get_active_sweeps

    with _lock:
        active = dict(_active_tasks)

    active.update(get_active_sweeps())
    return active

def cancel_task(task_id: str) -> bool:
    with _lock:
        executor = _active_tasks.get(task_id)

    if executor:
        executor.cancel()
        return True

    from llm.tasks.sweep_executor import cancel_sweep

    return cancel_sweep(task_id)