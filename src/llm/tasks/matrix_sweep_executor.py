from __future__ import annotations

import csv
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from api.task_notifier import notify_event
from api.task_presenter import task_executor_to_api, task_result_to_api
from llm.clients.generator_client import GeneratorClientError, send_generator_command
from llm.clients.mcp_client import send_scpi_command
from llm.memory.session_memory import session_memory
from llm.memory.task_history import task_history
from llm.tasks.task_models import TaskMeasurement, TaskPlan, TaskResult, TaskStatus


@dataclass
class MatrixSweepPlan:
    task_id: str
    machine_id_generator: str
    machine_ids_hexylon: list[str]

    freq_start_hz: float
    freq_stop_hz: float
    freq_step_hz: float

    power_start_dbm: float
    power_stop_dbm: float
    power_step_dbm: float

    commands: list[str]
    dwell_seconds: float
    output_file: str
    description: str

class MatrixSweepExecutor:
    def __init__(
        self,
        matrix_plan: MatrixSweepPlan,
        on_complete: Callable[[TaskResult], None] | None = None,
    ) -> None:
        self.matrix_plan = matrix_plan
        self.on_complete = on_complete

        self.plan = TaskPlan(
            commands=matrix_plan.commands,
            interval_seconds=matrix_plan.dwell_seconds,
            duration_seconds=self._estimate_duration(),
            output_file=matrix_plan.output_file,
            task_id=matrix_plan.task_id,
            description=matrix_plan.description,
            machine_id=",".join(matrix_plan.machine_ids_hexylon),
        )

        self._thread: threading.Thread | None = None
        self._cancel_event = threading.Event()
        self._result: TaskResult | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def result(self) -> TaskResult | None:
        return self._result

    def _build_freqs(self) -> list[float]:
        values: list[float] = []
        value = self.matrix_plan.freq_start_hz

        while value <= self.matrix_plan.freq_stop_hz + 1:
            values.append(value)
            value += self.matrix_plan.freq_step_hz

        return values

    def _build_powers(self) -> list[float]:
        values: list[float] = []
        value = self.matrix_plan.power_start_dbm
        step = self.matrix_plan.power_step_dbm

        if step == 0:
            return values

        if step > 0:
            while value <= self.matrix_plan.power_stop_dbm + 1e-9:
                values.append(value)
                value += step
        else:
            while value >= self.matrix_plan.power_stop_dbm - 1e-9:
                values.append(value)
                value += step

        return values

    def _estimate_duration(self) -> float:
        return (
            len(self._build_freqs())
            * len(self._build_powers())
            * self.matrix_plan.dwell_seconds
        )

    def start(self) -> None:
        if self.is_running:
            raise RuntimeError(
                f"El barrido matricial {self.matrix_plan.task_id} ya está en ejecución."
            )

        self._cancel_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"matrix-sweep-{self.matrix_plan.task_id}",
            daemon=True,
        )
        self._thread.start()

    def cancel(self) -> None:
        self._cancel_event.set()

    def wait(self, timeout: float | None = None) -> TaskResult | None:
        if self._thread:
            self._thread.join(timeout=timeout)
        return self._result

    def _configure_generator_power(self, power_dbm: float) -> None:
        power_cmd = f"POW {power_dbm:g}dBm"

        try:
            send_generator_command(
                power_cmd,
                machine_id=self.matrix_plan.machine_id_generator,
            )
        except (GeneratorClientError, Exception) as exc:
            raise RuntimeError(
                f"Error configurando {power_cmd}: {exc}"
            ) from exc

    def _configure_generator_frequency(self, freq_cmd: str) -> None:
        try:
            send_generator_command(
                freq_cmd,
                machine_id=self.matrix_plan.machine_id_generator,
            )
        except (GeneratorClientError, Exception) as exc:
            raise RuntimeError(
                f"Error configurando {freq_cmd}: {exc}"
            ) from exc

    def _configure_hexylon_frequency(
        self,
        machine_id: str,
        freq_cmd: str,
    ) -> str | None:
        try:
            response = send_scpi_command(
                freq_cmd,
                machine_id=machine_id,
            )

            time.sleep(0.5)

            try:
                send_scpi_command(
                    "LOCK?",
                    machine_id=machine_id,
                )
            except Exception:
                pass

            time.sleep(0.5)

            return response.strip()

        except Exception as exc:
            return f"ERROR configurando frecuencia: {exc}"

    def _run(self) -> None:
        freqs = self._build_freqs()
        powers = self._build_powers()
        total_steps = max(1, len(freqs) * len(powers))

        output_path = Path(self.matrix_plan.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        measurements: list[TaskMeasurement] = []
        started_at = datetime.now()

        try:
            fieldnames = [
                "timestamp",
                "generator_power_dbm",
                "generator_frequency_hz",
                "generator_frequency_mhz",
            ]

            for machine_id in self.matrix_plan.machine_ids_hexylon:
                fieldnames.append(f"{machine_id}_frequency_set_response")
                for command in self.matrix_plan.commands:
                    fieldnames.append(f"{machine_id}_{command}")

            with open(output_path, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for power_dbm in powers:
                    if self._cancel_event.is_set():
                        self._result = TaskResult(
                            plan=self.plan,
                            status=TaskStatus.CANCELLED,
                            measurements=measurements,
                            output_file=str(output_path),
                            started_at=started_at,
                            finished_at=datetime.now(),
                            stop_reason="Cancelado manualmente",
                        )
                        return

                    self._configure_generator_power(power_dbm)

                    for freq_hz in freqs:
                        if self._cancel_event.is_set():
                            self._result = TaskResult(
                                plan=self.plan,
                                status=TaskStatus.CANCELLED,
                                measurements=measurements,
                                output_file=str(output_path),
                                started_at=started_at,
                                finished_at=datetime.now(),
                                stop_reason="Cancelado manualmente",
                            )
                            return

                        freq_mhz = freq_hz / 1e6
                        freq_cmd = f"FREQ {freq_mhz:.3f} MHz"

                        self._configure_generator_frequency(freq_cmd)

                        time.sleep(self.matrix_plan.dwell_seconds)

                        timestamp = datetime.now()
                        values: dict[str, str] = {}

                        row = {
                            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"),
                            "generator_power_dbm": power_dbm,
                            "generator_frequency_hz": freq_hz,
                            "generator_frequency_mhz": freq_mhz,
                        }

                        for machine_id in self.matrix_plan.machine_ids_hexylon:
                            set_key = f"{machine_id}_frequency_set_response"

                            frequency_response = self._configure_hexylon_frequency(
                                machine_id=machine_id,
                                freq_cmd=freq_cmd,
                            )

                            row[set_key] = frequency_response or "OK"

                            if frequency_response and frequency_response.startswith("ERROR"):
                                for command in self.matrix_plan.commands:
                                    key = f"{machine_id}_{command}"
                                    values[key] = frequency_response
                                    row[key] = values[key]
                                continue

                            for command in self.matrix_plan.commands:
                                key = f"{machine_id}_{command}"

                                try:
                                    response = send_scpi_command(
                                        command,
                                        machine_id=machine_id,
                                    )
                                    values[key] = response.strip()
                                except Exception as exc:
                                    values[key] = f"ERROR: {exc}"

                                row[key] = values[key]

                        writer.writerow(row)
                        csvfile.flush()

                        measurements.append(
                            TaskMeasurement(
                                timestamp=timestamp,
                                iteration=len(measurements) + 1,
                                values=values,
                            )
                        )

                        notify_event({
                            "type": "matrix_sweep_progress",
                            "task_id": self.matrix_plan.task_id,
                            "data": {
                                "current_freq_mhz": freq_mhz,
                                "current_power_dbm": power_dbm,
                                "current_step": len(measurements),
                                "total_steps": total_steps,
                                "percent": round(
                                    len(measurements) / total_steps * 100
                                ),
                            },
                        })

            self._result = TaskResult(
                plan=self.plan,
                status=TaskStatus.COMPLETED,
                measurements=measurements,
                output_file=str(output_path),
                started_at=started_at,
                finished_at=datetime.now(),
            )

        except Exception as exc:
            self._result = TaskResult(
                plan=self.plan,
                status=TaskStatus.FAILED,
                measurements=measurements,
                output_file=str(output_path),
                error=str(exc),
                started_at=started_at,
                finished_at=datetime.now(),
            )

        finally:
            if self.on_complete and self._result:
                self.on_complete(self._result)

_active_matrix_sweeps: dict[str, MatrixSweepExecutor] = {}
_lock = threading.Lock()


def launch_matrix_sweep(
    matrix_plan: MatrixSweepPlan,
    on_complete: Callable[[TaskResult], None] | None = None,
) -> MatrixSweepExecutor:
    def _on_complete_wrapper(result: TaskResult) -> None:
        with _lock:
            _active_matrix_sweeps.pop(result.plan.task_id, None)

        if result.status == TaskStatus.COMPLETED:
            task_history.record_completed(
                task_id=result.plan.task_id,
                output_file=result.output_file or result.plan.output_file,
                measurements=result.total_measurements,
                stop_reason=result.stop_reason,
            )
            session_memory.set_last_completed_task(
                task_id=result.plan.task_id,
                output_file=result.output_file or result.plan.output_file,
            )
            event_type = "task_completed"

        elif result.status == TaskStatus.CANCELLED:
            task_history.record_cancelled(
                task_id=result.plan.task_id,
                measurements=result.total_measurements,
                stop_reason=result.stop_reason,
            )
            event_type = "task_cancelled"

        else:
            task_history.record_failed(
                task_id=result.plan.task_id,
                error=result.error or "error desconocido",
            )
            event_type = "task_failed"

        notify_event({
            "type": event_type,
            "task_id": result.plan.task_id,
            "data": task_result_to_api(result),
        })

        if on_complete:
            on_complete(result)

    executor = MatrixSweepExecutor(matrix_plan, on_complete=_on_complete_wrapper)

    task_history.record_launched(
        task_id=executor.plan.task_id,
        description=executor.plan.description,
        commands=executor.plan.commands,
        interval_seconds=executor.plan.interval_seconds,
        duration_seconds=executor.plan.duration_seconds,
        output_file=executor.plan.output_file,
    )

    session_memory.set_last_task_id(executor.plan.task_id)

    with _lock:
        _active_matrix_sweeps[executor.plan.task_id] = executor

    executor.start()

    notify_event({
        "type": "task_created",
        "task_id": executor.plan.task_id,
        "data": task_executor_to_api(executor.plan.task_id, executor),
    })

    return executor


def get_active_matrix_sweeps() -> dict[str, MatrixSweepExecutor]:
    with _lock:
        return dict(_active_matrix_sweeps)


def cancel_matrix_sweep(task_id: str) -> bool:
    with _lock:
        executor = _active_matrix_sweeps.get(task_id)

    if executor:
        executor.cancel()
        return True

    return False