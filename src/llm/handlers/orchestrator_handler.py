"""
Handler para secuencias orquestadas multi-máquina.

Recibe un mensaje del usuario que implica múltiples pasos con dependencia
secuencial entre equipos distintos (generador → hexylon).

Usa el LLM para descomponer el mensaje en pasos estructurados y luego
delega la ejecución al orquestador.
"""

from __future__ import annotations

import json
from typing import Any

from llm.clients.ollama_client import ask_llm
from llm.tasks.orchestrator import (
    CommandStep,
    TaskStep,
    SequenceStep,
    run_sequence,
)
from llm.tasks.task_planner import plan_task, TaskPlannerError
from llm.memory.conversation_history import conversation_history


SEQUENCE_PLANNER_PROMPT = """
Eres un planificador de secuencias para el sistema Hexylon + Generador de señales R&S SGU100A.

Tu tarea es descomponer una petición del usuario en una lista ordenada de pasos.
Cada paso va dirigido a una máquina concreta y tiene un tipo de acción.

Máquinas disponibles:
- "generator": generador de señales R&S SGU100A (comandos de configuración)
- "hexylon_a": equipo de medición Hexylon (comandos de lectura o tareas periódicas)
- "hexylon_b": equipo de medición Hexylon secundario

Tipos de paso:
- "command": envía un único comando SCPI y espera respuesta
- "task": lanza una medición periódica con intervalo y duración

## Comandos del generador R&S SGU100A

Frecuencia:
- SOURce:FREQuency:CW <valor> — configura la frecuencia RF
  Ejemplos: FREQ 2 GHz, FREQ 594 MHz, SOURce:FREQuency:CW 2000000000
  Rango: 1 MHz a 40 GHz

Potencia/nivel:
- SOURce:POWer:LEVel:IMMediate:AMPLitude <valor>dBm — configura el nivel RF
  Ejemplos: POW -10dBm, POW 0dBm, SOURce:POWer:LEVel:IMMediate:AMPLitude -30dBm
  Rango: -120 a 25 dBm
- SOURce:POWer:POWer <valor> — configura el nivel sin considerar offset
  Ejemplo: POW:POW 15

Salida RF:
- OUTPut:STATe ON / OUTPut:STATe OFF — activa/desactiva la salida RF
- SETTings:APPLy — aplica la configuración (obligatorio en modo upconverter)

Control de sesión:
- LOCK? 12345 — bloquea el instrumento para control remoto exclusivo
- UNL 12345 — libera el bloqueo
- *RST — resetea el instrumento al estado por defecto
- *IDN? — consulta la identificación del instrumento

Nota sobre unidades:
- Frecuencia: GHz, MHz, kHz, Hz son válidos
- Potencia: siempre en dBm (no se admiten unidades lineales como V o W)

## Comandos del Hexylon (lectura)

POW?, MER?, CN?, CBER?, VBER?, LOCK?, FREQ?, MER?, LKM?, MEAS?

## Debes devolver ÚNICAMENTE un array JSON válido con esta estructura:

[
  {
    "step": 1,
    "machine_id": "generator",
    "machine_type": "generator",
    "action": "command",
    "command": "POW -10dBm"
  },
  {
    "step": 2,
    "machine_id": "generator",
    "machine_type": "generator",
    "action": "command",
    "command": "OUTPut:STATe ON"
  },
  {
    "step": 3,
    "machine_id": "hexylon_a",
    "machine_type": "hexylon",
    "action": "task",
    "commands": ["POW?"],
    "interval_seconds": 5,
    "duration_seconds": 600,
    "description": "Medición de potencia cada 5 segundos durante 10 minutos"
  }
]

Reglas obligatorias:
- Devuelve SOLO el array JSON. Sin texto antes ni después. Sin bloques de código.
- El orden de los pasos es el orden de ejecución — respeta la dependencia secuencial.
- Para pasos de tipo "command": incluye solo "machine_id", "machine_type", "action", "command".
- Para pasos de tipo "task": incluye "machine_id", "machine_type", "action", "commands", "interval_seconds", "duration_seconds", "description".
- Añade '?' a los comandos de lectura del Hexylon si no lo tienen.
- Los comandos de escritura del generador NO llevan '?'.
- "interval_seconds" y "duration_seconds" deben ser números positivos.
- Si el usuario menciona activar la salida del generador, añade OUTPut:STATe ON como paso previo a la medición.
- Si no puedes generar un plan válido, devuelve: [{"error": "motivo"}]

Ejemplos de conversión:

"pon la potencia en el generador a -10 dBm y después mide la potencia en hexylon_a cada 5 segundos durante 10 minutos"
→ [
    {"step": 1, "machine_id": "generator", "machine_type": "generator", "action": "command", "command": "POW -10dBm"},
    {"step": 2, "machine_id": "generator", "machine_type": "generator", "action": "command", "command": "OUTPut:STATe ON"},
    {"step": 3, "machine_id": "hexylon_a", "machine_type": "hexylon", "action": "task", "commands": ["POW?"], "interval_seconds": 5, "duration_seconds": 600, "description": "Medición de potencia cada 5 segundos durante 10 minutos"}
  ]

"pon la frecuencia del generador a 2 GHz y mide el MER en hexylon_a cada 10 segundos durante 5 minutos"
→ [
    {"step": 1, "machine_id": "generator", "machine_type": "generator", "action": "command", "command": "FREQ 2 GHz"},
    {"step": 2, "machine_id": "hexylon_a", "machine_type": "hexylon", "action": "task", "commands": ["MER?"], "interval_seconds": 10, "duration_seconds": 300, "description": "Medición de MER cada 10 segundos durante 5 minutos"}
  ]
""".strip()

def _parse_sequence_plan(raw: str) -> list[dict]:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines
            if not line.startswith("```")
        ).strip()

    data = json.loads(raw)

    if not isinstance(data, list):
        raise ValueError("La respuesta no es un array JSON.")

    if data and "error" in data[0]:
        raise ValueError(f"El planificador no pudo generar un plan: {data[0]['error']}")

    return data


def _build_steps(plan: list[dict]) -> list[SequenceStep]:
    from llm.tasks.task_models import TaskPlan
    from llm.tasks.task_planner import _build_output_filename, _get_output_dir

    steps: list[SequenceStep] = []

    for item in plan:
        machine_id = item["machine_id"]
        machine_type = item.get("machine_type", "hexylon")
        action = item["action"]

        if action == "command":
            steps.append(CommandStep(
                machine_id=machine_id,
                command=item["command"],
                machine_type=machine_type,
            ))

        elif action == "task":
            commands = item["commands"]
            output_file = str(
                _get_output_dir() / _build_output_filename(commands)
            )
            plan_obj = TaskPlan(
                commands=commands,
                interval_seconds=float(item["interval_seconds"]),
                duration_seconds=float(item["duration_seconds"]),
                output_file=output_file,
                description=item.get("description", ""),
                machine_id=machine_id,
            )
            steps.append(TaskStep(
                machine_id=machine_id,
                plan=plan_obj,
            ))

    return steps


def handle_orchestrated_sequence(user_input: str) -> dict[str, Any] | str:
    # 1. Descomponer en pasos con el LLM
    messages = [
        {"role": "system", "content": SEQUENCE_PLANNER_PROMPT},
        {"role": "user", "content": user_input},
    ]

    try:
        raw = ask_llm(messages)
        plan = _parse_sequence_plan(raw)
    except Exception as exc:
        return (
            "## Error al planificar la secuencia\n\n"
            f"- No se ha podido descomponer la petición en pasos: {exc}\n"
            "- Reformula la petición especificando claramente el equipo, "
            "el comando y la medición."
        )

    steps = _build_steps(plan)

    if not steps:
        return "## Error\n\n- No se han podido construir los pasos de la secuencia."

    # 2. Confirmar al usuario los pasos antes de ejecutar
    step_lines = []
    for i, step in enumerate(steps, start=1):
        if isinstance(step, CommandStep):
            step_lines.append(
                f"- **Paso {i}**: `{step.command}` → `{step.machine_id}`"
            )
        elif isinstance(step, TaskStep):
            step_lines.append(
                f"- **Paso {i}**: tarea `{step.plan.description}` → `{step.machine_id}`"
            )

    # 3. Ejecutar la secuencia
    result = run_sequence(steps)

    if not result.success:
        return (
            "## Secuencia interrumpida\n\n"
            f"- Pasos completados: {result.steps_completed} / {result.steps_total}\n"
            f"- Error: {result.error}\n\n"
            "## Pasos planificados\n\n"
            + "\n".join(step_lines)
        )

    # 4. Respuesta de éxito
    result_lines = []
    for sr in result.step_results:
        if sr["type"] == "command":
            result_lines.append(
                f"- **Paso {sr['step']}** (`{sr['machine_id']}`): "
                f"`{sr['command']}` → `{sr['response']}`"
            )
        elif sr["type"] == "task":
            result_lines.append(
                f"- **Paso {sr['step']}** (`{sr['machine_id']}`): "
                f"tarea `{sr['task_id']}` lanzada en background — "
                f"resultados en `{sr['output_file']}`"
            )
            
    return {
        "message": (
            "## Secuencia completada\n\n"
            + "\n".join(result_lines)
        ),
        "sequence": {
            "steps_completed": result.steps_completed,
            "steps_total": result.steps_total,
            "step_results": result.step_results,
        },
    }