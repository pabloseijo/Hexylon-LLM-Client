"""
Modelos de datos para la rama de tareas del cliente LLM de Hexylon.

Define las estructuras que representan:
- un plan de tarea
- condiciones de alerta / parada
- una medición individual
- el resultado final de una tarea
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """Estado del ciclo de vida de una tarea."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _generate_task_id() -> str:
    """Genera un identificador único de tarea basado en timestamp."""
    return datetime.now().strftime("task_%Y%m%d_%H%M%S")


@dataclass
class TaskCondition:
    """
    Condición evaluable durante la ejecución de una tarea.

    Attributes
    ----------
    command:
        Comando SCPI sobre cuyo valor se evalúa la condición.
        Ejemplo: "MER?", "POW?", "CBER?", "LOCK?"
    operator:
        Operador de comparación.
        Soportados inicialmente: <, <=, >, >=, ==
    threshold_raw:
        Valor umbral en formato legible original.
        Ejemplo: "20 dB", "60 dBuV", "1E-4", "TRUE"
    action:
        Acción asociada a la condición:
        - "alert"
        - "stop"
    description:
        Texto legible de la condición.
    """
    command: str
    operator: str
    threshold_raw: str
    action: str
    description: str = ""

    def __post_init__(self) -> None:
        self.command = self.command if self.command.endswith("?") else f"{self.command}?"
        self.operator = self.operator.strip()
        self.action = self.action.strip().lower()

        valid_operators = {"<", "<=", ">", ">=", "=="}
        if self.operator not in valid_operators:
            raise ValueError(
                f"Operador no soportado en TaskCondition: {self.operator}"
            )

        if self.action not in {"alert", "stop"}:
            raise ValueError(
                f"Acción no soportada en TaskCondition: {self.action}"
            )

    def __str__(self) -> str:
        return self.description or (
            f"{self.action.upper()}: {self.command} {self.operator} {self.threshold_raw}"
        )


@dataclass
class TaskPlan:
    commands: list[str]
    interval_seconds: float
    duration_seconds: float
    output_file: str
    task_id: str = field(default_factory=_generate_task_id)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    alert_conditions: list[TaskCondition] = field(default_factory=list)
    stop_conditions: list[TaskCondition] = field(default_factory=list)
    machine_id: str | None = None  # ← NUEVO

    def __str__(self) -> str:
        lines = [
            f"Tarea {self.task_id}: {self.description}",
            f"  Comandos:    {', '.join(self.commands)}",
            f"  Intervalo:   {self.interval_seconds}s",
            f"  Duración:    {self.duration_seconds}s",
            f"  Iteraciones: {self.total_iterations}",
            f"  Salida:      {self.output_file}",
            f"  Máquina:     {self.machine_id or 'default'}",  # ← NUEVO
        ]
        if self.alert_conditions:
            lines.append("  Alertas:")
            for condition in self.alert_conditions:
                lines.append(f"    - {condition}")
        if self.stop_conditions:
            lines.append("  Parada automática:")
            for condition in self.stop_conditions:
                lines.append(f"    - {condition}")
        return "\n".join(lines)

@dataclass
class TaskMeasurement:
    """
    Una fila de medición capturada durante la ejecución de una tarea.

    Attributes
    ----------
    timestamp:
        Momento exacto en que se tomó la medición.
    iteration:
        Número de iteración (empieza en 1).
    values:
        Diccionario comando → valor devuelto por el equipo.
    """
    timestamp: datetime
    iteration: int
    values: dict[str, str]

@dataclass
class TriggeredAlert:
    """
    Alerta disparada durante la ejecución de una tarea.
    """
    timestamp: datetime
    iteration: int
    command: str
    current_value: str
    operator: str
    threshold_raw: str
    message: str

    def summary_line(self) -> str:
        ts = self.timestamp.strftime("%H:%M:%S")
        return (
            f"[{ts}] iteración {self.iteration} — "
            f"{self.command} = {self.current_value} {self.operator} {self.threshold_raw}"
        )

@dataclass
class TaskResult:
    """
    Resultado final de la ejecución de una tarea.

    Attributes
    ----------
    plan:
        El plan que se ejecutó.
    status:
        Estado final de la tarea.
    measurements:
        Lista de mediciones capturadas.
    output_file:
        Ruta del CSV generado. None si la tarea falló antes de escribir.
    error:
        Mensaje de error si la tarea falló.
    started_at:
        Timestamp de inicio de ejecución.
    finished_at:
        Timestamp de finalización.
    triggered_alerts:
        Lista de alertas disparadas durante la ejecución.
    stop_reason:
        Motivo explícito de parada si terminó por condición.
    """
    plan: TaskPlan
    status: TaskStatus
    measurements: list[TaskMeasurement] = field(default_factory=list)
    output_file: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    triggered_alerts: list[TriggeredAlert] = field(default_factory=list)
    stop_reason: str | None = None

    @property
    def total_measurements(self) -> int:
        return len(self.measurements)

    @property
    def elapsed_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def summary(self) -> str:
        status_str = self.status.value.upper()
        lines = [
            f"Tarea {self.plan.task_id} — {status_str}",
            f"  Descripción:  {self.plan.description}",
            f"  Mediciones:   {self.total_measurements} / {self.plan.total_iterations}",
        ]

        if self.elapsed_seconds is not None:
            lines.append(f"  Tiempo total: {self.elapsed_seconds:.1f}s")

        if self.output_file:
            lines.append(f"  CSV guardado: {self.output_file}")

        if self.stop_reason:
            lines.append(f"  Motivo stop:  {self.stop_reason}")

        if self.triggered_alerts:
            lines.append("  Alertas:")
            for alert in self.triggered_alerts:
                lines.append(f"    - {alert.summary_line()}")

        if self.error:
            lines.append(f"  Error:        {self.error}")

        return "\n".join(lines)
    