from __future__ import annotations

from llm.memory.session_memory import session_memory
from llm.memory.task_history import task_history
from llm.parsing.intent_models import ParsedIntent
from llm.parsing.plot_request_parser import (
    contains_task_reference,
    detect_plot_intent,
    extract_metric,
    extract_task_reference,
)


TASK_MARKERS = (
    "cada ",
    "durante ",
    "cada minuto",
    "cada hora",
    "cada segundo",
    "mídeme durante",
    "mideme durante",
    "registra durante",
    "monitoriza durante",
    "monitorea durante",
    "mide durante",
    "mide cada",
    "registra cada",
    "monitoriza cada",
    "monitorea cada",
    "captura cada",
    "guarda cada",
    "durante las próximas",
    "durante los próximos",
    "durante las proximas",
    "durante los proximos",
)

CANCEL_MARKERS = (
    "cancela la tarea",
    "cancela tarea",
    "cancelar la tarea",
    "cancelar tarea",
    "para la tarea",
    "parar la tarea",
    "detén la tarea",
    "deten la tarea",
    "detener la tarea",
    "detén la medición",
    "deten la medicion",
    "detener la medición",
    "detener la medicion",
    "para la medición",
    "para la medicion",
    "cancela la medición",
    "cancela la medicion",
    "cancel task",
    "stop task",
    "cancela todo",
    "para todo",
)

LIST_TASKS_MARKERS = (
    "tareas activas",
    "qué tareas hay",
    "que tareas hay",
    "tareas en curso",
    "qué está midiendo",
    "que esta midiendo",
    "hay alguna tarea",
    "tareas corriendo",
    "mediciones activas",
    "mediciones en curso",
)

SESSION_QUESTION_MARKERS = (
    "qué estamos haciendo",
    "que estamos haciendo",
    "en qué punto estamos",
    "en que punto estamos",
    "qué hicimos",
    "que hicimos",
    "qué acabas de hacer",
    "que acabas de hacer",
    "resume la sesión",
    "resume la sesion",
    "resumen de la sesión",
    "resumen de la sesion",
    "qué ha pasado",
    "que ha pasado",
    "historial de tareas",
    "qué tareas hemos ejecutado",
    "que tareas hemos ejecutado",
    "qué hemos medido",
    "que hemos medido",
    "cuál es el estado",
    "cual es el estado",
    "en qué fase estamos",
    "en que fase estamos",
)

ANALYSIS_MARKERS = (
    "analiza",
    "análisis",
    "analisis",
    "resume",
    "resumen",
    "resultados",
    "medición",
    "medicion",
    "csv",
    "evolución",
    "evolucion",
    "tendencia",
    "comportamiento",
    "valores",
    "cómo salió",
    "como salio",
    "cómo fue",
    "como fue",
    "qué pasó",
    "que paso",
    "qué midió",
    "que midio",
    "degradación",
    "degradacion",
    "degradó",
    "degrado",
)


def strip_conversational_prefix(user_input: str) -> str:
    prefixes = (
        "y eso ",
        "y eso,",
        "y que ",
        "y qué ",
        "y como ",
        "y cómo ",
        "y cual ",
        "y cuál ",
        "pero ",
        "entonces ",
        "oye, ",
        "oye ",
        "bueno, ",
        "bueno ",
        "vale, ",
        "vale ",
        "y ",
    )

    text = user_input.strip()
    lower = text.lower()

    for prefix in prefixes:
        if lower.startswith(prefix):
            stripped = text[len(prefix):].strip()
            if stripped and stripped[0].islower():
                stripped = stripped[0].upper() + stripped[1:]
            return stripped

    return text


def _has_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _has_analysis_context() -> bool:
    state = session_memory.get_state()

    if state.last_output_file:
        return True

    for entry in task_history.get_last(50):
        if entry.get("status") == "completed" and entry.get("output_file"):
            return True

    return False


def parse_input(user_input: str) -> ParsedIntent:
    normalized = strip_conversational_prefix(user_input)
    text = normalized.lower()

    task_id = extract_task_reference(normalized)
    metric = extract_metric(normalized)

    if _has_marker(text, CANCEL_MARKERS):
        return ParsedIntent(
            intent="cancel_task",
            normalized_input=normalized,
            task_id=task_id,
            metric=metric,
        )

    if _has_marker(text, LIST_TASKS_MARKERS):
        return ParsedIntent(
            intent="list_tasks",
            normalized_input=normalized,
            task_id=task_id,
            metric=metric,
        )

    if _has_marker(text, SESSION_QUESTION_MARKERS):
        return ParsedIntent(
            intent="session_question",
            normalized_input=normalized,
            task_id=task_id,
            metric=metric,
        )

    if _has_marker(text, TASK_MARKERS):
        return ParsedIntent(
            intent="launch_task",
            normalized_input=normalized,
            task_id=task_id,
            metric=metric,
        )

    has_analysis_language = _has_marker(text, ANALYSIS_MARKERS)
    has_plot_language = detect_plot_intent(normalized)
    has_task_reference = contains_task_reference(normalized)
    has_context = _has_analysis_context()

    if has_plot_language and (has_task_reference or has_context):
        return ParsedIntent(
            intent="plot",
            normalized_input=normalized,
            task_id=task_id,
            metric=metric,
        )

    if has_analysis_language and (has_task_reference or has_context):
        return ParsedIntent(
            intent="analysis",
            normalized_input=normalized,
            task_id=task_id,
            metric=metric,
        )

    return ParsedIntent(
        intent="unknown",
        normalized_input=normalized,
        task_id=task_id,
        metric=metric,
    )