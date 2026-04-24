from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd
import re 


NUMERIC_CANDIDATES = {
    # Medidas agregadas / pantalla
    "MEAS",

    # Medidas RF principales
    "POW",
    "CN",
    "VA",
    "MER",

    # BER / calidad
    "CBER",
    "VBER",
    "BCHBER",
    "PREBER",
    "POSTBER",
    "PRELDPCBER",
    "PREBCHBER",
    "MSCBER",
    "FICBER",

    # BER por capas
    "CBERA",
    "VBERA",
    "CBERB",
    "VBERB",
    "CBERC",
    "VBERC",

    # Métricas adicionales
    "LKM",
    "PER",
    "SER",
    "HUM",
    "CSO",
    "CNBOOT",

    # Óptica
    "OPT_POW",
    "OPT_POW_1310",
    "OPT_POW_1490",
    "OPT_POW_1550",

    # Ecos: representable solo si tu parser extrae valores numéricos
    "ECHOES",

    # Parámetros de espectro potencialmente numéricos
    "RBW",
    "VBW",
    "SPAN",
    "RLEVEL",

    # Otros valores configurables potencialmente numéricos
    "FREQ",
    "LAMBDA",
    "EXTAMP",
    "VDC",
}


def _normalize_metric_name(name: str) -> str:
    return (
        name.upper()
        .replace("?", "")
        .replace(" ", "")
        .replace("/", "")
        .strip()
    )

def _to_numeric_series(series: pd.Series) -> pd.Series:
    """
    Convierte una serie con valores tipo:
    - 57.8 dBµV
    - 57,8 dBµV
    - <1.0E-6
    - NVAL
    - - - -
    a valores numéricos cuando sea posible.
    """
    def parse_value(value: object) -> float | None:
        if value is None:
            return None

        text = str(value).strip()

        if not text or text.upper() in {"NVAL", "NONE", "NULL", "- - -", "---"}:
            return None

        text = text.replace(",", ".")

        if text.startswith("<"):
            text = text[1:].strip()

        match = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text)
        if not match:
            return None

        try:
            return float(match.group(0))
        except ValueError:
            return None

    return series.map(parse_value)

def _find_metric_column(
    df: pd.DataFrame,
    requested_metric: str | None = None,
) -> str | None:
    if requested_metric:
        requested = _normalize_metric_name(requested_metric)

        for col in df.columns:
            if _normalize_metric_name(col) == requested:
                return col

    for col in df.columns:
        if _normalize_metric_name(col) in NUMERIC_CANDIDATES:
            return col

    return None


def generate_task_plot(
    csv_path: str,
    requested_metric: str | None = None,
) -> str:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el CSV: {csv_path}")

    df = pd.read_csv(path)

    metric_col = _find_metric_column(df, requested_metric=requested_metric)
    if metric_col is None:
        raise ValueError("No se encontró ninguna columna métrica representable.")

    if "timestamp" in df.columns:
        x = pd.to_datetime(df["timestamp"], errors="coerce")
        x_label = "Tiempo"
    elif "iteration" in df.columns:
        x = df["iteration"]
        x_label = "Iteración"
    else:
        x = range(1, len(df) + 1)
        x_label = "Muestra"

    y = _to_numeric_series(df[metric_col])    
    valid = y.notna()

    if valid.sum() == 0:
        raise ValueError(f"La métrica {metric_col} no contiene valores numéricos válidos.")

    output_dir = path.parent / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{path.stem}_{metric_col.lower()}.png"

    fig = plt.figure(figsize=(10, 4.5))
    ax = fig.add_subplot(111)

    ax.plot(x[valid], y[valid], linewidth=1.8)
    ax.set_title(f"Evolución de {metric_col}")
    ax.set_xlabel(x_label)
    ax.set_ylabel(metric_col)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_file, dpi=150)
    plt.close(fig)

    return str(output_file)