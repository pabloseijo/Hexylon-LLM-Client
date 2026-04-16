from llm.clients.mcp_client import send_scpi_command
from llm.core.interpreter import interpret_response
from llm.core.scpi_generator import detect_intent, generate_response, generate_scpi
from llm.tasks.task_planner import try_plan_task, TaskPlannerError
from llm.tasks.task_executor import launch_task
from llm.tasks.task_models import TaskResult


# Marcadores que indican que el usuario quiere lanzar una tarea periódica
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


def detect_task_intent(user_input: str) -> bool:
    """
    Detecta si la petición del usuario quiere lanzar una tarea periódica.

    Una tarea se caracteriza por tener un intervalo ("cada X segundos")
    y una duración ("durante Y minutos").
    """
    text = user_input.lower()
    return any(marker in text for marker in TASK_MARKERS)


def _on_task_complete(result: TaskResult) -> None:
    """
    Callback llamado cuando una tarea termina.
    Imprime el resumen en la consola para notificar al usuario.
    """
    print("\n")
    print("=" * 50)
    print(result.summary())
    print("=" * 50)
    print(">>> ", end="", flush=True)


def run_pipeline(user_input: str) -> str:
    """
    Ejecuta el flujo completo del sistema.

    - Si la intención es una tarea periódica, planifica y lanza la tarea
      de forma asíncrona y devuelve confirmación inmediata.
    - Si la intención es documental, responde usando la capa knowledge y no
      contacta con MCP ni Hexylon.
    - Si la intención es operativa, genera SCPI, lo envía al MCP y después
      interpreta la respuesta del equipo.
    """
    # --- Rama tasks: tarea periódica asíncrona ---
    if detect_task_intent(user_input):
        plan_or_error = try_plan_task(user_input)

        if isinstance(plan_or_error, str):
            # try_plan_task devolvió un mensaje de error
            return plan_or_error

        plan = plan_or_error
        launch_task(plan, on_complete=_on_task_complete)

        return (
            f"Tarea lanzada: {plan.description}\n"
            f"  Comandos:    {', '.join(plan.commands)}\n"
            f"  Intervalo:   {plan.interval_seconds}s\n"
            f"  Duración:    {plan.duration_seconds}s "
            f"({int(plan.duration_seconds // 60)} min)\n"
            f"  Iteraciones: {plan.total_iterations}\n"
            f"  Salida:      {plan.output_file}\n"
            f"Puedes seguir usando el chat mientras la tarea se ejecuta en segundo plano."
        )

    # --- Rama knowledge: respuesta documental ---
    intent = detect_intent(user_input)
    if intent == "knowledge":
        return generate_response(user_input)

    # --- Rama command: generación y ejecución de SCPI ---
    scpi_command = generate_scpi(user_input)
    if scpi_command == "UNKNOWN":
        return "No he podido determinar un comando SCPI válido para esa petición."

    raw_response = send_scpi_command(scpi_command)
    return interpret_response(user_input, scpi_command, raw_response)