"""
Memoria conversacional estructurada para el cliente LLM de Hexylon.

Mantiene un historial de eventos de la sesión actual en RAM y un resumen
incremental que puede inyectarse al LLM para responder preguntas como:
- "qué estamos haciendo"
- "qué hicimos antes"
- "en qué fase estamos"

No persiste entre reinicios. Para persistencia usar task_history.py (nivel 3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any


class EventType(Enum):
    TASK_LAUNCHED    = "TASK_LAUNCHED"
    TASK_COMPLETED   = "TASK_COMPLETED"
    TASK_CANCELLED   = "TASK_CANCELLED"
    TASK_FAILED      = "TASK_FAILED"
    COMMAND_SENT     = "COMMAND_SENT"
    KNOWLEDGE_QUERY  = "KNOWLEDGE_QUERY"
    SESSION_QUESTION = "SESSION_QUESTION"


@dataclass
class SessionEvent:
    """
    Un evento ocurrido durante la sesión.

    Attributes
    ----------
    event_type:
        Tipo de evento.
    description:
        Descripción legible del evento.
    timestamp:
        Momento en que ocurrió.
    data:
        Datos estructurados adicionales del evento.
    """
    event_type: EventType
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict[str, Any] = field(default_factory=dict)

    def to_summary_line(self) -> str:
        """Representación compacta para incluir en resúmenes."""
        ts = self.timestamp.strftime("%H:%M:%S")
        return f"[{ts}] {self.event_type.value}: {self.description}"


class SessionLog:
    """
    Registro conversacional de la sesión actual.

    Mantiene:
    - historial de eventos (máximo MAX_EVENTS para no crecer infinitamente)
    - resumen incremental de la sesión

    Thread-safe mediante Lock.
    """

    MAX_EVENTS = 50

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: list[SessionEvent] = []
        self._session_start = datetime.now()

    # ------------------------------------------------------------------
    # Registro de eventos
    # ------------------------------------------------------------------

    def log(
        self,
        event_type: EventType,
        description: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Registra un nuevo evento en el log."""
        event = SessionEvent(
            event_type=event_type,
            description=description,
            data=data or {},
        )
        with self._lock:
            self._events.append(event)
            # Mantener solo los últimos MAX_EVENTS
            if len(self._events) > self.MAX_EVENTS:
                self._events = self._events[-self.MAX_EVENTS:]

    def log_task_launched(self, task_id: str, description: str, commands: list[str]) -> None:
        self.log(
            EventType.TASK_LAUNCHED,
            f"Lanzada tarea '{description}' con comandos {', '.join(commands)}",
            data={"task_id": task_id, "commands": commands, "description": description},
        )

    def log_task_completed(self, task_id: str, description: str, output_file: str, measurements: int) -> None:
        self.log(
            EventType.TASK_COMPLETED,
            f"Completada tarea '{description}' — {measurements} mediciones en {output_file}",
            data={"task_id": task_id, "output_file": output_file, "measurements": measurements},
        )

    def log_task_cancelled(self, task_id: str) -> None:
        self.log(
            EventType.TASK_CANCELLED,
            f"Cancelada tarea {task_id}",
            data={"task_id": task_id},
        )

    def log_task_failed(self, task_id: str, error: str) -> None:
        self.log(
            EventType.TASK_FAILED,
            f"Fallida tarea {task_id}: {error}",
            data={"task_id": task_id, "error": error},
        )

    def log_command_sent(self, scpi_command: str, user_input: str) -> None:
        self.log(
            EventType.COMMAND_SENT,
            f"Ejecutado comando {scpi_command}",
            data={"command": scpi_command, "user_input": user_input},
        )

    def log_knowledge_query(self, user_input: str, query_type: str) -> None:
        self.log(
            EventType.KNOWLEDGE_QUERY,
            f"Consulta documental ({query_type}): {user_input[:60]}",
            data={"user_input": user_input, "query_type": query_type},
        )

    # ------------------------------------------------------------------
    # Consulta del log
    # ------------------------------------------------------------------

    def get_recent_events(self, n: int = 10) -> list[SessionEvent]:
        """Devuelve los N eventos más recientes."""
        with self._lock:
            return list(self._events[-n:])

    def get_events_by_type(self, event_type: EventType) -> list[SessionEvent]:
        """Devuelve todos los eventos de un tipo concreto."""
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def get_last_event_of_type(self, event_type: EventType) -> SessionEvent | None:
        """Devuelve el evento más reciente de un tipo concreto."""
        with self._lock:
            for event in reversed(self._events):
                if event.event_type == event_type:
                    return event
        return None

    # ------------------------------------------------------------------
    # Resumen de sesión para inyectar al LLM
    # ------------------------------------------------------------------

    def build_session_summary(self) -> str:
        """
        Construye un resumen estructurado de la sesión actual.

        Este texto puede inyectarse al LLM para responder preguntas como
        "qué estamos haciendo" o "en qué punto estamos".
        """
        with self._lock:
            events = list(self._events)

        if not events:
            return "La sesión acaba de empezar. No se ha realizado ninguna acción todavía."

        start_str = self._session_start.strftime("%H:%M:%S")
        lines = [f"Resumen de la sesión (iniciada a las {start_str}):"]

        # Contar por tipo
        counts: dict[str, int] = {}
        for event in events:
            key = event.event_type.value
            counts[key] = counts.get(key, 0) + 1

        if counts:
            lines.append("\nAcciones realizadas:")
            type_labels = {
                "TASK_LAUNCHED":    "Tareas lanzadas",
                "TASK_COMPLETED":   "Tareas completadas",
                "TASK_CANCELLED":   "Tareas canceladas",
                "TASK_FAILED":      "Tareas fallidas",
                "COMMAND_SENT":     "Comandos ejecutados",
                "KNOWLEDGE_QUERY":  "Consultas documentales",
                "SESSION_QUESTION": "Preguntas sobre la sesión",
            }
            for key, count in counts.items():
                label = type_labels.get(key, key)
                lines.append(f"  - {label}: {count}")

        # Últimos 5 eventos
        recent = events[-5:]
        lines.append("\nÚltimas acciones:")
        for event in recent:
            lines.append(f"  {event.to_summary_line()}")

        # Estado actual de tareas
        launched = [e for e in events if e.event_type == EventType.TASK_LAUNCHED]
        completed_ids = {
            e.data.get("task_id")
            for e in events
            if e.event_type in (EventType.TASK_COMPLETED, EventType.TASK_CANCELLED, EventType.TASK_FAILED)
        }
        active_tasks = [
            e for e in launched
            if e.data.get("task_id") not in completed_ids
        ]

        if active_tasks:
            lines.append("\nTareas activas ahora mismo:")
            for e in active_tasks:
                lines.append(f"  - {e.data.get('description', e.data.get('task_id'))}")
        else:
            last_completed = None
            for e in reversed(events):
                if e.event_type == EventType.TASK_COMPLETED:
                    last_completed = e
                    break
            if last_completed:
                lines.append(
                    f"\nÚltima tarea completada: {last_completed.data.get('description', '')} "
                    f"— CSV: {last_completed.data.get('output_file', '')}"
                )

        return "\n".join(lines)

    def clear(self) -> None:
        """Limpia el log de sesión."""
        with self._lock:
            self._events.clear()
            self._session_start = datetime.now()


# Instancia global
session_log = SessionLog()