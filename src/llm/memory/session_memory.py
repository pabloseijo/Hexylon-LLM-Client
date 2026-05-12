"""
Estado de sesión para el cliente LLM de Hexylon.
Mantiene memoria operativa del chat actual en memoria de proceso.
No persiste entre reinicios. Su objetivo es resolver referencias
conversacionales al contexto reciente.
"""
from __future__ import annotations
from dataclasses import dataclass
from threading import Lock


@dataclass
class SessionState:
    """
    Estado de sesión del chat actual.

    Attributes
    ----------
    last_task_id:
        ID de la última tarea lanzada en esta sesión.
    last_completed_task_id:
        ID de la última tarea que terminó correctamente o fue cancelada.
    last_output_file:
        Ruta del último CSV generado por una tarea finalizada.
    last_metric:
        Última métrica relevante mencionada o usada en contexto.
    last_machine_id:
        Última máquina usada — permite resolver "vuelve a medir" sin especificar equipo.
    """
    last_task_id: str | None = None
    last_completed_task_id: str | None = None
    last_output_file: str | None = None
    last_metric: str | None = None
    last_machine_id: str | None = None  # ← NUEVO

    def clear(self) -> None:
        """Reinicia el estado de sesión."""
        self.last_task_id = None
        self.last_completed_task_id = None
        self.last_output_file = None
        self.last_metric = None
        self.last_machine_id = None  # ← NUEVO


class SessionMemory:
    """
    Envoltorio thread-safe sobre SessionState.
    Permite actualizar el estado desde el hilo principal y desde callbacks
    de tareas asíncronas de forma segura.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._state = SessionState()

    def get_state(self) -> SessionState:
        """Devuelve una copia del estado actual."""
        with self._lock:
            return SessionState(
                last_task_id=self._state.last_task_id,
                last_completed_task_id=self._state.last_completed_task_id,
                last_output_file=self._state.last_output_file,
                last_metric=self._state.last_metric,
                last_machine_id=self._state.last_machine_id,  # ← NUEVO
            )

    def set_last_task_id(self, task_id: str | None) -> None:
        with self._lock:
            self._state.last_task_id = task_id

    def set_last_completed_task(
        self,
        task_id: str | None,
        output_file: str | None,
    ) -> None:
        with self._lock:
            self._state.last_completed_task_id = task_id
            self._state.last_output_file = output_file

    def set_last_metric(self, metric: str | None) -> None:
        with self._lock:
            self._state.last_metric = metric

    def set_last_machine_id(self, machine_id: str | None) -> None:  # ← NUEVO
        with self._lock:
            self._state.last_machine_id = machine_id

    def clear_last_task_if_matches(self, task_id: str) -> None:
        with self._lock:
            if self._state.last_task_id == task_id:
                self._state.last_task_id = None

    def clear(self) -> None:
        with self._lock:
            self._state.clear()


session_memory = SessionMemory()