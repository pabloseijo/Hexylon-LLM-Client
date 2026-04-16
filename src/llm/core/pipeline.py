import re

from llm.clients.mcp_client import send_scpi_command
from llm.core.interpreter import interpret_response
from llm.core.scpi_generator import detect_intent, generate_response, generate_scpi
from llm.tasks.task_planner import try_plan_task
from llm.tasks.task_executor import launch_task, get_active_tasks, cancel_task
from llm.tasks.task_models import TaskResult


# ---------------------------------------------------------------------------
# Registro de la última tarea lanzada en la sesión
# ---------------------------------------------------------------------------

_last_task_id: str | None = None


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


# ---------------------------------------------------------------------------
# Detección de intención
# ---------------------------------------------------------------------------

def detect_task_intent(user_input: str) -> bool:
    """Detecta si el usuario quiere lanzar una tarea periódica."""
    text = user_input.lower()
    return any(marker in text for marker in TASK_MARKERS)


def detect_cancel_intent(user_input: str) -> bool:
    """Detecta si el usuario quiere cancelar una tarea."""
    text = user_input.lower()
    return any(marker in text for marker in CANCEL_MARKERS)


def detect_list_tasks_intent(user_input: str) -> bool:
    """Detecta si el usuario quiere ver las tareas activas."""
    text = user_input.lower()
    return any(marker in text for marker in LIST_TASKS_MARKERS)


# ---------------------------------------------------------------------------
# Utilidades de orden y resolución de tareas
# ---------------------------------------------------------------------------

def _get_sorted_active_tasks() -> list[tuple[str, object]]:
    """
    Devuelve las tareas activas ordenadas de más antigua a más reciente.

    Se asume que task_id tiene formato temporal tipo:
    task_YYYYMMDD_HHMMSS
    y que el dict de activas devuelve ejecutores con .plan
    """
    active = get_active_tasks()
    return sorted(active.items(), key=lambda item: item[0])


def _extract_explicit_task_id(user_input: str, active_task_ids: list[str]) -> str | None:
    """
    Busca un task_id real mencionado explícitamente en el texto.
    """
    text = user_input.lower()

    for task_id in active_task_ids:
        if task_id.lower() in text:
            return task_id

    return None


def _extract_ordinal_index(user_input: str) -> int | None:
    """
    Extrae un índice ordinal humano 1-based de expresiones como:
    - tarea 1
    - la tarea 2
    - task 3
    """
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
    """
    Resuelve qué tarea cancelar.

    Retorna:
    - (task_id, None) si pudo resolver
    - (None, mensaje_error) si no pudo resolver
    """
    global _last_task_id

    sorted_active = _get_sorted_active_tasks()
    if not sorted_active:
        return None, "No hay ninguna tarea activa en este momento."

    active_task_ids = [task_id for task_id, _ in sorted_active]
    text = user_input.lower().strip()

    # 1. ID real explícito
    explicit_task_id = _extract_explicit_task_id(user_input, active_task_ids)
    if explicit_task_id is not None:
        return explicit_task_id, None

    # 2. Referencia ordinal: "tarea 1", "tarea 2", ...
    ordinal_index = _extract_ordinal_index(user_input)
    if ordinal_index is not None:
        if 1 <= ordinal_index <= len(sorted_active):
            return sorted_active[ordinal_index - 1][0], None
        return None, (
            f"No existe la tarea {ordinal_index}. "
            f"Actualmente hay {len(sorted_active)} tareas activas."
        )

    # 3. "cancela la tarea" sin más -> usar la más reciente activa
    if (
        "cancela la tarea" in text
        or "cancelar la tarea" in text
        or "cancela tarea" in text
        or "cancelar tarea" in text
        or "para la tarea" in text
        or "detén la tarea" in text
        or "deten la tarea" in text
    ):
        return sorted_active[-1][0], None

    # 4. Fallback a última tarea conocida de la sesión, si sigue activa
    if _last_task_id and _last_task_id in active_task_ids:
        return _last_task_id, None

    # 5. Si solo hay una, usar esa
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
        "  - cancela la primera tarea\n"
        "  - cancela la tarea task_20260416_110556\n\n"
        f"Tareas activas:\n{ids}"
    )


# ---------------------------------------------------------------------------
# Handlers de tareas
# ---------------------------------------------------------------------------

def _on_task_complete(result: TaskResult) -> None:
    """Callback al terminar una tarea — notifica en consola."""
    print("\n")
    print("=" * 50)
    print(result.summary())
    print("=" * 50)
    print(">>> ", end="", flush=True)


def _handle_launch_task(user_input: str) -> str:
    """Planifica y lanza una tarea periódica."""
    global _last_task_id

    plan_or_error = try_plan_task(user_input)
    if isinstance(plan_or_error, str):
        return plan_or_error

    plan = plan_or_error
    launch_task(plan, on_complete=_on_task_complete)
    _last_task_id = plan.task_id

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
    """Cancela una tarea por ID explícito, posición o referencia semántica."""
    global _last_task_id

    target_id, error = _resolve_task_id_for_cancel(user_input)
    if error:
        return error

    cancelled = cancel_task(target_id)
    if not cancelled:
        return (
            f"No se ha podido cancelar la tarea {target_id}. "
            "Puede que ya haya finalizado."
        )

    if _last_task_id == target_id:
        _last_task_id = None

    return f"Tarea {target_id} cancelada."


def _handle_list_tasks() -> str:
    """Lista las tareas activas ordenadas de más antigua a más reciente."""
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


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def run_pipeline(user_input: str) -> str:
    """
    Ejecuta el flujo completo del sistema.

    Orden de evaluación:
    1. Cancelar tarea activa
    2. Listar tareas activas
    3. Lanzar tarea periódica
    4. Respuesta documental (knowledge)
    5. Ejecución de comando SCPI puntual (command)
    """
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
        return generate_response(user_input)

    # --- Command ---
    scpi_command = generate_scpi(user_input)
    if scpi_command == "UNKNOWN":
        return "No he podido determinar un comando SCPI válido para esa petición."

    raw_response = send_scpi_command(scpi_command)
    return interpret_response(user_input, scpi_command, raw_response)