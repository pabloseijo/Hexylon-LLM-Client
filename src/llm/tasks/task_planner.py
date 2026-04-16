"""
Planificador de tareas para el cliente LLM de Hexylon.

Convierte una petición en lenguaje natural en un TaskPlan estructurado
usando el LLM para extraer: comandos SCPI, intervalo, duración y nombre
del fichero de salida.

El planificador es el único componente de la rama tasks que invoca al LLM.
El executor y el writer son completamente deterministas.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from llm.clients.ollama_client import ask_llm
from llm.tasks.task_models import TaskPlan


TASK_PLANNER_SYSTEM_PROMPT = """
Eres un planificador de tareas de medición para el equipo Hexylon.

Tu tarea es extraer de una petición en lenguaje natural los parámetros
necesarios para ejecutar una tarea de medición periódica.

Debes devolver ÚNICAMENTE un objeto JSON válido con esta estructura exacta:
{
  "commands": ["CMD1?", "CMD2?"],
  "interval_seconds": <número>,
  "duration_seconds": <número>,
  "description": "<descripción breve de la tarea>"
}

Reglas obligatorias:
- Devuelve SOLO el JSON. Sin texto antes ni después. Sin bloques de código.
- "commands" debe contener únicamente comandos SCPI documentados para Hexylon.
- Añade '?' a los comandos de lectura si no lo tienen.
- "interval_seconds" debe ser un número positivo en segundos.
- "duration_seconds" debe ser un número positivo en segundos.
- Si no puedes determinar algún parámetro con seguridad, usa estos valores por defecto:
    interval_seconds: 10
    duration_seconds: 60
- Si la petición menciona múltiples métricas, inclúyelas todas en "commands".
- Si no puedes generar un plan válido, devuelve: {"error": "motivo"}

Comandos de medición válidos (solo lectura):
POW?, CN?, MER?, CBER?, VBER?, BCHBER?, LKM?, PER?, SER?, HUM?, CSO?,
PREBER?, POSTBER?, PRELDPCBER?, PREBCHBER?, MSCBER?, FICBER?,
CBERA?, VBERA?, CBERB?, VBERB?, CBERC?, VBERC?, CNBOOT?,
ECHOES?, OPT_POW?, OPT_POW_1310?, OPT_POW_1490?, OPT_POW_1550?,
LOCK?, MEAS?, PAR?, FREQ?, BAND?

Ejemplos de conversión:
- "mídeme la potencia cada 5 segundos durante 10 minutos"
  → {"commands": ["POW?"], "interval_seconds": 5, "duration_seconds": 600, ...}

- "registra POW y MER cada minuto durante 2 horas"
  → {"commands": ["POW?", "MER?"], "interval_seconds": 60, "duration_seconds": 7200, ...}

- "mide el BER cada 30 segundos durante una hora"
  → {"commands": ["CBER?"], "interval_seconds": 30, "duration_seconds": 3600, ...}
""".strip()


class TaskPlannerError(Exception):
    """Error al generar el plan de tarea."""


def _get_output_dir() -> Path:
    """
    Devuelve la ruta absoluta al directorio output/ en la raíz del proyecto.

    Sube desde este fichero (src/llm/tasks/) hasta la raíz del proyecto
    y construye la ruta a output/. Lo crea si no existe.

    También puede sobreescribirse con la variable de entorno HEXYLON_OUTPUT_DIR.
    """
    env_dir = os.getenv("HEXYLON_OUTPUT_DIR")
    if env_dir:
        output_dir = Path(env_dir)
    else:
        # src/llm/tasks/task_planner.py → subir 3 niveles → raíz del proyecto
        project_root = Path(__file__).resolve().parents[3]
        output_dir = project_root / "output"

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _build_output_filename(commands: list[str]) -> str:
    """
    Genera un nombre de fichero CSV único con timestamp detallado.

    Ejemplo:
    medicion_POW_MER_20260416_111945_482193.csv
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    cmd_names = "_".join(cmd.rstrip("?") for cmd in commands[:3])
    return f"medicion_{cmd_names}_{now}.csv"

def _parse_plan_response(raw: str, user_input: str) -> TaskPlan:
    """
    Parsea la respuesta JSON del LLM y construye un TaskPlan.

    Raises
    ------
    TaskPlannerError
        Si el JSON es inválido, contiene un error explícito o faltan campos.
    """
    raw = raw.strip()

    # Eliminar bloques de código si el LLM los añade igualmente
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines
            if not line.startswith("```")
        ).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TaskPlannerError(
            f"El LLM no devolvió JSON válido: {exc}\nRespuesta: {raw}"
        ) from exc

    if "error" in data:
        raise TaskPlannerError(
            f"El planificador no pudo generar un plan: {data['error']}"
        )

    required_fields = ["commands", "interval_seconds", "duration_seconds"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise TaskPlannerError(
            f"Faltan campos obligatorios en el plan: {missing}"
        )

    commands: list[str] = data["commands"]
    if not commands:
        raise TaskPlannerError("El plan no contiene ningún comando.")

    # Asegurar que los comandos tienen '?'
    commands = [
        cmd if cmd.endswith("?") else cmd + "?"
        for cmd in commands
    ]

    interval = float(data["interval_seconds"])
    duration = float(data["duration_seconds"])

    if interval <= 0:
        raise TaskPlannerError(
            f"El intervalo debe ser positivo, recibido: {interval}"
        )
    if duration <= 0:
        raise TaskPlannerError(
            f"La duración debe ser positiva, recibida: {duration}"
        )

    # El nombre del fichero se genera siempre de forma determinista en cliente
    output_filename = _build_output_filename(commands)
    output_file = str(_get_output_dir() / output_filename)

    description = data.get("description") or user_input

    return TaskPlan(
        commands=commands,
        interval_seconds=interval,
        duration_seconds=duration,
        output_file=output_file,
        description=description,
    )


def plan_task(user_input: str) -> TaskPlan:
    """
    Convierte una petición en lenguaje natural en un TaskPlan estructurado.

    Parameters
    ----------
    user_input:
        Petición del usuario, p. ej. "mídeme la potencia cada 5 segundos
        durante 10 minutos".

    Returns
    -------
    TaskPlan
        Plan de ejecución listo para ser consumido por task_executor.

    Raises
    ------
    TaskPlannerError
        Si el LLM no puede generar un plan válido.
    """
    messages = [
        {"role": "system", "content": TASK_PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    raw_response = ask_llm(messages)
    return _parse_plan_response(raw_response, user_input)


def try_plan_task(user_input: str) -> TaskPlan | str:
    """
    Versión segura de plan_task que devuelve un mensaje de error en lugar
    de lanzar excepción. Útil para integración con el pipeline de chat.
    """
    try:
        return plan_task(user_input)
    except TaskPlannerError as exc:
        return f"No he podido planificar la tarea: {exc}"