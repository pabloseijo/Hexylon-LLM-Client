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
from llm.tasks.task_models import (
    TaskMeasurement,
    TaskPlan,
    TaskResult,
    TaskStatus,
)


@dataclass
class SweepPlan:
    task_id: str
    machine_id_generator: str
    machine_id_hexylon: str
    freq_start_hz: float
    freq_stop_hz: float
    freq_step_hz: float
    commands: list[str]
    dwell_seconds: float
    output_file: str
    description: str


class SweepExecutor:
    def __init__(
        self,
        sweep_plan: SweepPlan,
        on_complete: Callable[[TaskResult], None] | None = None,
    ) -> None:
        self.sweep_plan = sweep_plan
        self.on_complete = on_complete

        self.plan = TaskPlan(
            commands=sweep_plan.commands,
            interval_seconds=sweep_plan.dwell_seconds,
            duration_seconds=self._estimate_duration(),
            output_file=sweep_plan.output_file,
            task_id=sweep_plan.task_id,
            description=sweep_plan.description,
            machine_id=sweep_plan.machine_id_hexylon,
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
        freqs: list[float] = []
        freq = self.sweep_plan.freq_start_hz

        while freq <= self.sweep_plan.freq_stop_hz + 1:
            freqs.append(freq)
            freq += self.sweep_plan.freq_step_hz

        return freqs

    def _estimate_duration(self) -> float:
        freqs = self._build_freqs()
        return len(freqs) * self.sweep_plan.dwell_seconds

    def start(self) -> None:
        if self.is_running:
            raise RuntimeError(
                f"El barrido {self.sweep_plan.task_id} ya está en ejecución."
            )

        self._cancel_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"sweep-{self.sweep_plan.task_id}",
            daemon=True,
        )
        self._thread.start()

    def cancel(self) -> None:
        self._cancel_event.set()

    def wait(self, timeout: float | None = None) -> TaskResult | None:
        if self._thread:
            self._thread.join(timeout=timeout)
        return self._result

    def _run(self) -> None:
        freqs = self._build_freqs()
        output_path = Path(self.sweep_plan.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        measurements: list[TaskMeasurement] = []
        started_at = datetime.now()

        try:
            with open(output_path, "w", newline="") as csvfile:
                fieldnames = [
                    "timestamp",
                    "frequency_hz",
                    "frequency_mhz",
                ] + self.sweep_plan.commands

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

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

                    try:
                        send_generator_command(
                            freq_cmd,
                            machine_id=self.sweep_plan.machine_id_generator,
                        )
                    except (GeneratorClientError, Exception) as exc:
                        raise RuntimeError(
                            f"Error configurando {freq_cmd}: {exc}"
                        ) from exc

                    time.sleep(self.sweep_plan.dwell_seconds)

                    timestamp = datetime.now()
                    values: dict[str, str] = {}

                    row = {
                        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "frequency_hz": freq_hz,
                        "frequency_mhz": freq_mhz,
                    }
                    
                    send_scpi_command(
                        freq_cmd,
                        machine_id=self.sweep_plan.machine_id_hexylon,
                    )

                    time.sleep(0.5)

                    try:
                        send_scpi_command(
                            "LOCK?",
                            machine_id=self.sweep_plan.machine_id_hexylon,
                        )
                    except Exception:
                        pass

                    time.sleep(0.5)

                    for command in self.sweep_plan.commands:
                        try:
                            response = send_scpi_command(
                                command,
                                machine_id=self.sweep_plan.machine_id_hexylon,
                            )
                            values[command] = response.strip()
                        except Exception as exc:
                            values[command] = f"ERROR: {exc}"

                        row[command] = values[command]

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
                        "type": "sweep_progress",
                        "task_id": self.sweep_plan.task_id,
                        "data": {
                            "current_freq_mhz": freq_mhz,
                            "current_step": len(measurements),
                            "total_steps": len(freqs),
                            "percent": round(len(measurements) / len(freqs) * 100),
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


_active_sweeps: dict[str, SweepExecutor] = {}
_lock = threading.Lock()


def launch_sweep(
    sweep_plan: SweepPlan,
    on_complete: Callable[[TaskResult], None] | None = None,
) -> SweepExecutor:
    def _on_complete_wrapper(result: TaskResult) -> None:
        with _lock:
            _active_sweeps.pop(result.plan.task_id, None)

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

    executor = SweepExecutor(sweep_plan, on_complete=_on_complete_wrapper)

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
        _active_sweeps[executor.plan.task_id] = executor

    executor.start()

    notify_event({
        "type": "task_created",
        "task_id": executor.plan.task_id,
        "data": task_executor_to_api(executor.plan.task_id, executor),
    })

    return executor

def get_active_sweeps() -> dict[str, SweepExecutor]:
    with _lock:
        return dict(_active_sweeps)


def cancel_sweep(task_id: str) -> bool:
    with _lock:
        executor = _active_sweeps.get(task_id)

    if executor:
        executor.cancel()
        return True

    return False