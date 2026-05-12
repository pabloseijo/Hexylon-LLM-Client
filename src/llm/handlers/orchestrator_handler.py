"""
Handler para secuencias orquestadas multi-máquina.

Recibe un mensaje del usuario que implica múltiples pasos con dependencia
secuencial entre equipos distintos (generador → hexylon).

Usa el LLM para descomponer el mensaje en pasos estructurados y luego
delega la ejecución al orquestador.
"""

from __future__ import annotations

import json
import re
from typing import Any
from datetime import datetime

from llm.clients.ollama_client import ask_llm
from llm.tasks.orchestrator import (
    CommandStep,
    TaskStep,
    SequenceStep,
    run_sequence,
)
from llm.tasks.task_planner import plan_task, TaskPlannerError
from llm.memory.conversation_history import conversation_history
from llm.tasks.orchestrator import (
    CommandStep,
    TaskStep,
    MatrixSweepStep,
    SequenceStep,
    run_sequence,
)

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
- "sweep": barrido de frecuencias — configura el generador en cada paso y mide en el Hexylon
- "matrix_sweep": barrido combinado frecuencia/potencia — cambia potencia y frecuencia del generador y mide en uno o varios Hexylon

## Comandos del generador R&S SGU100A

Frecuencia:
- SOURce:FREQuency:CW <valor> — configura la frecuencia RF
  Ejemplos: FREQ 2 GHz, FREQ 594 MHz
  Rango: 10 MHz a 40 GHz

Potencia/nivel:
- SOURce:POWer:LEVel:IMMediate:AMPLitude <valor>dBm
  Ejemplos: POW -10dBm, POW 0dBm
  Rango: -120 a 25 dBm

Salida RF:
- OUTPut:STATe ON / OUTPut:STATe OFF
- SETTings:APPLy

## Comandos del Hexylon (lectura)

POW?, MER?, CN?, CBER?, VBER?, LOCK?, FREQ?, LKM?, MEAS?

## Estructura JSON

Para pasos de tipo "command":
{
  "step": 1,
  "machine_id": "generator",
  "machine_type": "generator",
  "action": "command",
  "command": "POW -10dBm"
}

Para pasos de tipo "task":
{
  "step": 2,
  "machine_id": "hexylon_a",
  "machine_type": "hexylon",
  "action": "task",
  "commands": ["POW?"],
  "interval_seconds": 5,
  "duration_seconds": 120,
  "description": "Medición de potencia cada 5 segundos durante 2 minutos"
}

Para pasos de tipo "sweep":
{
  "step": 1,
  "machine_id_generator": "generator",
  "machine_id_hexylon": "hexylon_a",
  "action": "sweep",
  "freq_start_mhz": 500,
  "freq_stop_mhz": 800,
  "freq_step_mhz": 50,
  "dwell_seconds": 5,
  "commands": ["POW?"]
}

Para pasos de tipo "matrix_sweep":
{
  "step": 2,
  "machine_id_generator": "generator",
  "machine_ids_hexylon": ["hexylon_a", "hexylon_b"],
  "action": "matrix_sweep",
  "freq_start_mhz": 500,
  "freq_stop_mhz": 800,
  "freq_step_mhz": 50,
  "power_start_dbm": -10,
  "power_stop_dbm": -50,
  "power_step_dbm": -10,
  "dwell_seconds": 5,
  "commands": ["FREQ?", "POW?"]
}

Reglas obligatorias:
- Devuelve SOLO el array JSON. Sin texto antes ni después. Sin bloques de código.
- El orden de los pasos es el orden de ejecución.
- Para sweep: freq_start_mhz, freq_stop_mhz y freq_step_mhz son obligatorios.
- dwell_seconds es el tiempo de espera en cada frecuencia antes de medir (por defecto 5).
- Los comandos de escritura del generador NO llevan '?'.
- Si el usuario menciona activar la salida del generador, añade OUTPut:STATe ON antes del sweep.
- Si no puedes generar un plan válido, devuelve: [{"error": "motivo"}]
- Si el usuario pide barrer frecuencia y potencia a la vez, usa un único paso "matrix_sweep". No generes dos pasos "sweep" separados.
- Si menciona varios Hexylon, usa "machine_ids_hexylon" con todos ellos.

Ejemplos de conversión:

"barre el generador de 500 MHz a 800 MHz en pasos de 50 MHz y mide la potencia en hexylon_a"
→ [
    {"step": 1, "machine_id": "generator", "machine_type": "generator", "action": "command", "command": "OUTPut:STATe ON"},
    {"step": 2, "machine_id_generator": "generator", "machine_id_hexylon": "hexylon_a", "action": "sweep", "freq_start_mhz": 500, "freq_stop_mhz": 800, "freq_step_mhz": 50, "dwell_seconds": 5, "commands": ["POW?"]}
  ]

"pon la potencia en el generador a -10 dBm y mide la potencia en hexylon_a cada 5 segundos durante 2 minutos"
→ [
    {"step": 1, "machine_id": "generator", "machine_type": "generator", "action": "command", "command": "POW -10dBm"},
    {"step": 2, "machine_id": "generator", "machine_type": "generator", "action": "command", "command": "OUTPut:STATe ON"},
    {"step": 3, "machine_id": "hexylon_a", "machine_type": "hexylon", "action": "task", "commands": ["POW?"], "interval_seconds": 5, "duration_seconds": 120, "description": "Medición de potencia cada 5 segundos durante 2 minutos"}
  ]
  
"barre el generador de 500 MHz a 800 MHz en pasos de 50 MHz y la potencia de -10 dBm a -50 dBm en pasos de -10 dBm y mide la frecuencia y la potencia en hexylon_a y hexylon_b"
→ [
    {"step": 1, "machine_id": "generator", "machine_type": "generator", "action": "command", "command": "OUTPut:STATe ON"},
    {"step": 2, "machine_id_generator": "generator", "machine_ids_hexylon": ["hexylon_a", "hexylon_b"], "action": "matrix_sweep", "freq_start_mhz": 500, "freq_stop_mhz": 800, "freq_step_mhz": 50, "power_start_dbm": -10, "power_stop_dbm": -50, "power_step_dbm": -10, "dwell_seconds": 5, "commands": ["FREQ?", "POW?"]}
  ]
""".strip()


# ---------------------------------------------------------------------------
# Validación de rangos del generador
# ---------------------------------------------------------------------------

_FREQ_RANGE_HZ = (10e6, 40e9)    # 10 MHz – 40 GHz
_POW_RANGE_DBM = (-120.0, 25.0)  # -120 dBm – +25 dBm


def _validate_generator_command(command: str) -> str | None:
    """
    Valida que el comando del generador esté dentro de los rangos del SGU100A.
    Devuelve un mensaje de error si está fuera de rango, None si es válido.
    """
    cmd = command.strip().upper()

    # Validar potencia: POW -10dBm / POW -10 DBM
    pow_match = re.search(r"\bPOW\s+([+-]?\d+(?:\.\d+)?)", cmd)
    if pow_match:
        val = float(pow_match.group(1))
        lo, hi = _POW_RANGE_DBM
        if not (lo <= val <= hi):
            return (
                f"Potencia **{val} dBm** fuera de rango del SGU100A "
                f"({lo:.0f} dBm – +{hi:.0f} dBm)."
            )

    # Validar frecuencia: FREQ 500 MHZ / FREQ 2 GHZ
    freq_match = re.search(
        r"\bFREQ\s+(\d+(?:\.\d+)?)\s*(GHZ|MHZ|KHZ|HZ)?", cmd
    )
    if freq_match:
        val = float(freq_match.group(1))
        unit = (freq_match.group(2) or "HZ").upper()
        multipliers = {"GHZ": 1e9, "MHZ": 1e6, "KHZ": 1e3, "HZ": 1.0}
        hz = val * multipliers[unit]
        lo, hi = _FREQ_RANGE_HZ
        if not (lo <= hz <= hi):
            return (
                f"Frecuencia **{val} {unit}** fuera de rango del SGU100A "
                f"(10 MHz – 40 GHz)."
            )

    return None


def _validate_sweep_ranges(
    freq_start_hz: float,
    freq_stop_hz: float,
    freq_step_hz: float,
) -> str | None:
    """
    Valida los parámetros de un barrido de frecuencias.
    Devuelve mensaje de error o None si es válido.
    """
    lo, hi = _FREQ_RANGE_HZ
    for label, val in [
        ("inicio", freq_start_hz),
        ("fin", freq_stop_hz),
        ("paso", freq_step_hz),
    ]:
        if not (lo <= val <= hi):
            return (
                f"Frecuencia de {label} **{val/1e6:.1f} MHz** "
                f"fuera de rango (10 MHz – 40 GHz)."
            )
    if freq_step_hz <= 0:
        return "El paso de frecuencia debe ser mayor que 0."
    if freq_start_hz >= freq_stop_hz:
        return "La frecuencia de inicio debe ser menor que la de fin."
    return None

def _validate_power_sweep_ranges(
    power_start_dbm: float,
    power_stop_dbm: float,
    power_step_dbm: float,
) -> str | None:
    lo, hi = _POW_RANGE_DBM

    for label, val in [
        ("inicio", power_start_dbm),
        ("fin", power_stop_dbm),
    ]:
        if not (lo <= val <= hi):
            return (
                f"Potencia de {label} **{val:g} dBm** fuera de rango "
                f"({lo:.0f} dBm – +{hi:.0f} dBm)."
            )

    if power_step_dbm == 0:
        return "El paso de potencia debe ser distinto de 0."

    if power_start_dbm < power_stop_dbm and power_step_dbm < 0:
        return "El paso de potencia debe ser positivo si la potencia final es mayor."

    if power_start_dbm > power_stop_dbm and power_step_dbm > 0:
        return "El paso de potencia debe ser negativo si la potencia final es menor."

    return None
# ---------------------------------------------------------------------------
# Parseo del plan
# ---------------------------------------------------------------------------

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
    from llm.tasks.orchestrator import SweepStep
    from llm.tasks.orchestrator import SweepStep, MatrixSweepStep

    steps: list[SequenceStep] = []

    for item in plan:
        action = item["action"]

        if action == "command":
            command = item["command"]
            machine_type = item.get("machine_type", "hexylon")

            # Validar rangos si es un comando del generador
            if machine_type == "generator":
                error = _validate_generator_command(command)
                if error:
                    raise ValueError(error)

            steps.append(CommandStep(
                machine_id=item["machine_id"],
                command=command,
                machine_type=machine_type,
            ))

        elif action == "task":
            machine_id = item["machine_id"]
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

        elif action == "sweep":
            freq_start = float(item["freq_start_mhz"]) * 1e6
            freq_stop  = float(item["freq_stop_mhz"])  * 1e6
            freq_step  = float(item["freq_step_mhz"])  * 1e6
            dwell      = float(item.get("dwell_seconds", 5.0))
            commands   = item.get("commands", ["POW?"])

            # Validar rangos del sweep
            error = _validate_sweep_ranges(freq_start, freq_stop, freq_step)
            if error:
                raise ValueError(error)

            output_file = str(
                _get_output_dir() /
                f"sweep_{int(freq_start/1e6)}-{int(freq_stop/1e6)}MHz"
                f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

            steps.append(SweepStep(
                machine_id_generator=item.get("machine_id_generator", "generator"),
                machine_id_hexylon=item.get("machine_id_hexylon", "hexylon_a"),
                freq_start_hz=freq_start,
                freq_stop_hz=freq_stop,
                freq_step_hz=freq_step,
                commands=commands,
                dwell_seconds=dwell,
                output_file=output_file,
            ))

        elif action == "matrix_sweep":
            freq_start = float(item["freq_start_mhz"]) * 1e6
            freq_stop = float(item["freq_stop_mhz"]) * 1e6
            freq_step = float(item["freq_step_mhz"]) * 1e6

            power_start = float(item["power_start_dbm"])
            power_stop = float(item["power_stop_dbm"])
            power_step = float(item["power_step_dbm"])

            dwell = float(item.get("dwell_seconds", 5.0))
            commands = item.get("commands", ["FREQ?", "POW?"])
            machine_ids = item.get("machine_ids_hexylon", ["hexylon_a"])

            error = _validate_sweep_ranges(freq_start, freq_stop, freq_step)
            if error:
                raise ValueError(error)

            error = _validate_power_sweep_ranges(power_start, power_stop, power_step)
            if error:
                raise ValueError(error)

            output_file = str(
                _get_output_dir() /
                f"matrix_sweep_{int(freq_start/1e6)}-{int(freq_stop/1e6)}MHz"
                f"_{int(power_start)}-{int(power_stop)}dBm"
                f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

            steps.append(MatrixSweepStep(
                machine_id_generator=item.get("machine_id_generator", "generator"),
                machine_ids_hexylon=machine_ids,
                freq_start_hz=freq_start,
                freq_stop_hz=freq_stop,
                freq_step_hz=freq_step,
                power_start_dbm=power_start,
                power_stop_dbm=power_stop,
                power_step_dbm=power_step,
                commands=commands,
                dwell_seconds=dwell,
                output_file=output_file,
            ))

    return steps


# ---------------------------------------------------------------------------
# Handler principal
# ---------------------------------------------------------------------------

def handle_orchestrated_sequence(user_input: str) -> dict[str, Any] | str:
    # 1. Descomponer en pasos con el LLM
    messages = [
        {"role": "system", "content": SEQUENCE_PLANNER_PROMPT},
        {"role": "user", "content": user_input},
    ]

    try:
        raw = ask_llm(messages, num_ctx=2048)
        plan = _parse_sequence_plan(raw)
    except Exception as exc:
        return (
            "## Error al planificar la secuencia\n\n"
            f"- No se ha podido descomponer la petición en pasos: {exc}\n"
            "- Reformula la petición especificando claramente el equipo, "
            "el comando y la medición."
        )

    # 2. Construir pasos con validación de rangos
    try:
        steps = _build_steps(plan)
    except ValueError as exc:
        return (
            "## Parámetros fuera de rango\n\n"
            f"- {exc}\n\n"
            "## Rangos válidos del SGU100A\n\n"
            "- **Frecuencia**: 10 MHz – 40 GHz\n"
            "- **Potencia**: −120 dBm – +25 dBm"
        )

    if not steps:
        return "## Error\n\n- No se han podido construir los pasos de la secuencia."

    # 3. Confirmar pasos al usuario
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

    # 4. Ejecutar la secuencia
    result = run_sequence(steps)

    if not result.success:
        return (
            "## Secuencia interrumpida\n\n"
            f"- Pasos completados: {result.steps_completed} / {result.steps_total}\n"
            f"- Error: {result.error}\n\n"
            "## Pasos planificados\n\n"
            + "\n".join(step_lines)
        )

    # 5. Respuesta de éxito
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
        elif sr["type"] == "sweep":
            result_lines.append(
                f"- **Paso {sr['step']}** barrido de frecuencias: "
                f"`{sr['freq_start_mhz']:.0f} MHz` → `{sr['freq_stop_mhz']:.0f} MHz` "
                f"en pasos de `{sr['freq_step_mhz']:.0f} MHz` — "
                f"**{sr['points']} puntos** — "
                f"resultados en `{sr['output_file']}`"
            )
        elif sr["type"] == "matrix_sweep":
            result_lines.append(
                f"- **Paso {sr['step']}** barrido matricial frecuencia/potencia: "
                f"`{sr['freq_start_mhz']:.0f} MHz` → `{sr['freq_stop_mhz']:.0f} MHz` "
                f"paso `{sr['freq_step_mhz']:.0f} MHz`; "
                f"`{sr['power_start_dbm']:g} dBm` → `{sr['power_stop_dbm']:g} dBm` "
                f"paso `{sr['power_step_dbm']:g} dB` — "
                f"**{sr['points']} puntos** por equipo — "
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