from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use("Agg")

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

def _is_matrix_sweep_csv(df: pd.DataFrame) -> bool:
    return (
        "generator_power_dbm" in df.columns
        and "generator_frequency_mhz" in df.columns
    )

def _find_matrix_metric_column(
    df: pd.DataFrame,
    requested_metric: str | None = None,
) -> str | None:
    if requested_metric:
        requested = _normalize_metric_name(requested_metric)

        for col in df.columns:
            normalized = _normalize_metric_name(col)

            # Permite pedir "POW" y encontrar "hexylon_a_POW?"
            if normalized.endswith(requested):
                return col

    for col in df.columns:
        normalized = _normalize_metric_name(col)

        for candidate in NUMERIC_CANDIDATES:
            if normalized.endswith(candidate):
                return col

    return None

def _generate_matrix_sweep_plot(
    df: pd.DataFrame,
    path: Path,
    requested_metric: str | None = None,
) -> str:
    metric_col = _find_matrix_metric_column(df, requested_metric=requested_metric)

    if metric_col is None:
        raise ValueError("No se encontró ninguna columna métrica representable para el barrido matricial.")

    df = df.copy()
    df["generator_power_dbm"] = pd.to_numeric(df["generator_power_dbm"], errors="coerce")
    df["generator_frequency_mhz"] = pd.to_numeric(df["generator_frequency_mhz"], errors="coerce")
    df["_metric_value"] = _to_numeric_series(df[metric_col])

    df = df.dropna(
        subset=[
            "generator_power_dbm",
            "generator_frequency_mhz",
            "_metric_value",
        ]
    )

    if df.empty:
        raise ValueError(f"La métrica {metric_col} no contiene valores numéricos válidos.")

    output_dir = path.parent / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_metric = _normalize_metric_name(metric_col).lower()
    output_file = output_dir / f"{path.stem}_matrix_{safe_metric}.png"

    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(111)

    for freq_mhz, group in df.groupby("generator_frequency_mhz"):
        group = group.sort_values("generator_power_dbm")

        ax.plot(
            group["generator_power_dbm"],
            group["_metric_value"],
            marker="o",
            linewidth=1.6,
            label=f"{freq_mhz:.0f} MHz",
        )

    ax.set_title(f"{metric_col} en función de la potencia del generador")
    ax.set_xlabel("Potencia del generador (dBm)")
    ax.set_ylabel(metric_col)
    ax.grid(True, alpha=0.3)
    ax.legend(title="Frecuencia", fontsize=8)

    fig.tight_layout()
    fig.savefig(output_file, dpi=150)
    plt.close(fig)

    return str(output_file)

def _find_matrix_metric_columns_by_hexylon(
    df: pd.DataFrame,
    requested_metric: str | None = None,
) -> dict[str, str]:
    result: dict[str, str] = {}

    priority = ["POW", "MER", "CN", "CBER", "VBER", "LOCK", "FREQ"]

    requested = (
        _normalize_metric_name(requested_metric)
        if requested_metric
        else None
    )

    machine_columns: dict[str, list[tuple[str, str]]] = {}

    for col in df.columns:
        if not col.startswith("hexylon_"):
            continue

        parts = col.split("_", 2)
        if len(parts) != 3:
            continue

        machine_id = f"{parts[0]}_{parts[1]}"
        metric_name = parts[2]
        normalized_metric = _normalize_metric_name(metric_name)

        machine_columns.setdefault(machine_id, []).append(
            (col, normalized_metric)
        )

    for machine_id, cols in machine_columns.items():
        if requested:
            for col, metric in cols:
                if metric == requested:
                    result[machine_id] = col
                    break
        else:
            for wanted in priority:
                for col, metric in cols:
                    if metric == wanted:
                        result[machine_id] = col
                        break
                if machine_id in result:
                    break

    return result

def _generate_matrix_sweep_plots_by_hexylon(
    df: pd.DataFrame,
    path: Path,
    requested_metric: str | None = None,
) -> list[str]:
    metric_by_hexylon = _find_matrix_metric_columns_by_hexylon(
        df,
        requested_metric=requested_metric,
    )

    if not metric_by_hexylon:
        raise ValueError(
            "No se encontraron columnas métricas representables por Hexylon."
        )

    df = df.copy()
    df["generator_power_dbm"] = pd.to_numeric(
        df["generator_power_dbm"],
        errors="coerce",
    )
    df["generator_frequency_mhz"] = pd.to_numeric(
        df["generator_frequency_mhz"],
        errors="coerce",
    )

    output_dir = path.parent / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_files: list[str] = []

    for machine_id, metric_col in metric_by_hexylon.items():
        local = df.copy()
        local["_metric_value"] = _to_numeric_series(local[metric_col])

        local = local.dropna(
            subset=[
                "generator_power_dbm",
                "generator_frequency_mhz",
                "_metric_value",
            ]
        )

        if local.empty:
            continue

        safe_metric = _normalize_metric_name(metric_col).lower()
        output_file = output_dir / f"{path.stem}_{machine_id}_{safe_metric}.png"

        fig = plt.figure(figsize=(10, 5))
        ax = fig.add_subplot(111)

        for freq_mhz, group in local.groupby("generator_frequency_mhz"):
            group = group.sort_values("generator_power_dbm")

            ax.plot(
                group["generator_power_dbm"],
                group["_metric_value"],
                marker="o",
                linewidth=1.6,
                label=f"{freq_mhz:.0f} MHz",
            )

        ax.set_title(
            f"{machine_id} — {metric_col} en función de la potencia del generador"
        )
        ax.set_xlabel("Potencia del generador (dBm)")
        ax.set_ylabel(metric_col)
        ax.grid(True, alpha=0.3)
        ax.legend(title="Frecuencia", fontsize=8)

        fig.tight_layout()
        fig.savefig(output_file, dpi=150)
        plt.close(fig)

        output_files.append(str(output_file))

    if not output_files:
        raise ValueError(
            "No se pudo generar ninguna gráfica matricial con datos válidos."
        )

    return output_files

def generate_task_plot(
    csv_path: str,
    requested_metric: str | None = None,
) -> str:
    plots = generate_task_plots(
        csv_path=csv_path,
        requested_metric=requested_metric,
    )

    if not plots:
        raise ValueError("No se ha generado ninguna gráfica.")

    return plots[0]

def generate_task_plots(
    csv_path: str,
    requested_metric: str | None = None,
) -> list[str]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el CSV: {csv_path}")

    df = pd.read_csv(path)

    if _is_matrix_sweep_csv(df):
        return _generate_matrix_sweep_plots_by_hexylon(
            df=df,
            path=path,
            requested_metric=requested_metric,
        )

    return [
        generate_task_plot(
            csv_path=csv_path,
            requested_metric=requested_metric,
        )
    ]