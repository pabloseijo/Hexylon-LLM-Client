"""
Analizador post-tarea para el cliente LLM de Hexylon.

Lee el CSV generado por una tarea finalizada, extrae valores numéricos
de los formatos heterogéneos del Hexylon y calcula métricas resumen.

Formatos de valor soportados:
- Numérico con unidad:  "75.5 dBuV", "28.3 dB", "-45.2 dBm"
- Notación científica:  "1.0E-6", "<1.0E-8"
- Booleano:             "TRUE", "FALSE"
- No disponible:        "NVAL", "N/A", ""
- Error:                "ERROR: ..."
- Parámetros:           "Standard ATSC3 | BW 6.0 MHz | ..."
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Modelos de datos
# ---------------------------------------------------------------------------

@dataclass
class CommandStats:
    """
    Estadísticas de un comando SCPI a lo largo de una tarea.

    Attributes
    ----------
    command:
        Nombre del comando SCPI (p. ej. "POW?").
    unit:
        Unidad detectada en los valores (p. ej. "dBuV"). None si no aplica.
    values:
        Valores numéricos extraídos. Lista vacía si ningún valor era parseable.
    raw_values:
        Todos los valores raw del CSV (incluyendo NVAL, ERROR, etc.).
    min_val / max_val / mean_val:
        Estadísticas calculadas sobre values. None si no hay valores numéricos.
    last_val:
        Último valor numérico registrado. None si no hay valores numéricos.
    last_raw:
        Último valor raw registrado (puede ser NVAL o ERROR).
    trend:
        Tendencia detectada: "subiendo", "bajando", "estable", "sin_datos".
    unavailable_count:
        Número de muestras con NVAL o vacías.
    error_count:
        Número de muestras con ERROR.
    """
    command: str
    unit: str | None = None
    values: list[float] = field(default_factory=list)
    raw_values: list[str] = field(default_factory=list)
    min_val: float | None = None
    max_val: float | None = None
    mean_val: float | None = None
    last_val: float | None = None
    last_raw: str | None = None
    trend: str = "sin_datos"
    unavailable_count: int = 0
    error_count: int = 0


@dataclass
class TaskAnalysis:
    """
    Resultado completo del análisis de una tarea finalizada.

    Attributes
    ----------
    task_id:
        ID de la tarea analizada.
    csv_path:
        Ruta del CSV analizado.
    total_rows:
        Número total de filas de datos leídas.
    commands:
        Lista de comandos presentes en el CSV.
    stats:
        Estadísticas por comando.
    duration_seconds:
        Duración real estimada de la tarea (diferencia entre primera y última fila).
    summary_text:
        Resumen textual estructurado listo para inyectar al LLM.
    """
    task_id: str
    csv_path: str
    total_rows: int
    commands: list[str]
    stats: dict[str, CommandStats]
    duration_seconds: float | None = None
    summary_text: str = ""


# ---------------------------------------------------------------------------
# Parseo de valores
# ---------------------------------------------------------------------------

# Regex para extraer número y unidad de valores como "75.5 dBuV", "-3.2 dB"
_NUMERIC_WITH_UNIT = re.compile(
    r"^[<>]?\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Zµ%/]+.*)?$"
)

# Prefijos que indican valor no disponible
_UNAVAILABLE = {"nval", "n/a", "", "none", "-"}

# Prefijos que indican error
_ERROR_PREFIX = "error"


def _parse_numeric(raw: str) -> tuple[float | None, str | None]:
    """
    Intenta extraer un valor numérico y su unidad de un string raw.

    Returns
    -------
    (value, unit) si se pudo parsear, (None, None) en caso contrario.
    """
    if not raw:
        return None, None

    cleaned = raw.strip()

    # Valores no disponibles
    if cleaned.lower() in _UNAVAILABLE:
        return None, None

    # Errores
    if cleaned.lower().startswith(_ERROR_PREFIX):
        return None, None

    # Booleanos
    if cleaned.upper() == "TRUE":
        return 1.0, None
    if cleaned.upper() == "FALSE":
        return 0.0, None

    # Numérico con o sin unidad
    match = _NUMERIC_WITH_UNIT.match(cleaned)
    if match:
        try:
            value = float(match.group(1))
            unit = match.group(2).strip() if match.group(2) else None
            return value, unit
        except ValueError:
            pass

    return None, None


def _detect_trend(values: list[float]) -> str:
    """
    Detecta la tendencia usando regresión lineal simple.
    Más robusto que comparar medias para señales con ruido.
    """
    if len(values) < 4:
        return "estable"

    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return "estable"

    slope = numerator / denominator
    value_range = max(values) - min(values)

    if value_range == 0:
        return "estable"

    normalized_slope = abs(slope) / value_range
    if normalized_slope < 0.01:
        return "estable"

    return "subiendo" if slope > 0 else "bajando"

# ---------------------------------------------------------------------------
# Análisis principal
# ---------------------------------------------------------------------------

def analyze_csv(csv_path: str, task_id: str = "") -> TaskAnalysis:
    """
    Lee un CSV de tarea y calcula estadísticas por comando.

    Parameters
    ----------
    csv_path:
        Ruta completa al fichero CSV generado por task_executor.
    task_id:
        ID de la tarea. Se infiere del nombre del fichero si no se proporciona.

    Returns
    -------
    TaskAnalysis
        Análisis completo con estadísticas y resumen textual.

    Raises
    ------
    FileNotFoundError
        Si el fichero CSV no existe.
    ValueError
        Si el CSV está vacío o malformado.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV no encontrado: {csv_path}")

    if not task_id:
        task_id = path.stem

    rows: list[dict[str, str]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV vacío o sin cabecera: {csv_path}")
        for row in reader:
            rows.append(dict(row))

    if not rows:
        raise ValueError(f"CSV sin filas de datos: {csv_path}")

    # Detectar columnas de comandos (todo excepto timestamp e iteration)
    all_columns = list(rows[0].keys())
    command_columns = [
        col for col in all_columns
        if col not in ("timestamp", "iteration")
    ]

    # Calcular estadísticas por comando
    stats: dict[str, CommandStats] = {}
    from collections import Counter

    for cmd in command_columns:
        stat = CommandStats(command=cmd)
        unit_counter: Counter = Counter()

        for row in rows:
            raw = row.get(cmd, "").strip()
            stat.raw_values.append(raw)

            if raw.lower() in _UNAVAILABLE:
                stat.unavailable_count += 1
                continue
            if raw.lower().startswith(_ERROR_PREFIX):
                stat.error_count += 1
                continue

            value, unit = _parse_numeric(raw)
            if value is not None:
                stat.values.append(value)
                if unit:
                    unit_counter[unit] += 1

        stat.unit = unit_counter.most_common(1)[0][0] if unit_counter else None

        if stat.values:
            stat.min_val = min(stat.values)
            stat.max_val = max(stat.values)
            stat.mean_val = sum(stat.values) / len(stat.values)
            stat.last_val = stat.values[-1]
            stat.trend = _detect_trend(stat.values)

        if stat.raw_values:
            stat.last_raw = stat.raw_values[-1]

        stats[cmd] = stat

    # Duración real estimada
    duration_seconds: float | None = None
    try:
        from datetime import datetime
        first_ts = rows[0].get("timestamp", "")
        last_ts = rows[-1].get("timestamp", "")
        if first_ts and last_ts:
            fmt = "%Y-%m-%d %H:%M:%S.%f"
            t0 = datetime.strptime(first_ts, fmt)
            t1 = datetime.strptime(last_ts, fmt)
            duration_seconds = (t1 - t0).total_seconds()
    except Exception:
        pass

    analysis = TaskAnalysis(
        task_id=task_id,
        csv_path=csv_path,
        total_rows=len(rows),
        commands=command_columns,
        stats=stats,
        duration_seconds=duration_seconds,
    )
    analysis.summary_text = _build_summary(analysis)
    return analysis


# ---------------------------------------------------------------------------
# Construcción del resumen textual
# ---------------------------------------------------------------------------

def _fmt(value: float | None, unit: str | None) -> str:
    """Formatea un valor numérico con su unidad."""
    if value is None:
        return "N/A"
    unit_str = f" {unit}" if unit else ""
    return f"{value:.4g}{unit_str}"


def _build_summary(analysis: TaskAnalysis) -> str:
    """
    Construye un resumen textual estructurado del análisis.

    Este texto se inyecta al LLM para generar respuestas conversacionales.
    """
    lines = [
        f"Análisis de tarea: {analysis.task_id}",
        f"Fichero CSV: {analysis.csv_path}",
        f"Muestras totales: {analysis.total_rows}",
    ]

    if analysis.duration_seconds is not None:
        lines.append(f"Duración real: {analysis.duration_seconds:.1f}s")

    lines.append(f"Comandos medidos: {', '.join(analysis.commands)}")
    lines.append("")

    for cmd, stat in analysis.stats.items():
        lines.append(f"--- {cmd} ---")

        if not stat.values:
            if stat.unavailable_count == len(stat.raw_values):
                lines.append("  Todos los valores no disponibles (NVAL).")
            elif stat.error_count > 0:
                lines.append(f"  {stat.error_count} errores de lectura.")
            else:
                lines.append("  Sin valores numéricos parseables.")
            if stat.last_raw:
                lines.append(f"  Último valor raw: {stat.last_raw}")
            lines.append("")
            continue

        u = stat.unit
        lines.append(f"  Muestras numéricas: {len(stat.values)} / {analysis.total_rows}")
        lines.append(f"  Mínimo:  {_fmt(stat.min_val, u)}")
        lines.append(f"  Máximo:  {_fmt(stat.max_val, u)}")
        lines.append(f"  Media:   {_fmt(stat.mean_val, u)}")
        lines.append(f"  Última:  {_fmt(stat.last_val, u)}")
        lines.append(f"  Tendencia: {stat.trend}")

        if stat.unavailable_count > 0:
            lines.append(f"  NVAL/vacíos: {stat.unavailable_count}")
        if stat.error_count > 0:
            lines.append(f"  Errores: {stat.error_count}")

        lines.append("")

    return "\n".join(lines)