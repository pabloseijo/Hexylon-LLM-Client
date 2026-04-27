from __future__ import annotations

import re
from dataclasses import dataclass


PLOT_MARKERS = (
    "grafica",
    "gráfica",
    "graficar",
    "grafícame",
    "graficame",
    "hacerme la grafica",
    "hacerme la gráfica",
    "hazme la grafica",
    "hazme la gráfica",
    "plot",
    "curva",
    "evolución",
    "evolucion",
    "muéstrame la gráfica",
    "muestrame la grafica",
    "enséñame la gráfica",
    "enseñame la grafica",
)


METRICS = (
    "pow",
    "mer",
    "cn",
    "cber",
    "vber",
    "preber",
    "postber",
    "preldpcber",
    "prebchber",
    "lkm",
    "per",
    "ser",
)


@dataclass(frozen=True)
class PlotRequest:
    task_id: str | None
    metric: str | None
    explicit_task_reference: bool


def detect_plot_intent(user_input: str) -> bool:
    text = user_input.lower()
    return any(marker in text for marker in PLOT_MARKERS)


def contains_task_reference(user_input: str) -> bool:
    text = user_input.lower()

    if "task_" in text:
        return True

    if "tarea" in text:
        return True

    if re.search(r"\b20\d{6,8}_\d{6}\b", text):
        return True

    if re.search(r"\b20\d{10,14}\b", text):
        return True

    return False


def normalize_task_reference(raw: str) -> str:
    raw = raw.strip()

    if raw.startswith("task_"):
        return raw

    if re.fullmatch(r"20\d{6,8}_\d{6}", raw):
        return f"task_{raw}"

    return raw


def extract_task_reference(user_input: str) -> str | None:
    text = user_input.lower()

    match = re.search(r"\btask_(20\d{6,8}_\d{6})\b", text)
    if match:
        return f"task_{match.group(1)}"

    match = re.search(r"\b(20\d{6,8}_\d{6})\b", text)
    if match:
        return f"task_{match.group(1)}"

    return None


def extract_metric(user_input: str) -> str | None:
    text = user_input.lower()

    for metric in METRICS:
        if re.search(rf"\b{metric}\b", text):
            return metric.upper()

    return None


def parse_plot_request(user_input: str) -> PlotRequest | None:
    if not detect_plot_intent(user_input):
        return None

    task_id = extract_task_reference(user_input)
    metric = extract_metric(user_input)

    return PlotRequest(
        task_id=task_id,
        metric=metric,
        explicit_task_reference=task_id is not None,
    )