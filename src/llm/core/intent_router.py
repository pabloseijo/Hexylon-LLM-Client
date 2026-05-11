from __future__ import annotations

from llm.clients.ollama_client import ask_llm
from llm.memory.conversation_history import conversation_history


INTENT_ROUTER_SYSTEM_PROMPT = """
Eres un router de intención para el sistema Hexylon LLM.

Tu tarea es clasificar la entrada actual del usuario en UNA sola categoría:

- command
- knowledge

Definiciones:
- command:
  El usuario quiere ejecutar o consultar directamente algo en el equipo
  mediante un comando SCPI. Ejemplos: "dame la potencia actual",
  "qué frecuencia tengo", "muéstrame el lock", "lee el MER".

- knowledge:
  El usuario quiere una explicación técnica, interpretación, comparación,
  valoración o continuación conversacional basada en el contexto.
  Incluye preguntas anafóricas o follow-ups como:
  "y eso qué significa", "eso es alto o bajo", "explícame mejor",
  "para qué sirve", "cómo se interpreta", "es normal ese valor".

Reglas obligatorias:
- Usa el historial conversacional para resolver referencias como
  "eso", "ese valor", "lo anterior", "esa medición".
- Si hay ambigüedad, prioriza knowledge antes que command.
- Devuelve SOLO una palabra:
  command
  o
  knowledge
""".strip()


def route_intent(user_input: str) -> str:
    """
    Clasifica la intención usando el historial conversacional.

    Returns
    -------
    str
        "command" o "knowledge"
    """
    messages = conversation_history.build_messages(
        system_prompt=INTENT_ROUTER_SYSTEM_PROMPT,
    )
    response = ask_llm(messages, num_ctx=512).strip().lower()

    if response in {"command", "knowledge"}:
        return response

    # Fallback conservador: ante salida inválida, tratar como knowledge
    # para evitar intentar generar SCPI sobre preguntas conversacionales.
    return "knowledge"