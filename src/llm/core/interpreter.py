import re

from llm.clients.ollama_client import ask_llm
from llm.normalization.unit_normalizer import (
    UnitNormalizationError,
    normalize_boolean,
    normalize_frequency_to_mhz,
)


class InterpreterError(Exception):
    """Error al interpretar una respuesta SCPI."""


def _interpret_freq(raw_response: str) -> str:
    try:
        normalized = normalize_frequency_to_mhz(raw_response)
    except UnitNormalizationError as exc:
        raise InterpreterError(str(exc)) from exc

    return f"La frecuencia actual configurada es {normalized}."


def _interpret_lock(raw_response: str) -> str:
    try:
        normalized = normalize_boolean(raw_response)
    except UnitNormalizationError as exc:
        raise InterpreterError(str(exc)) from exc

    if normalized == "TRUE":
        return "La señal está bloqueada correctamente."

    return "La señal no está bloqueada."


def _interpret_band(raw_response: str) -> str:
    text = raw_response.strip()

    match = re.search(r"\b(TER|SAT|FM|DAB)\b", text, re.IGNORECASE)
    if not match:
        raise InterpreterError(f"No se pudo interpretar la banda: {raw_response}")

    band = match.group(1).upper()
    return f"La banda actualmente seleccionada es {band}."


def _interpret_idn(raw_response: str) -> str:
    text = raw_response.strip()
    if not text:
        raise InterpreterError("La respuesta de identificación está vacía.")

    return f"Identificación del equipo: {text}"


def _interpret_prof(raw_response: str) -> str:
    text = raw_response.strip()
    if not text:
        raise InterpreterError("La respuesta del perfil está vacía.")

    return f"El perfil actual es: {text}."


def _interpret_with_llm(user_input: str, command: str, raw_response: str) -> str:
    system_prompt = """
Eres un asistente técnico especializado en interpretar respuestas SCPI de un equipo Hexylon.

Reglas obligatorias:
- Usa únicamente la información presente en la respuesta SCPI proporcionada.
- No inventes datos.
- No deduzcas valores no presentes.
- No añadas contexto externo.
- Si la respuesta no permite una interpretación clara, indícalo explícitamente.
- Responde en español, con tono técnico y preciso.
- Responde de forma breve.
- Normaliza unidades cuando sea posible:
  - frecuencia -> MHz
  - tasas binarias -> Mbps
  - valores en dB -> mantener dB
  - potencia -> mantener unidad original si es válida
"""

    user_prompt = f"""
Consulta original del usuario:
{user_input}

Comando SCPI ejecutado:
{command}

Respuesta SCPI cruda:
{raw_response}

Genera una respuesta técnica breve y fiel a la respuesta SCPI.
"""

    return ask_llm(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    ).strip()


def interpret_response(user_input: str, command: str, raw_response: str) -> str:
    command = command.strip().upper()
    raw_response = raw_response.strip()

    if not raw_response:
        raise InterpreterError("La respuesta SCPI está vacía.")

    if command == "FREQ?":
        return _interpret_freq(raw_response)

    if command == "LOCK?":
        return _interpret_lock(raw_response)

    if command == "BAND?":
        return _interpret_band(raw_response)

    if command == "IDN?":
        return _interpret_idn(raw_response)

    if command == "PROF?":
        return _interpret_prof(raw_response)

    if command in {"MEAS?", "PAR?"}:
        return _interpret_with_llm(user_input, command, raw_response)

    return _interpret_with_llm(user_input, command, raw_response)