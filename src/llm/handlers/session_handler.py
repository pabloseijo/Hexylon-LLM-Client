from __future__ import annotations

from llm.clients.ollama_client import ask_llm
from llm.memory.conversation_history import conversation_history
from llm.memory.session_log import session_log, EventType
from llm.memory.task_history import task_history


# ---------------------------------------------------------------------------
# Prompt del sistema
# ---------------------------------------------------------------------------

SESSION_INTERPRETER_PROMPT = """
Eres un asistente técnico del sistema Hexylon LLM.

Responde preguntas sobre el estado actual de la sesión de forma clara,
estructurada y en español.

Reglas obligatorias:
- Usa markdown válido.
- Usa encabezados con ##.
- Usa listas con -.
- Resalta elementos importantes con **negrita**.
- No devuelvas logs crudos.
""".strip()


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def handle_session_question(user_input: str) -> str:
    """
    Responde preguntas sobre el estado de la sesión actual.
    """

    text = user_input.lower()

    # Logging de evento
    session_log.log(
        EventType.SESSION_QUESTION,
        f"Pregunta sobre sesión: {user_input[:80]}",
        data={"user_input": user_input},
    )

    # -----------------------------------------------------------------------
    # Selección de contexto
    # -----------------------------------------------------------------------

    if any(
        marker in text
        for marker in (
            "historial",
            "hemos ejecutado",
            "hemos medido",
            "tareas anteriores",
        )
    ):
        context = task_history.build_history_summary()
    else:
        context = session_log.build_session_summary()

    # -----------------------------------------------------------------------
    # LLM (con fallback obligatorio)
    # -----------------------------------------------------------------------

    messages = conversation_history.build_messages(
        system_prompt=SESSION_INTERPRETER_PROMPT,
        extra_user_content=f"Contexto de la sesión:\n{context}",
    )

    try:
        return ask_llm(messages).strip()

    except Exception as exc:
        # Fallback determinista
        print("ERROR_SESSION_LLM:", repr(exc))

        return (
            "## Estado de la sesión\n\n"
            "- No se ha podido generar la respuesta mediante el modelo LLM.\n"
            "- Se devuelve información de contexto disponible.\n\n"
            "## Contexto\n\n"
            f"{context}\n"
        )