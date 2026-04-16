"""
Escritor incremental de mediciones al CSV para la rama tasks de Hexylon.

Escribe cada medición en el fichero en el momento en que se captura,
sin acumular en memoria. Esto garantiza que los datos no se pierden
aunque la tarea sea cancelada o falle a mitad de ejecución.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from llm.tasks.task_models import TaskMeasurement


class CsvWriter:
    """
    Escritor incremental de mediciones al CSV.

    Abre el fichero en modo append para que las mediciones se persistan
    inmediatamente. Si el fichero no existe lo crea con cabecera.

    Parameters
    ----------
    filepath:
        Ruta completa del fichero CSV de salida.
    commands:
        Lista de comandos SCPI cuyos valores se escribirán como columnas.
    """

    def __init__(self, filepath: str, commands: list[str]) -> None:
        self.filepath = filepath
        self.commands = commands
        self._file = None
        self._writer = None

    def open(self) -> None:
        """Abre el fichero CSV y escribe la cabecera si es nuevo."""
        Path(self.filepath).parent.mkdir(parents=True, exist_ok=True)

        file_exists = os.path.isfile(self.filepath)
        self._file = open(self.filepath, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)

        if not file_exists:
            self._write_header()

    def _write_header(self) -> None:
        """Escribe la fila de cabecera."""
        header = ["timestamp", "iteration"] + self.commands
        self._writer.writerow(header)
        self._file.flush()

    def write_row(self, measurement: TaskMeasurement) -> None:
        """
        Escribe una fila de medición en el CSV.

        Parameters
        ----------
        measurement:
            La medición a escribir.
        """
        if self._writer is None:
            raise RuntimeError(
                "CsvWriter no está abierto. Llama a open() primero."
            )

        timestamp_str = measurement.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        row = [timestamp_str, measurement.iteration]
        row += [measurement.values.get(cmd, "") for cmd in self.commands]

        self._writer.writerow(row)
        self._file.flush()  # persistencia inmediata

    def close(self) -> None:
        """Cierra el fichero CSV."""
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None