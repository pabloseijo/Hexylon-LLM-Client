"""
Historial persistente de tareas para el cliente LLM de Hexylon.

Guarda en disco el registro de todas las tareas ejecutadas entre sesiones.
Usa formato JSONL (una línea JSON por tarea) para simplicidad y robustez.

Fichero: ~/.hexylon/task_history.jsonl

Cada entrada tiene dos estados:
- Al lanzar la tarea: status=running, sin finished_at ni output_file
- Al completar/cancelar/fallar: se actualiza la línea con el estado final

Como JSONL no permite actualizar líneas, se mantiene un índice en memoria
y se reescribe el fichero completo solo al cerrar sesión o cuando se
actualiza una entrada.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


def _get_history_path() -> Path:
    """
    Devuelve la ruta al fichero de historial.
    Usa HEXYLON_HISTORY_PATH si está definida, o ~/.hexylon/task_history.jsonl.
    """
    env_path = os.getenv("HEXYLON_HISTORY_PATH")
    if env_path:
        return Path(env_path)
    history_dir = Path.home() / ".hexylon"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / "task_history.jsonl"


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class TaskHistory:
    """
    Registro persistente de tareas ejecutadas.

    Mantiene un índice en memoria (dict task_id → entry) y sincroniza
    con el fichero JSONL en disco al añadir o actualizar entradas.

    Thread-safe mediante Lock.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._path = _get_history_path()
        self._entries: dict[str, dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Carga inicial
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Carga el historial desde disco al arrancar."""
        if not self._path.exists():
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        task_id = entry.get("task_id")
                        if task_id:
                            self._entries[task_id] = entry
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Escritura en disco
    # ------------------------------------------------------------------

    def _flush(self) -> None:
        """Reescribe el fichero JSONL completo desde el índice en memoria."""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                for entry in self._entries.values():
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def record_launched(
        self,
        task_id: str,
        description: str,
        commands: list[str],
        interval_seconds: float,
        duration_seconds: float,
        output_file: str,
    ) -> None:
        """
        Registra una tarea recién lanzada.
        Estado inicial: running.
        """
        entry: dict[str, Any] = {
            "task_id": task_id,
            "description": description,
            "commands": commands,
            "interval_seconds": interval_seconds,
            "duration_seconds": duration_seconds,
            "output_file": output_file,
            "status": "running",
            "started_at": _now_str(),
            "finished_at": None,
            "measurements": None,
        }
        with self._lock:
            self._entries[task_id] = entry
            self._flush()

    def record_completed(
        self,
        task_id: str,
        output_file: str,
        measurements: int,
    ) -> None:
        """Actualiza una tarea como completada."""
        with self._lock:
            if task_id in self._entries:
                self._entries[task_id].update({
                    "status": "completed",
                    "finished_at": _now_str(),
                    "output_file": output_file,
                    "measurements": measurements,
                })
                self._flush()

    def record_cancelled(self, task_id: str, measurements: int) -> None:
        """Actualiza una tarea como cancelada."""
        with self._lock:
            if task_id in self._entries:
                self._entries[task_id].update({
                    "status": "cancelled",
                    "finished_at": _now_str(),
                    "measurements": measurements,
                })
                self._flush()

    def record_failed(self, task_id: str, error: str) -> None:
        """Actualiza una tarea como fallida."""
        with self._lock:
            if task_id in self._entries:
                self._entries[task_id].update({
                    "status": "failed",
                    "finished_at": _now_str(),
                    "error": error,
                })
                self._flush()

    def get_all(self) -> list[dict[str, Any]]:
        """Devuelve todas las entradas ordenadas por started_at descendente."""
        with self._lock:
            entries = list(self._entries.values())
        entries.sort(key=lambda e: e.get("started_at", ""), reverse=True)
        return entries

    def get_last(self, n: int = 5) -> list[dict[str, Any]]:
        """Devuelve las N tareas más recientes."""
        return self.get_all()[:n]

    def get_by_id(self, task_id: str) -> dict[str, Any] | None:
        """Devuelve una tarea por su ID."""
        with self._lock:
            return self._entries.get(task_id)

    def build_history_summary(self, n: int = 10) -> str:
        """
        Construye un resumen legible del historial reciente.
        Útil para responder preguntas como "qué tareas hemos ejecutado".
        """
        recent = self.get_last(n)
        if not recent:
            return "No hay tareas registradas en el historial."

        lines = [f"Últimas {len(recent)} tareas ejecutadas:"]
        for entry in recent:
            status_icon = {
                "completed": "✓",
                "cancelled": "✗",
                "failed": "!",
                "running": "→",
            }.get(entry.get("status", ""), "?")

            lines.append(
                f"\n  {status_icon} {entry.get('task_id', '-')}\n"
                f"    Descripción: {entry.get('description', '-')}\n"
                f"    Comandos:    {', '.join(entry.get('commands', []))}\n"
                f"    Estado:      {entry.get('status', '-')}\n"
                f"    Inicio:      {entry.get('started_at', '-')}\n"
                f"    Fin:         {entry.get('finished_at', '-') or 'en curso'}\n"
                f"    CSV:         {entry.get('output_file', '-')}"
            )
        return "\n".join(lines)


# Instancia global
task_history = TaskHistory()