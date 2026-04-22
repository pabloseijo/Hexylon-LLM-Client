import re
from typing import Any

from llm.clients.mcp_client import send_scpi_command
from llm.clients.ollama_client import ask_llm
from llm.core.intent_router import route_intent
from llm.core.scpi_generator import generate_scpi
from llm.memory.conversation_history import conversation_history
from llm.memory.session_memory import session_memory
from llm.memory.session_log import EventType, session_log
from llm.memory.task_history import task_history
from llm.tasks.task_analyzer import analyze_csv
from llm.tasks.task_executor import cancel_task, get_active_tasks, launch_task
from llm.tasks.task_models import TaskResult, TaskStatus
from llm.tasks.task_planner import try_plan_task
from llm.core.interpreter import interpret_response


# ---------------------------------------------------------------------------
# Prompts del sistema
# ---------------------------------------------------------------------------

KNOWLEDGE_SYSTEM_PROMPT = """
Eres un asistente técnico especializado en la API SCPI del equipo Hexylon.

Tu tarea es responder preguntas técnicas sobre:
- qué hace un comando
- qué devuelve
- qué sintaxis tiene
- qué restricciones tiene
- qué comandos están relacionados con una capacidad concreta
- qué opciones ofrece una determinada área funcional de la API

Reglas obligatorias:
- Responde en español.
- Responde de forma técnica, clara y precisa.
- Usa exclusivamente el contexto documental proporcionado.
- No inventes comandos, sintaxis, restricciones ni comportamientos.
- Si la documentación no es suficiente para responder con seguridad, indícalo.
- No uses markdown.
""".strip()

SESSION_INTERPRETER_PROMPT = """
Eres un asistente técnico del sistema Hexylon LLM.

Responde preguntas sobre el estado actual de la sesión de forma natural y
conversacional, como un colaborador que conoce bien lo que está pasando.
No enumeres logs ni eventos crudos. Sintetiza y explica en prosa.
No uses markdown.
""".strip()

ANALYSIS_INTERPRETER_PROMPT = """
Eres un asistente técnico especializado en análisis de señales RF del equipo Hexylon.

Analiza los resultados de medición proporcionados y responde de forma técnica
y precisa. Explica qué se midió, los valores relevantes, tendencias y anomalías.
Si el usuario pregunta por una métrica específica, céntrate en ella.
No uses markdown. Responde en prosa técnica clara.
""".strip()

COMMAND_INTERPRETER_PROMPT = """
Eres un asistente técnico del equipo Hexylon.

Tienes acceso al historial de la conversación y a la última respuesta del equipo.
Interpreta la respuesta de forma clara y natural en español.
Si la respuesta es un valor de medición, explica qué significa.
Si el usuario hace una pregunta de seguimiento sobre un valor anterior, respóndela
usando el historial sin necesidad de ejecutar otro comando.
No uses markdown. Sé conciso.
""".strip()


# ---------------------------------------------------------------------------
# Marcadores de intención
# ---------------------------------------------------------------------------

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
    "resume la última medición",
    "resume la ultima medicion",
    "analiza la última medición",
    "analiza la ultima medicion",
    "analiza los resultados",
    "resumen de la medición",
    "resumen de la medicion",
    "cómo evolucionó",
    "como evoluciono",
    "cómo fue la medición",
    "como fue la medicion",
    "qué pasó con la medición",
    "que paso con la medicion",
    "hubo degradación",
    "hubo degradacion",
    "degradó la señal",
    "degrado la senal",
    "cómo quedó la potencia",
    "como quedo la potencia",
    "cómo quedó el mer",
    "como quedo el mer",
    "resultados de la tarea",
    "resultados de la medición",
    "resultados de la medicion",
    "qué midió",
    "que midio",
    "muéstrame los resultados",
    "muestrame los resultados",
    "analiza el csv",
    "analiza los datos",
)


# ---------------------------------------------------------------------------
# Detección de intención
# ---------------------------------------------------------------------------

def detect_task_intent(user_input: str) -> bool:
    text = user_input.lower()
    return any(marker in text for marker in TASK_MARKERS)


def detect_cancel_intent(user_input: str) -> bool:
    text = user_input.lower()
    return any(marker in text for marker in CANCEL_MARKERS)


def detect_list_tasks_intent(user_input: str) -> bool:
    text = user_input.lower()
    return any(marker in text for marker in LIST_TASKS_MARKERS)


def detect_session_question_intent(user_input: str) -> bool:
    text = user_input.lower()
    return any(marker in text for marker in SESSION_QUESTION_MARKERS)


def detect_analysis_intent(user_input: str) -> bool:
    text = user_input.lower()
    return any(marker in text for marker in ANALYSIS_MARKERS)


# ---------------------------------------------------------------------------
# Normalización de prefijos conversacionales
# ---------------------------------------------------------------------------

def _strip_conversational_prefix(user_input: str) -> str:
    """
    Elimina prefijos conversacionales que rompen la detección de intención.

    Ejemplos:
    - "y eso es un valor alto?"  →  "eso es un valor alto?"
    - "y que comandos hay?"      →  "que comandos hay?"
    - "pero como funciona?"      →  "como funciona?"
    - "entonces dame la freq"    →  "dame la freq"
    """
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


# ---------------------------------------------------------------------------
# Utilidades de resolución de tareas
# ---------------------------------------------------------------------------

def _get_sorted_active_tasks() -> list[tuple[str, object]]:
    active = get_active_tasks()
    return sorted(active.items(), key=lambda item: item[0])


def _extract_explicit_task_id(
    user_input: str,
    active_task_ids: list[str],
) -> str | None:
    text = user_input.lower()
    for task_id in active_task_ids:
        if task_id.lower() in text:
            return task_id
    return None


def _extract_ordinal_index(user_input: str) -> int | None:
    text = user_input.lower().strip()
    patterns = (
        r"\btarea\s+(\d+)\b",
        r"\bla\s+tarea\s+(\d+)\b",
        r"\btask\s+(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def _resolve_task_id_for_cancel(user_input: str) -> tuple[str | None, str | None]:
    sorted_active = _get_sorted_active_tasks()
    if not sorted_active:
        return None, "No hay ninguna tarea activa en este momento."

    active_task_ids = [task_id for task_id, _ in sorted_active]
    text = user_input.lower().strip()

    explicit_task_id = _extract_explicit_task_id(user_input, active_task_ids)
    if explicit_task_id is not None:
        return explicit_task_id, None

    ordinal_index = _extract_ordinal_index(user_input)
    if ordinal_index is not None:
        if 1 <= ordinal_index <= len(sorted_active):
            return sorted_active[ordinal_index - 1][0], None
        return None, (
            f"No existe la tarea {ordinal_index}. "
            f"Actualmente hay {len(sorted_active)} tareas activas."
        )

    if any(
        m in text
        for m in (
            "cancela la tarea",
            "cancelar la tarea",
            "cancela tarea",
            "cancelar tarea",
            "para la tarea",
            "detén la tarea",
            "deten la tarea",
        )
    ):
        return sorted_active[-1][0], None

    session_state = session_memory.get_state()
    if session_state.last_task_id and session_state.last_task_id in active_task_ids:
        return session_state.last_task_id, None

    if len(sorted_active) == 1:
        return sorted_active[0][0], None

    ids = "\n".join(
        f"  {idx}. {task_id}"
        for idx, (task_id, _) in enumerate(sorted_active, start=1)
    )
    return None, (
        "No se ha podido determinar qué tarea cancelar.\n"
        "Especifica el ID real o una posición, por ejemplo:\n"
        "  - cancela la tarea 1\n"
        "  - cancela la tarea task_20260416_110556\n\n"
        f"Tareas activas:\n{ids}"
    )


def _resolve_csv_for_analysis(user_input: str) -> tuple[str | None, str | None]:
    text = user_input.lower()

    recent = task_history.get_last(20)
    for entry in recent:
        task_id = entry.get("task_id", "")
        if task_id.lower() in text:
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


# ---------------------------------------------------------------------------
# Callbacks y handlers
# ---------------------------------------------------------------------------

def _on_task_complete(result: TaskResult) -> None:
    session_memory.set_last_completed_task(
        task_id=result.plan.task_id,
        output_file=result.output_file,
    )
    session_memory.clear_last_task_if_matches(result.plan.task_id)

    # Registrar alertas disparadas
    for alert_message in result.triggered_alerts:
        session_log.log_task_alert_triggered(
            task_id=result.plan.task_id,
            alert_message=alert_message,
        )

    if result.status == TaskStatus.COMPLETED:
        if result.stop_reason:
            session_log.log_task_stop_condition_triggered(
                task_id=result.plan.task_id,
                stop_reason=result.stop_reason,
            )

        session_log.log_task_completed(
            task_id=result.plan.task_id,
            description=result.plan.description,
            output_file=result.output_file or "",
            measurements=result.total_measurements,
            stop_reason=result.stop_reason,
        )
        task_history.record_completed(
            task_id=result.plan.task_id,
            output_file=result.output_file or "",
            measurements=result.total_measurements,
            stop_reason=result.stop_reason,
        )

    elif result.status == TaskStatus.CANCELLED:
        session_log.log_task_cancelled(result.plan.task_id)
        task_history.record_cancelled(
            task_id=result.plan.task_id,
            measurements=result.total_measurements,
            stop_reason=result.stop_reason,
        )

    elif result.status == TaskStatus.FAILED:
        session_log.log_task_failed(
            task_id=result.plan.task_id,
            error=result.error or "error desconocido",
        )
        task_history.record_failed(
            task_id=result.plan.task_id,
            error=result.error or "error desconocido",
        )

    completion_notice = (
        f"[Sistema] La tarea {result.plan.task_id} ha finalizado "
        f"con estado {result.status.value}. "
        f"Mediciones: {result.total_measurements}. "
        f"CSV: {result.output_file or 'no generado'}."
    )

    if result.stop_reason:
        completion_notice += f" Motivo de parada: {result.stop_reason}."

    if result.triggered_alerts:
        alert_lines = " | ".join(
            alert.summary_line() if hasattr(alert, "summary_line") else str(alert)
            for alert in result.triggered_alerts
        )
        completion_notice += f" Alertas disparadas: {alert_lines}."

    conversation_history.add_assistant_message(completion_notice)

    print("\n")
    print("=" * 50)
    print(result.summary())
    print("=" * 50)
    print(">>> ", end="", flush=True)
    
    
def _handle_launch_task(user_input: str) -> dict[str, Any] | str:
    plan_or_error = try_plan_task(user_input)
    if isinstance(plan_or_error, str):
        return plan_or_error

    plan = plan_or_error
    launch_task(plan, on_complete=_on_task_complete)

    session_memory.set_last_task_id(plan.task_id)
    session_log.log_task_launched(
        task_id=plan.task_id,
        description=plan.description,
        commands=plan.commands,
    )
    task_history.record_launched(
        task_id=plan.task_id,
        description=plan.description,
        commands=plan.commands,
        interval_seconds=plan.interval_seconds,
        duration_seconds=plan.duration_seconds,
        output_file=plan.output_file,
    )

    lines = [
        f"Tarea lanzada: {plan.description}",
        f"  ID:          {plan.task_id}",
        f"  Comandos:    {', '.join(plan.commands)}",
        f"  Intervalo:   {plan.interval_seconds}s",
        f"  Duración:    {plan.duration_seconds}s ({int(plan.duration_seconds // 60)} min)",
        f"  Iteraciones: {plan.total_iterations}",
        f"  Salida:      {plan.output_file}",
    ]

    if plan.alert_conditions:
        lines.append("  Alertas:")
        for condition in plan.alert_conditions:
            lines.append(f"    - {condition}")

    if plan.stop_conditions:
        lines.append("  Parada automática:")
        for condition in plan.stop_conditions:
            lines.append(f"    - {condition}")

    lines.extend([
        "Puedes seguir usando el chat mientras la tarea se ejecuta en segundo plano.",
        "Para cancelarla di:",
        '  - "cancela la tarea"',
        '  - "cancela la tarea 1"',
        f'  - "cancela la tarea {plan.task_id}"',
    ])

    message = "\n".join(lines)

    return {
        "message": message,
        "task": {
            "task_id": plan.task_id,
            "description": plan.description,
            "commands": plan.commands,
            "interval_seconds": plan.interval_seconds,
            "duration_seconds": plan.duration_seconds,
            "output_file": plan.output_file,
            "status": "active",
        },
    }
    
def _handle_cancel_task(user_input: str) -> str:
    target_id, error = _resolve_task_id_for_cancel(user_input)
    if error:
        return error

    cancelled = cancel_task(target_id)
    if not cancelled:
        return (
            f"No se ha podido cancelar la tarea {target_id}. "
            "Puede que ya haya finalizado."
        )

    session_memory.clear_last_task_if_matches(target_id)
    return f"Tarea {target_id} cancelada."


def _handle_list_tasks() -> str:
    sorted_active = _get_sorted_active_tasks()
    if not sorted_active:
        return "No hay ninguna tarea activa en este momento."

    lines = [f"Tareas activas: {len(sorted_active)}"]
    for idx, (task_id, executor) in enumerate(sorted_active, start=1):
        plan = executor.plan
        lines.append(
            f"\n  Tarea #{idx}\n"
            f"  ID:          {task_id}\n"
            f"  Descripción: {plan.description}\n"
            f"  Comandos:    {', '.join(plan.commands)}\n"
            f"  Intervalo:   {plan.interval_seconds}s\n"
            f"  Duración:    {plan.duration_seconds}s\n"
            f"  Salida:      {plan.output_file}"
        )
    return "\n".join(lines)


def _handle_session_question(user_input: str) -> str:
    text = user_input.lower()

    session_log.log(
        EventType.SESSION_QUESTION,
        f"Pregunta sobre sesión: {user_input[:60]}",
        data={"user_input": user_input},
    )

    if any(
        m in text
        for m in (
            "historial",
            "hemos ejecutado",
            "hemos medido",
            "tareas anteriores",
        )
    ):
        context = task_history.build_history_summary()
    else:
        context = session_log.build_session_summary()

    messages = conversation_history.build_messages(
        system_prompt=SESSION_INTERPRETER_PROMPT,
        extra_user_content=f"Contexto de la sesión:\n{context}",
    )
    return ask_llm(messages).strip()


def _handle_analysis(user_input: str) -> str:
    csv_path, task_id_or_error = _resolve_csv_for_analysis(user_input)
    if csv_path is None:
        return task_id_or_error

    try:
        analysis = analyze_csv(csv_path, task_id=task_id_or_error or "")
    except FileNotFoundError:
        return f"No he encontrado el fichero CSV en {csv_path}."
    except ValueError as exc:
        return f"No he podido leer el CSV: {exc}"

    messages = conversation_history.build_messages(
        system_prompt=ANALYSIS_INTERPRETER_PROMPT,
        extra_user_content=f"Análisis calculado:\n{analysis.summary_text}",
    )
    return ask_llm(messages).strip()


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def run_pipeline(user_input: str) -> dict[str, Any] | str:
    conversation_history.add_user_message(user_input)
    normalized = _strip_conversational_prefix(user_input)

    if detect_analysis_intent(normalized):
        response = _handle_analysis(user_input)
        conversation_history.add_assistant_message(response)
        return response

    if detect_session_question_intent(normalized):
        response = _handle_session_question(user_input)
        conversation_history.add_assistant_message(response)
        return response

    if detect_cancel_intent(normalized):
        response = _handle_cancel_task(user_input)
        conversation_history.add_assistant_message(response)
        return response

    if detect_list_tasks_intent(normalized):
        response = _handle_list_tasks()
        conversation_history.add_assistant_message(response)
        return response

    if detect_task_intent(normalized):
        response = _handle_launch_task(user_input)

        if isinstance(response, dict):
            conversation_history.add_assistant_message(response["message"])
            return response

        conversation_history.add_assistant_message(response)
        return response

    routed_intent = route_intent(normalized)

    if routed_intent == "knowledge":
        session_log.log_knowledge_query(
            user_input=user_input,
            query_type="knowledge",
        )

        from llm.core.scpi_generator import answer_with_knowledge
        from llm.knowledge.context_builder import build_knowledge_payload
        from llm.knowledge.query_classifier import classify

        result = classify(normalized)

        if result.query_type in ("exact_command", "metric_definition", "unsupported"):
            response = answer_with_knowledge(normalized)
        else:
            payload = build_knowledge_payload(normalized, mode="knowledge")
            messages = conversation_history.build_messages(
                system_prompt=KNOWLEDGE_SYSTEM_PROMPT,
                extra_user_content=f"Contexto documental:\n{payload['context']}",
            )
            response = ask_llm(messages).strip()

        conversation_history.add_assistant_message(response)
        return response

    scpi_command = generate_scpi(normalized)

    if scpi_command == "UNKNOWN":
        messages = conversation_history.build_messages(
            system_prompt=COMMAND_INTERPRETER_PROMPT,
        )
        response = ask_llm(messages).strip()
        conversation_history.add_assistant_message(response)
        return response

    session_log.log_command_sent(scpi_command=scpi_command, user_input=user_input)
    session_memory.set_last_metric(scpi_command.rstrip("?"))

    raw_response = send_scpi_command(scpi_command)

    messages = conversation_history.build_messages(
        system_prompt=COMMAND_INTERPRETER_PROMPT,
        extra_user_content=(
            f"Comando ejecutado: {scpi_command}\n"
            f"Respuesta del equipo: {raw_response}"
        ),
    )
    response = ask_llm(messages).strip()
    conversation_history.add_assistant_message(response)
    return response