from llm.ollama_client import ask_llm


SCPI_SYSTEM_PROMPT = """
Eres un traductor de lenguaje natural a comandos SCPI para un equipo Hexylon.

Reglas obligatorias:
- Devuelve únicamente el comando SCPI.
- No añadas explicaciones.
- No añadas comillas.
- No añadas texto antes ni después.
- Si no puedes determinarlo con seguridad, responde exactamente: UNKNOWN

Comandos permitidos en esta fase:
- IDN?
- FREQ?
- BAND?
- CH?
- INPUT?
- PROF?
- LOCK?
- MEAS?
- PAR?

Ejemplos:
Usuario: ¿Cuál es la frecuencia actual?
Respuesta: FREQ?

Usuario: Dime la identificación del equipo
Respuesta: IDN?

Usuario: ¿Está bloqueada la señal?
Respuesta: LOCK?

Usuario: Muéstrame las medidas actuales
Respuesta: MEAS?
"""

ALLOWED_COMMANDS = {
    "IDN?",
    "FREQ?",
    "BAND?",
    "CH?",
    "INPUT?",
    "PROF?",
    "LOCK?",
    "MEAS?",
    "PAR?",
    "UNKNOWN",
}


def normalize_command(text: str) -> str:
    return text.strip().splitlines()[0].strip()


def generate_scpi(user_input: str) -> str:
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