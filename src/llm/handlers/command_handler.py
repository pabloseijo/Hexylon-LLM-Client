from __future__ import annotations

from llm.clients.mcp_client import send_scpi_command
from llm.clients.ollama_client import ask_llm
from llm.core.scpi_generator import generate_scpi
from llm.memory.conversation_history import conversation_history
from llm.memory.session_log import session_log
from llm.memory.session_memory import session_memory


COMMAND_INTERPRETER_PROMPT = """
Eres un asistente técnico del equipo Hexylon.

Interpreta la respuesta del equipo de forma clara y estructurada.

Reglas:
- Responde en español.
- Usa markdown.
- Incluye encabezado ##.
- Usa listas con -.
- Resalta valores con **negrita**.
""".strip()


def _safe_ask_llm(messages: list[dict[str, str]], fallback: str) -> str:
    try:
        return ask_llm(messages).strip()
    except Exception as exc:
        print("ERROR_LLM_COMMAND:", repr(exc))
        return fallback


def handle_command(user_input: str, normalized: str) -> str:
    # ---------------------------------------------------------
    # 1. Generar comando SCPI
    # ---------------------------------------------------------

    scpi_command = generate_scpi(normalized)

    if scpi_command == "UNKNOWN":
        return (
            "## Comando no reconocido\n\n"
            "- No se ha podido generar un comando SCPI válido.\n"
            "- Reformula la petición o especifica directamente el comando."
        )

    # ---------------------------------------------------------
    # 2. Logging + estado
    # ---------------------------------------------------------

    session_log.log_command_sent(
        scpi_command=scpi_command,
        user_input=user_input,
    )

    session_memory.set_last_metric(scpi_command.rstrip("?"))

    # ---------------------------------------------------------
    # 3. Ejecutar contra MCP / Hexylon
    # ---------------------------------------------------------

    try:
        raw_response = send_scpi_command(scpi_command)
    except Exception as exc:
        print("ERROR_SCPI:", repr(exc))
        return (
            "## Error de comunicación\n\n"
            f"- No se ha podido ejecutar el comando `{scpi_command}`.\n"
            "- Verifica la conexión con el equipo Hexylon."
        )

    # ---------------------------------------------------------
    # 4. Interpretación (LLM + fallback)
    # ---------------------------------------------------------

    messages = conversation_history.build_messages(
        system_prompt=COMMAND_INTERPRETER_PROMPT,
        extra_user_content=(
            f"Comando ejecutado: {scpi_command}\n"
            f"Respuesta del equipo: {raw_response}"
        ),
    )

    return _safe_ask_llm(
        messages,
        fallback=(
            "## Resultado\n\n"
            f"- **Comando**: `{scpi_command}`\n"
            f"- **Respuesta cruda**: `{raw_response}`\n\n"
            "## Interpretación\n\n"
            "- No se ha podido generar interpretación automática.\n"
            "- Consulta directamente la respuesta devuelta por el equipo."
        ),
    )