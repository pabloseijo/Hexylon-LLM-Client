"""
Modelos de datos para la rama de tareas del cliente LLM de Hexylon.

Define las estructuras que representan un plan de tarea, su estado
durante la ejecución y el resultado final.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """Estado del ciclo de vida de una tarea."""
    PENDING   = "pending"    # creada, aún no iniciada
    RUNNING   = "running"    # en ejecución
    COMPLETED = "completed"  # finalizada correctamente
    FAILED    = "failed"     # finalizada con error
    CANCELLED = "cancelled"  # cancelada por el usuario


def _generate_task_id() -> str:
    """Genera un identificador único de tarea basado en timestamp."""
    return datetime.now().strftime("task_%Y%m%d_%H%M%S")


@dataclass
class TaskPlan:
    """
    Plan de ejecución de una tarea de medición.

    Generado por task_planner.py a partir de lenguaje natural del usuario
    y consumido por task_executor.py para ejecutar la tarea.

    Attributes
    ----------
    commands:
        Lista de comandos SCPI a ejecutar en cada iteración.
        Ejemplo: ["POW?", "MER?", "CBER?"]
    interval_seconds:
        Intervalo entre iteraciones en segundos.
    duration_seconds:
        Duración total de la tarea en segundos.
    output_file:
        Ruta del fichero CSV donde se guardarán los resultados.
    task_id:
        Identificador único de la tarea. Generado automáticamente.
    description:
        Descripción legible de la tarea extraída del lenguaje natural.
    created_at:
        Timestamp de creación del plan.
    """
    commands: list[str]
    interval_seconds: float
    duration_seconds: float
    output_file: str
    task_id: str = field(default_factory=_generate_task_id)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_iterations(self) -> int:
        """Número total de iteraciones previstas."""
        if self.interval_seconds <= 0:
            return 0
        return int(self.duration_seconds / self.interval_seconds)

    def __str__(self) -> str:
        return (
            f"Tarea {self.task_id}: {self.description}\n"
            f"  Comandos:    {', '.join(self.commands)}\n"
            f"  Intervalo:   {self.interval_seconds}s\n"
            f"  Duración:    {self.duration_seconds}s\n"
            f"  Iteraciones: {self.total_iterations}\n"
            f"  Salida:      {self.output_file}"
        )


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
        Ejemplo: {"POW?": "75.5 dBuV", "MER?": "28.3 dB"}
    """
    timestamp: datetime
    iteration: int
    values: dict[str, str]


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
        Mensaje de error si la tarea falló. None en caso de éxito.
    started_at:
        Timestamp de inicio de ejecución.
    finished_at:
        Timestamp de finalización.
    """
    plan: TaskPlan
    status: TaskStatus
    measurements: list[TaskMeasurement] = field(default_factory=list)
    output_file: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

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
        if self.error:
            lines.append(f"  Error:        {self.error}")
        return "\n".join(lines)