"""
Constructor de contexto para la capa de conocimiento de Hexylon.

Este módulo orquesta la selección y composición del contexto documental que se
inyecta en el prompt del LLM. Combina:

- referencia base compacta
- contexto por comando
- contexto por topic

Su objetivo es entregar al generador SCPI únicamente el contexto relevante
para la petición actual, reduciendo ruido y consumo de tokens.
"""

from __future__ import annotations

from llm.knowledge.api_reference import API_REFERENCE
from llm.knowledge.command_catalog import get_command_context
from llm.knowledge.command_selector import select_candidate_commands
from llm.knowledge.topic_catalog import get_topic_context
from llm.knowledge.topic_selector import select_candidate_topics


def build_knowledge_context(
    user_input: str,
    *,
    include_reference: bool = True,
    max_commands: int = 5,
    max_topics: int = 3,
) -> str:
    """
    Construye el contexto documental final para una petición del usuario.

    El contexto puede incluir:
    - referencia base compacta de la API
    - comandos candidatos detectados heurísticamente
    - topics candidatos detectados heurísticamente

    Parameters
    ----------
    user_input:
        Petición original del usuario en lenguaje natural.
    include_reference:
        Si es True, incluye siempre API_REFERENCE al inicio.
    max_commands:
        Número máximo de comandos candidatos a incluir.
    max_topics:
        Número máximo de topics candidatos a incluir.

    Returns
    -------
    str
        Bloque de contexto textual listo para inyectar en el prompt.
    """
    blocks: list[str] = []

    if include_reference:
        blocks.append("BASE API REFERENCE:\n" + API_REFERENCE.strip())

    command_names = select_candidate_commands(user_input, max_commands=max_commands)
    command_context = get_command_context(command_names)
    if command_context:
        blocks.append("COMMAND-SPECIFIC CONTEXT:\n" + command_context.strip())

    topic_names = select_candidate_topics(user_input, max_topics=max_topics)
    topic_context = get_topic_context(topic_names)
    if topic_context:
        blocks.append("TOPIC-SPECIFIC CONTEXT:\n" + topic_context.strip())

    return "\n\n".join(blocks).strip()


def build_knowledge_payload(
    user_input: str,
    *,
    include_reference: bool = True,
    max_commands: int = 5,
    max_topics: int = 3,
) -> dict[str, object]:
    """
    Construye una representación estructurada del contexto seleccionado.

    Esta función es útil para:
    - depuración
    - trazabilidad
    - inspección del routing documental
    - futuros ajustes del pipeline

    Returns
    -------
    dict[str, object]
        Diccionario con:
        - user_input
        - selected_commands
        - selected_topics
        - context
    """
    selected_commands = select_candidate_commands(
        user_input,
        max_commands=max_commands,
    )
    selected_topics = select_candidate_topics(
        user_input,
        max_topics=max_topics,
    )
    context = build_knowledge_context(
        user_input,
        include_reference=include_reference,
        max_commands=max_commands,
        max_topics=max_topics,
    )

    return {
        "user_input": user_input,
        "selected_commands": selected_commands,
        "selected_topics": selected_topics,
        "context": context,
    }


def has_relevant_knowledge(
    user_input: str,
    *,
    max_commands: int = 5,
    max_topics: int = 3,
) -> bool:
    """
    Indica si la petición del usuario activa algún comando o topic relevante.

    Esta función puede ser útil si más adelante quieres decidir dinámicamente:
    - si enriquecer el prompt
    - si usar solo la referencia base
    - si activar lógica adicional de fallback
    """
    selected_commands = select_candidate_commands(
        user_input,
        max_commands=max_commands,
    )
    selected_topics = select_candidate_topics(
        user_input,
        max_topics=max_topics,
    )

    return bool(selected_commands or selected_topics)