from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd


NUMERIC_CANDIDATES = {
    "MEAS",
    "POW",
    "CN",
    "VA",
    "MER",
    "CBER",
    "VBER",
    "BCHBER",
    "PREBER",
    "POSTBER",
    "PRELDPCBER",
    "PREBCHBER",
    "MSCBER",
    "FICBER",
    "CBERA",
    "VBERA",
    "CBERB",
    "VBERB",
    "CBERC",
    "VBERC",
    "LKM",
    "PER",
    "SER",
    "HUM",
    "CSO",
    "CNBOOT",
    "OPT_POW",
    "OPT_POW_1310",
    "OPT_POW_1490",
    "OPT_POW_1550",
    "ECHOES",
    "RBW",
    "VBW",
    "SPAN",
    "RLEVEL",
    "FREQ",
    "LAMBDA",
    "EXTAMP",
    "VDC",
}

MATRIX_METRIC_PRIORITY = (
    "POW",
    "MER",
    "CN",
    "CBER",
    "VBER",
    "LOCK",
    "FREQ",
)

UNIT_PATTERNS = (
    "dBµV",
    "dBuV",
    "dB",
    "Hz",
    "kHz",
    "MHz",
    "GHz",
    "V",
    "mV",
    "W",
    "mW",
    "%",
)


def _normalize_metric_name(name: str) -> str:
    return (
        name.upper()
        .replace("?", "")
        .replace(" ", "")
        .replace("/", "")
        .strip()
    )


def _extract_unit(value: object) -> str | None:
    text = str(value)

    for unit in UNIT_PATTERNS:
        if unit in text:
            return unit

    return None


def _parse_numeric_value(value: object) -> float | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    if text.upper() in {"NVAL", "NONE", "NULL", "- - -", "---"}:
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


def _to_numeric_series(series: pd.Series) -> pd.Series:
    return series.map(_parse_numeric_value)


def _is_matrix_sweep_csv(df: pd.DataFrame) -> bool:
    return (
        "generator_power_dbm" in df.columns
        and "generator_frequency_mhz" in df.columns
    )


def _find_metric_columns(
    df: pd.DataFrame,
    requested_metric: str | None = None,
) -> list[str]:
    if requested_metric:
        requested = _normalize_metric_name(requested_metric)
        return [
            str(col)
            for col in df.columns
            if _normalize_metric_name(str(col)) == requested
        ]

    return [
        str(col)
        for col in df.columns
        if _normalize_metric_name(str(col)) in NUMERIC_CANDIDATES
    ]


def _find_matrix_metric_columns_by_hexylon(
    df: pd.DataFrame,
    requested_metric: str | None = None,
) -> dict[str, str]:
    result: dict[str, str] = {}

    requested = (
        _normalize_metric_name(requested_metric)
        if requested_metric
        else None
    )

    machine_columns: dict[str, list[tuple[str, str]]] = {}

    for col in df.columns:
        col_str = str(col)

        if not col_str.startswith("hexylon_"):
            continue

        parts = col_str.split("_", 2)
        if len(parts) != 3:
            continue

        machine_id = f"{parts[0]}_{parts[1]}"
        metric_name = parts[2]
        normalized_metric = _normalize_metric_name(metric_name)

        machine_columns.setdefault(machine_id, []).append(
            (col_str, normalized_metric)
        )

    for machine_id, cols in machine_columns.items():
        if requested:
            for col, metric in cols:
                if metric == requested:
                    result[machine_id] = col
                    break
        else:
            for wanted in MATRIX_METRIC_PRIORITY:
                for col, metric in cols:
                    if metric == wanted:
                        result[machine_id] = col
                        break
                if machine_id in result:
                    break

    return result


def _resolve_x_values(df: pd.DataFrame) -> tuple[list[str], str]:
    if "timestamp" in df.columns:
        values = pd.to_datetime(df["timestamp"], errors="coerce")
        labels = [
            value.strftime("%H:%M:%S") if not pd.isna(value) else str(index + 1)
            for index, value in enumerate(values)
        ]
        return labels, "Tiempo"

    if "iteration" in df.columns:
        return [str(value) for value in df["iteration"].tolist()], "Iteración"

    return [str(index + 1) for index in range(len(df))], "Muestra"


def _build_matrix_chart_data(
    df: pd.DataFrame,
    path: Path,
    requested_metric: str | None = None,
) -> dict[str, Any]:
    metric_by_hexylon = _find_matrix_metric_columns_by_hexylon(
        df,
        requested_metric=requested_metric,
    )

    if not metric_by_hexylon:
        raise ValueError("No se encontró ninguna columna métrica representable.")

    df = df.copy()
    df["generator_power_dbm"] = pd.to_numeric(
        df["generator_power_dbm"],
        errors="coerce",
    )
    df["generator_frequency_mhz"] = pd.to_numeric(
        df["generator_frequency_mhz"],
        errors="coerce",
    )

    charts: list[dict[str, Any]] = []

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

        unit = None
        for raw_value in local[metric_col].tolist():
            unit = _extract_unit(raw_value)
            if unit:
                break

        series: list[dict[str, Any]] = []

        for freq_mhz, group in local.groupby("generator_frequency_mhz"):
            group = group.sort_values("generator_power_dbm")

            points = [
                {
                    "x": float(row["generator_power_dbm"]),
                    "y": float(row["_metric_value"]),
                }
                for _, row in group.iterrows()
            ]

            if points:
                series.append({
                    "label": f"{freq_mhz:.0f} MHz",
                    "points": points,
                })

        if not series:
            continue

        normalized_metric = _normalize_metric_name(metric_col)

        charts.append({
            "metric": normalized_metric,
            "metric_column": metric_col,
            "machine_id": machine_id,
            "unit": unit,
            "x_label": "Potencia del generador (dBm)",
            "y_label": f"{normalized_metric}{f' ({unit})' if unit else ''}",
            "series": series,
            "source_file": str(path.resolve()),
        })

    if not charts:
        raise ValueError("No hay valores numéricos válidos para graficar.")

    return {
        "charts": charts,
        "source_file": str(path.resolve()),
    }


def build_task_chart_data(
    csv_path: str,
    requested_metric: str | None = None,
) -> dict[str, Any]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el CSV: {csv_path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError("El CSV no contiene filas.")

    if _is_matrix_sweep_csv(df):
        return _build_matrix_chart_data(
            df=df,
            path=path,
            requested_metric=requested_metric,
        )

    metric_cols = _find_metric_columns(df, requested_metric=requested_metric)
    if not metric_cols:
        raise ValueError("No se encontró ninguna columna métrica representable.")

    x_values, x_label = _resolve_x_values(df)

    charts: list[dict[str, Any]] = []

    for metric_col in metric_cols:
        normalized_metric = _normalize_metric_name(metric_col)
        y = _to_numeric_series(df[metric_col])

        unit = None
        for raw_value in df[metric_col].tolist():
            unit = _extract_unit(raw_value)
            if unit:
                break

        points: list[dict[str, Any]] = []

        for index, value in enumerate(y.tolist()):
            if value is None or pd.isna(value):
                continue

            points.append({
                "x": x_values[index],
                "y": float(value),
            })

        if not points:
            continue

        charts.append({
            "metric": normalized_metric,
            "metric_column": metric_col,
            "unit": unit,
            "x_label": x_label,
            "y_label": f"{normalized_metric}{f' ({unit})' if unit else ''}",
            "points": points,
            "source_file": str(path.resolve()),
        })

    if not charts:
        raise ValueError("No hay valores numéricos válidos para graficar.")

    return {
        "charts": charts,
        "source_file": str(path.resolve()),
    }