from llm.clients.ollama_client import ask_llm


SCPI_SYSTEM_PROMPT = """
Eres un traductor de lenguaje natural a comandos SCPI para un equipo Hexylon.

Tu única tarea es devolver un único comando SCPI válido.

Reglas obligatorias:
- Devuelve únicamente el comando SCPI.
- No añadas explicaciones.
- No añadas comillas.
- No añadas texto antes ni después.
- Si no puedes determinar el comando con seguridad, responde exactamente: UNKNOWN.
- No inventes comandos.

Comandos permitidos en esta fase:
- IDN?
- FREQ?
- BAND?
- LOCK?
- MEAS?
- PAR?
- PROF?
"""

ALLOWED_COMMANDS = {
    "IDN?",
    "FREQ?",
    "BAND?",
    "LOCK?",
    "MEAS?",
    "PAR?",
    "PROF?",
    "UNKNOWN",
}


def normalize_command(text: str) -> str:
    return text.strip().splitlines()[0].strip()


def keyword_mapping(user_input: str) -> str | None:
    text = user_input.lower()

    if "perfil" in text:
        return "PROF?"
    if "parámetro" in text or "parametro" in text:
        return "PAR?"
    if "medida" in text or "medición" in text or "medicion" in text:
        return "MEAS?"
    if "bloque" in text or "lock" in text:
        return "LOCK?"
    if "banda" in text:
        return "BAND?"
    if "frecuencia" in text:
        return "FREQ?"
    if "identificación" in text or "identificacion" in text or "equipo" in text:
        return "IDN?"

    return None


def generate_scpi(user_input: str) -> str:
    mapped = keyword_mapping(user_input)
    if mapped is not None:
        return mapped

    response = ask_llm(
        [
            {"role": "system", "content": SCPI_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]
    )

    command = normalize_command(response)

    if command not in ALLOWED_COMMANDS:
        return "UNKNOWN"

    return command