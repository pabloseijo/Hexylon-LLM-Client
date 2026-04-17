import re

from llm.clients.mcp_client import send_scpi_command
from llm.core.interpreter import interpret_response
from llm.core.scpi_generator import detect_intent, generate_response, generate_scpi
from llm.memory.session_memory import session_memory
from llm.memory.session_log import session_log, EventType
from llm.memory.task_history import task_history
from llm.tasks.task_executor import cancel_task, get_active_tasks, launch_task
from llm.tasks.task_models import TaskResult, TaskStatus
from llm.tasks.task_planner import try_plan_task


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


# ---------------------------------------------------------------------------
# Utilidades de resolución de tareas
# ---------------------------------------------------------------------------

def _get_sorted_active_tasks() -> list[tuple[str, object]]:
    active = get_active_tasks()
    return sorted(active.items(), key=lambda item: item[0])


def _extract_explicit_task_id(user_input: str, active_task_ids: list[str]) -> str | None:
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

    if any(m in text for m in (
        "cancela la tarea", "cancelar la tarea", "cancela tarea",
        "cancelar tarea", "para la tarea", "detén la tarea", "deten la tarea",
    )):
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


# ---------------------------------------------------------------------------
# Callbacks y handlers
# ---------------------------------------------------------------------------

def _on_task_complete(result: TaskResult) -> None:
    """Callback al terminar una tarea — actualiza los tres niveles de memoria."""

    # Nivel 1 — memoria operativa
    session_memory.set_last_completed_task(
        task_id=result.plan.task_id,
        output_file=result.output_file,
    )
    session_memory.clear_last_task_if_matches(result.plan.task_id)

    # Nivel 2 + 3 según estado
    if result.status == TaskStatus.COMPLETED:
        session_log.log_task_completed(
            task_id=result.plan.task_id,
            description=result.plan.description,
            output_file=result.output_file or "",
            measurements=result.total_measurements,
        )
        task_history.record_completed(
            task_id=result.plan.task_id,
            output_file=result.output_file or "",
            measurements=result.total_measurements,
        )
    elif result.status == TaskStatus.CANCELLED:
        session_log.log_task_cancelled(result.plan.task_id)
        task_history.record_cancelled(
            task_id=result.plan.task_id,
            measurements=result.total_measurements,
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

    print("\n")
    print("=" * 50)
    print(result.summary())
    print("=" * 50)
    print(">>> ", end="", flush=True)


def _handle_launch_task(user_input: str) -> str:
    plan_or_error = try_plan_task(user_input)
    if isinstance(plan_or_error, str):
        return plan_or_error

    plan = plan_or_error
    launch_task(plan, on_complete=_on_task_complete)

    # Nivel 1
    session_memory.set_last_task_id(plan.task_id)

    # Nivel 2
    session_log.log_task_launched(
        task_id=plan.task_id,
        description=plan.description,
        commands=plan.commands,
    )

    # Nivel 3
    task_history.record_launched(
        task_id=plan.task_id,
        description=plan.description,
        commands=plan.commands,
        interval_seconds=plan.interval_seconds,
        duration_seconds=plan.duration_seconds,
        output_file=plan.output_file,
    )

    return (
        f"Tarea lanzada: {plan.description}\n"
        f"  ID:          {plan.task_id}\n"
        f"  Comandos:    {', '.join(plan.commands)}\n"
        f"  Intervalo:   {plan.interval_seconds}s\n"
        f"  Duración:    {plan.duration_seconds}s "
        f"({int(plan.duration_seconds // 60)} min)\n"
        f"  Iteraciones: {plan.total_iterations}\n"
        f"  Salida:      {plan.output_file}\n"
        f"Puedes seguir usando el chat mientras la tarea se ejecuta en segundo plano.\n"
        f"Para cancelarla di:\n"
        f'  - "cancela la tarea"\n'
        f'  - "cancela la tarea 1"\n'
        f'  - "cancela la tarea {plan.task_id}"'
    )


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


SESSION_INTERPRETER_PROMPT = """
Eres un asistente técnico del sistema Hexylon LLM.

El usuario te hace una pregunta sobre el estado actual de la sesión o sobre
lo que se ha hecho. Tienes acceso al contexto estructurado de la sesión.

Responde en español de forma natural y conversacional, como si fueras un
colaborador que conoce bien lo que está pasando. No enumeres logs ni eventos
crudos. Sintetiza y explica.

Si hay tareas activas, menciónalas. Si hay tareas completadas, menciona qué
se midió y dónde están los resultados. Si no se ha hecho nada, dilo claramente.

No uses markdown. No uses listas con guiones. Responde en prosa.
""".strip()


def _handle_session_question(user_input: str) -> str:
    """Responde preguntas sobre la sesión inyectando contexto estructurado al LLM."""
    from llm.clients.ollama_client import ask_llm

    text = user_input.lower()

    session_log.log(
        EventType.SESSION_QUESTION,
        f"Pregunta sobre sesión: {user_input[:60]}",
        data={"user_input": user_input},
    )

    # Construir contexto según el tipo de pregunta
    if any(m in text for m in (
        "historial", "hemos ejecutado", "hemos medido", "tareas anteriores",
    )):
        context = task_history.build_history_summary()
    else:
        context = session_log.build_session_summary()

    messages = [
        {"role": "system", "content": SESSION_INTERPRETER_PROMPT},
        {
            "role": "user",
            "content": (
                f"Contexto de la sesión:\n{context}\n\n"
                f"Pregunta del usuario: {user_input}"
            ),
        },
    ]

    from llm.clients.ollama_client import ask_llm
    return ask_llm(messages).strip()


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def run_pipeline(user_input: str) -> str:
    """
    Ejecuta el flujo completo del sistema.

    Orden de evaluación:
    1. Pregunta sobre la sesión (sin LLM, desde memoria)
    2. Cancelar tarea activa
    3. Listar tareas activas
    4. Lanzar tarea periódica
    5. Respuesta documental (knowledge)
    6. Ejecución de comando SCPI puntual (command)
    """
    # --- Pregunta de sesión ---
    if detect_session_question_intent(user_input):
        return _handle_session_question(user_input)

    # --- Cancelación ---
    if detect_cancel_intent(user_input):
        return _handle_cancel_task(user_input)

    # --- Listado de tareas ---
    if detect_list_tasks_intent(user_input):
        return _handle_list_tasks()

    # --- Tarea periódica ---
    if detect_task_intent(user_input):
        return _handle_launch_task(user_input)

    # --- Knowledge ---
    intent = detect_intent(user_input)
    if intent == "knowledge":
        session_log.log_knowledge_query(
            user_input=user_input,
            query_type="knowledge",
        )
        return generate_response(user_input)

    # --- Command ---
    scpi_command = generate_scpi(user_input)
    if scpi_command == "UNKNOWN":
        return "No he podido determinar un comando SCPI válido para esa petición."

    session_log.log_command_sent(
        scpi_command=scpi_command,
        user_input=user_input,
    )
    session_memory.set_last_metric(scpi_command.rstrip("?"))

    raw_response = send_scpi_command(scpi_command)
    return interpret_response(user_input, scpi_command, raw_response)