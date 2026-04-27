from __future__ import annotations

from llm.clients.ollama_client import ask_llm
from llm.memory.conversation_history import conversation_history
from llm.memory.session_log import session_log
from llm.knowledge.command_catalog import COMMAND_CATALOG, get_command_info
from llm.knowledge.context_builder import build_knowledge_payload
from llm.knowledge.formatters import format_command_info_es
from llm.knowledge.query_classifier import classify


KNOWLEDGE_SYSTEM_PROMPT = """
Eres un asistente técnico especializado en la API SCPI del equipo Hexylon.

Reglas obligatorias:
- Responde en español.
- Responde de forma técnica, clara y precisa.
- Usa exclusivamente el contexto documental proporcionado.
- No inventes comandos, sintaxis, restricciones ni comportamientos.
- Si la documentación no es suficiente para responder con seguridad, indícalo explícitamente.
- Responde en markdown válido.
""".strip()


def _safe_ask_llm(messages: list[dict[str, str]], fallback: str) -> str:
    try:
        return ask_llm(messages).strip()
    except Exception as exc:
        print("ERROR_LLM_KNOWLEDGE:", repr(exc))
        return fallback


def _extract_catalog_command(text: str) -> str | None:
    upper = text.upper()

    for command_name in sorted(COMMAND_CATALOG.keys(), key=len, reverse=True):
        if command_name in upper:
            return command_name

    return None


def handle_knowledge(user_input: str, normalized: str) -> str:
    session_log.log_knowledge_query(
        user_input=user_input,
        query_type="knowledge",
    )

    result = classify(normalized)

    if result.query_type in (
        "exact_command",
        "metric_definition",
        "unsupported",
    ):
        command_name = _extract_catalog_command(normalized)

        if command_name:
            command = get_command_info(command_name)
            if command:
                return format_command_info_es(command)

        return (
            "## Comando no encontrado\n\n"
            "- No se ha encontrado un comando documentado en el catálogo para esta consulta.\n"
            "- Indica explícitamente el comando SCPI, por ejemplo: `POW?`, `MER?` o `FREQ?`."
        )

    payload = build_knowledge_payload(normalized, mode="knowledge")

    messages = conversation_history.build_messages(
        system_prompt=KNOWLEDGE_SYSTEM_PROMPT,
        extra_user_content=f"Contexto documental:\n{payload['context']}",
    )

    return _safe_ask_llm(
        messages,
        fallback=(
            "## Consulta documental\n\n"
            "- No se ha podido completar la respuesta mediante LLM.\n"
            "- El contexto documental fue localizado, pero la interpretación automática no está disponible temporalmente.\n\n"
            "## Acción recomendada\n\n"
            "- Reintenta la consulta o especifica el comando SCPI concreto."
        ),
    )