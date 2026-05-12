from __future__ import annotations

import re
import time

from llm.clients.generator_client import send_generator_command
from llm.clients.mcp_client import send_scpi_command
from llm.clients.ollama_client import ask_llm
from llm.core.scpi_generator import generate_scpi
from llm.memory.conversation_history import conversation_history
from llm.memory.session_log import session_log
from llm.memory.session_memory import session_memory


COMMAND_INTERPRETER_PROMPT = """
Eres un asistente técnico del equipo Hexylon.

Interpreta únicamente los datos realmente ejecutados y devueltos por el sistema.

Reglas:
- Detecta el idioma del mensaje del usuario y responde en ese mismo idioma.
  Idiomas soportados: español, gallego, inglés. Si no puedes determinarlo, responde en español.
- Usa markdown.
- Incluye encabezado ##.
- Usa listas con -.
- Resalta valores con **negrita**.
- No inventes medidas no devueltas por el equipo.
- No asumas frecuencia, potencia, impedancia, distancia, antena ni calibración si no aparecen explícitamente en los datos.
- No conviertas dBµV a dBm salvo que el sistema proporcione una función determinista de conversión.
- Si se ejecutó un comando previo de frecuencia, indica a qué equipo se envió.
- Si solo se ejecutó una lectura en Hexylon, no afirmes que se configuró ninguna frecuencia.
""".strip()


_FREQ_PATTERN = re.compile(
    r"\b(?:en|a|de)?\s*(\d+(?:[.,]\d+)?)\s*(ghz|mhz|khz|hz)?\b",
    re.IGNORECASE,
)

_MEASUREMENT_MARKERS = (
    "mide",
    "medir",
    "medición",
    "medicion",
    "dame",
    "lee",
    "leer",
    "consulta",
)

_FREQUENCY_MARKERS = (
    "mhz",
    "ghz",
    "khz",
    "hz",
    "frecuencia",
)

_GENERATOR_MARKERS = (
    "generador",
    "generator",
    "sgu",
    "sgu100a",
)


def _extract_frequency_command(user_input: str) -> str | None:
    text = user_input.lower()

    if not any(marker in text for marker in _FREQUENCY_MARKERS):
        return None

    matches = list(_FREQ_PATTERN.finditer(text))

    if not matches:
        return None

    unit_map = {
        "HZ": "Hz",
        "KHZ": "kHz",
        "MHZ": "MHz",
        "GHZ": "GHz",
    }

    for match in matches:
        value_raw = match.group(1)
        unit_raw = match.group(2)

        if not value_raw:
            continue

        value = value_raw.replace(",", ".")
        unit_key = (unit_raw or "mhz").upper()

        if unit_key not in unit_map:
            unit_key = "MHZ"

        return f"FREQ {value} {unit_map[unit_key]}"

    return None


def _is_measurement_with_explicit_frequency(
    user_input: str,
    scpi_command: str,
) -> bool:
    text = user_input.lower()

    return (
        scpi_command.endswith("?")
        and any(marker in text for marker in _MEASUREMENT_MARKERS)
        and _extract_frequency_command(user_input) is not None
    )


def _frequency_target_is_generator(user_input: str) -> bool:
    text = user_input.lower()

    return any(marker in text for marker in _GENERATOR_MARKERS)


def _safe_ask_llm(
    messages: list[dict[str, str]],
    fallback: str,
) -> str:
    try:
        return ask_llm(messages, num_ctx=1024).strip()

    except Exception as exc:
        print("ERROR_LLM_COMMAND:", repr(exc))
        return fallback


def handle_command(
    user_input: str,
    normalized: str,
    machine_id: str | None = None,
) -> str:

    # ------------------------------------------------------------------
    # 1. Generación SCPI principal
    # ------------------------------------------------------------------

    scpi_command = generate_scpi(normalized)

    if scpi_command == "UNKNOWN":
        return (
            "## Comando no reconocido\n\n"
            "- No se ha podido generar un comando SCPI válido.\n"
            "- Reformula la petición o especifica directamente el comando."
        )

    # ------------------------------------------------------------------
    # 2. Detectar frecuencia explícita
    # ------------------------------------------------------------------

    frequency_command: str | None = None

    if _is_measurement_with_explicit_frequency(
        user_input=user_input,
        scpi_command=scpi_command,
    ):
        frequency_command = _extract_frequency_command(user_input)

    # ------------------------------------------------------------------
    # 3. Logging + memoria
    # ------------------------------------------------------------------

    session_log.log_command_sent(
        scpi_command=scpi_command,
        user_input=user_input,
    )

    session_memory.set_last_metric(
        scpi_command.rstrip("?")
    )

    session_memory.set_last_machine_id(
        machine_id
    )

    # ------------------------------------------------------------------
    # 4. Ejecución real
    # ------------------------------------------------------------------

    frequency_response: str | None = None
    frequency_target = "no aplica"

    try:

        # --------------------------------------------------------------
        # 4.1 Cambio de frecuencia
        # --------------------------------------------------------------

        if frequency_command:

            # ----------------------------------------------------------
            # Caso A → frecuencia del generador
            # ----------------------------------------------------------

            if _frequency_target_is_generator(user_input):

                frequency_target = "generator"

                frequency_response = send_generator_command(
                    frequency_command,
                    machine_id="generator",
                )

            # ----------------------------------------------------------
            # Caso B → frecuencia del Hexylon
            # ----------------------------------------------------------

            else:

                frequency_target = machine_id or "hexylon"

                frequency_response = send_scpi_command(
                    frequency_command,
                    machine_id=machine_id,
                )

                # ------------------------------------------------------
                # IMPORTANTE:
                # Esperar estabilización del tuner / AGC / demodulador
                # ------------------------------------------------------

                time.sleep(2.0)

                # ------------------------------------------------------
                # Forzar actualización de lock interno
                # ------------------------------------------------------

                try:
                    send_scpi_command(
                        "LOCK?",
                        machine_id=machine_id,
                    )
                except Exception:
                    pass

                # ------------------------------------------------------
                # Espera adicional corta
                # ------------------------------------------------------

                time.sleep(0.5)

        # --------------------------------------------------------------
        # 4.2 Ejecutar medición principal
        # --------------------------------------------------------------

        raw_response = send_scpi_command(
            scpi_command,
            machine_id=machine_id,
        )

    except Exception as exc:

        print("ERROR_SCPI:", repr(exc))

        return (
            "## Error de comunicación\n\n"
            "- No se ha podido ejecutar la operación.\n"
            f"- Comando de frecuencia: `{frequency_command or 'no aplica'}`\n"
            f"- Destino del comando de frecuencia: `{frequency_target}`\n"
            f"- Comando de medida: `{scpi_command}`\n"
            "- Verifica la conexión con el generador y con el equipo Hexylon."
        )

    # ------------------------------------------------------------------
    # 5. Interpretación
    # ------------------------------------------------------------------

    messages = conversation_history.build_messages(
        system_prompt=COMMAND_INTERPRETER_PROMPT,
        extra_user_content=(
            f"Petición del usuario: {user_input}\n"
            f"Comando previo de frecuencia: {frequency_command or 'no ejecutado'}\n"
            f"Destino del comando previo: {frequency_target}\n"
            f"Respuesta del comando previo: {frequency_response or 'no aplica'}\n"
            f"Comando de medición ejecutado en Hexylon: {scpi_command}\n"
            f"Respuesta del Hexylon: {raw_response}"
        ),
    )

    # ------------------------------------------------------------------
    # 6. Respuesta final
    # ------------------------------------------------------------------

    return _safe_ask_llm(
        messages,
        fallback=(
            "## Resultado\n\n"
            f"- **Petición**: {user_input}\n"
            f"- **Comando previo de frecuencia**: `{frequency_command or 'no ejecutado'}`\n"
            f"- **Destino del comando previo**: `{frequency_target}`\n"
            f"- **Respuesta del comando previo**: `{frequency_response or 'no aplica'}`\n"
            f"- **Comando de medición en Hexylon**: `{scpi_command}`\n"
            f"- **Respuesta del Hexylon**: `{raw_response}`\n"
        ),
    )