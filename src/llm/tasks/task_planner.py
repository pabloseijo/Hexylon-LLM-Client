"""
Planificador de tareas para el cliente LLM de Hexylon.

Convierte una petición en lenguaje natural en un TaskPlan estructurado
usando el LLM para extraer:
- comandos SCPI
- intervalo
- duración
- descripción
- condiciones opcionales de alerta y parada

El planificador es el único componente de la rama tasks que invoca al LLM.
El executor y el writer son completamente deterministas.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from llm.clients.ollama_client import ask_llm
from llm.tasks.task_models import TaskCondition, TaskPlan


TASK_PLANNER_SYSTEM_PROMPT = """
Eres un planificador de tareas de medición para el equipo Hexylon.

Tu tarea es extraer de una petición en lenguaje natural los parámetros
necesarios para ejecutar una tarea de medición periódica.

Debes devolver ÚNICAMENTE un objeto JSON válido con esta estructura exacta:
{
  "commands": ["CMD1?", "CMD2?"],
  "interval_seconds": <número>,
  "duration_seconds": <número>,
  "description": "<descripción breve de la tarea>",
  "alert_conditions": [
    {
      "command": "MER?",
      "operator": "<",
      "threshold_raw": "20 dB",
      "action": "alert",
      "description": "Alertar si el MER baja de 20 dB"
    }
  ],
  "stop_conditions": [
    {
      "command": "CBER?",
      "operator": ">",
      "threshold_raw": "1E-4",
      "action": "stop",
      "description": "Parar si el CBER supera 1E-4"
    }
  ]
}

Reglas obligatorias:
- Devuelve SOLO el JSON. Sin texto antes ni después. Sin bloques de código.
- "commands" debe contener únicamente comandos SCPI documentados para Hexylon.
- Añade '?' a los comandos de lectura si no lo tienen.
- "interval_seconds" debe ser un número positivo en segundos.
- "duration_seconds" debe ser un número positivo en segundos.
- "description" debe ser una descripción técnica breve de la tarea.
- "alert_conditions" y "stop_conditions" deben existir SIEMPRE, aunque estén vacías.
- Si no hay condiciones en la petición, devuelve listas vacías:
    "alert_conditions": []
    "stop_conditions": []
- Solo genera condiciones cuando el usuario las pida explícitamente.
- Cada condición debe tener exactamente:
    - "command"
    - "operator"
    - "threshold_raw"
    - "action"
    - "description"
- "action" debe ser:
    - "alert" para alert_conditions
    - "stop" para stop_conditions
- Operadores permitidos:
    <, <=, >, >=, ==
- Si no puedes determinar algún parámetro con seguridad, usa estos valores por defecto:
    interval_seconds: 10
    duration_seconds: 60
- Si la petición menciona múltiples métricas, inclúyelas todas en "commands".
- Si una condición usa una métrica que no está todavía en "commands", añádela también a "commands".
- No inventes métricas ni condiciones no mencionadas.
- Si no puedes generar un plan válido, devuelve: {"error": "motivo"}

Comandos de medición válidos (solo lectura):
POW?, CN?, MER?, CBER?, VBER?, BCHBER?, LKM?, PER?, SER?, HUM?, CSO?,
PREBER?, POSTBER?, PRELDPCBER?, PREBCHBER?, MSCBER?, FICBER?,
CBERA?, VBERA?, CBERB?, VBERB?, CBERC?, VBERC?, CNBOOT?,
ECHOES?, OPT_POW?, OPT_POW_1310?, OPT_POW_1490?, OPT_POW_1550?,
LOCK?, MEAS?, PAR?, FREQ?, BAND?

Ejemplos de conversión:
- "mídeme la potencia cada 5 segundos durante 10 minutos"
  → {
      "commands": ["POW?"],
      "interval_seconds": 5,
      "duration_seconds": 600,
      "description": "Medición de potencia cada 5 segundos durante 10 minutos",
      "alert_conditions": [],
      "stop_conditions": []
    }

- "registra POW y MER cada minuto durante 2 horas"
  → {
      "commands": ["POW?", "MER?"],
      "interval_seconds": 60,
      "duration_seconds": 7200,
      "description": "Registro de POW y MER cada minuto durante 2 horas",
      "alert_conditions": [],
      "stop_conditions": []
    }

- "mide el BER cada 30 segundos durante una hora"
  → {
      "commands": ["CBER?"],
      "interval_seconds": 30,
      "duration_seconds": 3600,
      "description": "Medición de CBER cada 30 segundos durante una hora",
      "alert_conditions": [],
      "stop_conditions": []
    }

- "mide MER cada 5 segundos durante 10 minutos y avísame si baja de 20 dB"
  → {
      "commands": ["MER?"],
      "interval_seconds": 5,
      "duration_seconds": 600,
      "description": "Medición de MER cada 5 segundos durante 10 minutos",
      "alert_conditions": [
        {
          "command": "MER?",
          "operator": "<",
          "threshold_raw": "20 dB",
          "action": "alert",
          "description": "Alertar si el MER baja de 20 dB"
        }
      ],
      "stop_conditions": []
    }

- "mide CBER cada 2 segundos durante 1 hora y para si supera 1E-4"
  → {
      "commands": ["CBER?"],
      "interval_seconds": 2,
      "duration_seconds": 3600,
      "description": "Medición de CBER cada 2 segundos durante 1 hora",
      "alert_conditions": [],
      "stop_conditions": [
        {
          "command": "CBER?",
          "operator": ">",
          "threshold_raw": "1E-4",
          "action": "stop",
          "description": "Parar si el CBER supera 1E-4"
        }
      ]
    }

- "mide LOCK cada 5 segundos durante 2 minutos y para si es FALSE"
  → {
      "commands": ["LOCK?"],
      "interval_seconds": 5,
      "duration_seconds": 120,
      "description": "Medición de LOCK cada 5 segundos durante 2 minutos",
      "alert_conditions": [],
      "stop_conditions": [
        {
          "command": "LOCK?",
          "operator": "==",
          "threshold_raw": "FALSE",
          "action": "stop",
          "description": "Parar si LOCK es FALSE"
        }
      ]
    }
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


def _normalize_command_name(command: str) -> str:
    command = command.strip()
    return command if command.endswith("?") else f"{command}?"


def _parse_conditions(
    raw_conditions: list[dict],
    expected_action: str,
) -> list[TaskCondition]:
    """
    Convierte una lista de diccionarios JSON en TaskCondition.
    """
    parsed: list[TaskCondition] = []

    for i, item in enumerate(raw_conditions, start=1):
        if not isinstance(item, dict):
            raise TaskPlannerError(
                f"La condición #{i} no es un objeto JSON válido."
            )

        required_fields = {"command", "operator", "threshold_raw", "action", "description"}
        missing = required_fields - set(item.keys())
        if missing:
            raise TaskPlannerError(
                f"Faltan campos en la condición #{i}: {sorted(missing)}"
            )

        action = str(item["action"]).strip().lower()
        if action != expected_action:
            raise TaskPlannerError(
                f"La condición #{i} tiene acción '{action}', pero se esperaba '{expected_action}'."
            )

        try:
            condition = TaskCondition(
                command=_normalize_command_name(str(item["command"])),
                operator=str(item["operator"]).strip(),
                threshold_raw=str(item["threshold_raw"]).strip(),
                action=action,
                description=str(item["description"]).strip(),
            )
        except ValueError as exc:
            raise TaskPlannerError(
                f"Condición inválida #{i}: {exc}"
            ) from exc

        parsed.append(condition)

    return parsed


def _parse_plan_response(raw: str, user_input: str) -> TaskPlan:
    """
    Parsea la respuesta JSON del LLM y construye un TaskPlan.

    Raises
    ------
    TaskPlannerError
        Si el JSON es inválido, contiene un error explícito o faltan campos.
    """
    raw = raw.strip()

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

    required_fields = [
        "commands",
        "interval_seconds",
        "duration_seconds",
        "alert_conditions",
        "stop_conditions",
    ]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise TaskPlannerError(
            f"Faltan campos obligatorios en el plan: {missing}"
        )

    commands_raw = data["commands"]
    if not isinstance(commands_raw, list):
        raise TaskPlannerError("El campo 'commands' debe ser una lista.")

    commands = [_normalize_command_name(str(cmd)) for cmd in commands_raw]
    if not commands:
        raise TaskPlannerError("El plan no contiene ningún comando.")

    try:
        interval = float(data["interval_seconds"])
        duration = float(data["duration_seconds"])
    except (TypeError, ValueError) as exc:
        raise TaskPlannerError(
            "El intervalo y la duración deben ser numéricos."
        ) from exc

    if interval <= 0:
        raise TaskPlannerError(
            f"El intervalo debe ser positivo, recibido: {interval}"
        )
    if duration <= 0:
        raise TaskPlannerError(
            f"La duración debe ser positiva, recibida: {duration}"
        )

    raw_alert_conditions = data.get("alert_conditions", [])
    raw_stop_conditions = data.get("stop_conditions", [])

    if not isinstance(raw_alert_conditions, list):
        raise TaskPlannerError("El campo 'alert_conditions' debe ser una lista.")
    if not isinstance(raw_stop_conditions, list):
        raise TaskPlannerError("El campo 'stop_conditions' debe ser una lista.")

    alert_conditions = _parse_conditions(raw_alert_conditions, expected_action="alert")
    stop_conditions = _parse_conditions(raw_stop_conditions, expected_action="stop")

    # Asegurar que los comandos usados en condiciones estén en commands
    condition_commands = {cond.command for cond in alert_conditions + stop_conditions}
    for cmd in sorted(condition_commands):
        if cmd not in commands:
            commands.append(cmd)

    output_filename = _build_output_filename(commands)
    output_file = str(_get_output_dir() / output_filename)

    description = data.get("description") or user_input

    return TaskPlan(
        commands=commands,
        interval_seconds=interval,
        duration_seconds=duration,
        output_file=output_file,
        description=description,
        alert_conditions=alert_conditions,
        stop_conditions=stop_conditions,
    )


def plan_task(user_input: str) -> TaskPlan:
    """
    Convierte una petición en lenguaje natural en un TaskPlan estructurado.

    Parameters
    ----------
    user_input:
        Petición del usuario, p. ej.
        "mídeme la potencia cada 5 segundos durante 10 minutos".

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