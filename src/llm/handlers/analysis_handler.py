from __future__ import annotations

from typing import Any

from llm.clients.ollama_client import ask_llm
from llm.memory.conversation_history import conversation_history
from llm.memory.session_memory import session_memory
from llm.memory.task_history import task_history
from llm.parsing.plot_request_parser import (
    detect_plot_intent,
    extract_metric,
    extract_task_reference,
    normalize_task_reference,
)
from llm.tasks.task_analyzer import analyze_csv
from llm.tasks.task_chart_data import build_task_chart_data
from llm.tasks.task_plotter import generate_task_plot, generate_task_plots

ANALYSIS_INTERPRETER_PROMPT = """
Eres un asistente técnico especializado en análisis de señales RF del equipo Hexylon.

Analiza los resultados de medición proporcionados y responde de forma técnica
y precisa.

Reglas obligatorias:
- Responde en markdown válido.
- Usa exactamente estas secciones:
  ## Resumen
  ## Valores clave
  ## Análisis
  ## Conclusión
- Usa listas con - dentro de las secciones.
- Usa **negrita** para métricas y valores importantes.
- No respondas en texto plano corrido.

Si una sección no aplica, indícalo dentro de ella.
""".strip()


def _safe_ask_llm(messages: list[dict[str, str]], fallback: str) -> str:
    try:
        return ask_llm(messages, num_ctx=4096).strip()
    except Exception as exc:
        print("ERROR_LLM_ANALYSIS:", repr(exc))
        return fallback


def resolve_csv_for_analysis(user_input: str) -> tuple[str | None, str | None]:
    text = user_input.lower()
    recent = task_history.get_last(50)

    referenced_task_id = extract_task_reference(user_input)
    if referenced_task_id:
        normalized_task_id = normalize_task_reference(referenced_task_id)

        for entry in recent:
            if entry.get("task_id") == normalized_task_id:
                csv_path = entry.get("output_file")
                if csv_path:
                    return csv_path, normalized_task_id

                return None, f"La tarea {normalized_task_id} no tiene CSV asociado."

        return None, f"No he encontrado la tarea {normalized_task_id} en el historial."

    for entry in recent:
        task_id = entry.get("task_id", "")
        if task_id and task_id.lower() in text:
            csv_path = entry.get("output_file")
            if csv_path:
                return csv_path, task_id

            return None, f"La tarea {task_id} no tiene CSV asociado."

    state = session_memory.get_state()
    if state.last_output_file:
        return state.last_output_file, state.last_completed_task_id or ""

    for entry in recent:
        if entry.get("status") == "completed" and entry.get("output_file"):
            return entry["output_file"], entry["task_id"]

    return None, (
        "No he encontrado ninguna medición reciente para analizar. "
        "Lanza primero una tarea de medición."
    )


def handle_analysis(user_input: str) -> dict[str, Any] | str:
    csv_path, task_id_or_error = resolve_csv_for_analysis(user_input)
    if csv_path is None:
        return task_id_or_error

    metric_filter = extract_metric(user_input)
    plot_requested = detect_plot_intent(user_input)

    plot_file: str | None = None
    plot_files: list[str] = []
    chart_data: dict[str, Any] | None = None

    try:
        analysis = analyze_csv(csv_path, task_id=task_id_or_error or "")
    except FileNotFoundError:
        return f"No he encontrado el fichero CSV en {csv_path}."
    except ValueError as exc:
        return f"No he podido leer el CSV: {exc}"

    if plot_requested:
        try:
            chart_data = build_task_chart_data(
                csv_path,
                requested_metric=metric_filter,
            )
        except Exception as exc:
            print("ERROR_CHART_DATA:", repr(exc))
            chart_data = None

        try:
            plot_files = generate_task_plots(
                csv_path,
                requested_metric=metric_filter,
            )
            plot_file = plot_files[0] if plot_files else None
        except Exception as exc:
            print("ERROR_PLOT_FILE:", repr(exc))
            plot_file = None

    messages = conversation_history.build_messages(
        system_prompt=ANALYSIS_INTERPRETER_PROMPT,
        extra_user_content=(
            f"Tarea analizada: {task_id_or_error or 'desconocida'}\n"
            f"Fichero CSV: {csv_path}\n"
            f"Análisis calculado:\n{analysis.summary_text}"
        ),
    )

    fallback = (
        "## Resumen\n\n"
        "- El CSV se ha localizado y el análisis determinista se ha calculado correctamente.\n"
        "- No se ha podido completar la interpretación mediante LLM.\n\n"
        "## Valores clave\n\n"
        f"{analysis.summary_text}\n\n"
        "## Análisis\n\n"
        "- La gráfica interactiva se adjunta debajo si los datos se han generado correctamente.\n\n"
        "## Conclusión\n\n"
        "- El sistema ha devuelto una respuesta de respaldo para evitar interrumpir el flujo."
    )

    message = _safe_ask_llm(messages, fallback=fallback)

    return {
        "message": message,
        "plot_file": plot_file,
        "chart_data": chart_data,
        "plot_files": plot_files,
    }