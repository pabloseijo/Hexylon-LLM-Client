"""
Constructor de contexto para la capa de conocimiento de Hexylon.

Este módulo orquesta la selección y composición del contexto documental que se
inyecta en el prompt del LLM.

Ahora soporta dos modos distintos:

- mode="command"
  Construye contexto orientado a generación de comandos SCPI.
  En este modo se permite incluir la referencia compacta de generación.

- mode="knowledge"
  Construye contexto orientado a explicación documental.
  En este modo no debe reutilizarse la referencia de generación SCPI, ya que
  contiene instrucciones incompatibles con respuestas explicativas.
"""

from __future__ import annotations

from typing import Literal

from llm.knowledge.api_reference import API_REFERENCE
from llm.knowledge.command_catalog import get_command_context
from llm.knowledge.command_selector import select_candidate_commands
from llm.knowledge.topic_catalog import get_topic_context
from llm.knowledge.topic_selector import select_candidate_topics

KnowledgeMode = Literal["command", "knowledge"]


# Referencia base específica para respuestas documentales.
# No incluye instrucciones de generación de SCPI.
KNOWLEDGE_BASE_REFERENCE = """
HEXYLON DOCUMENTED KNOWLEDGE REFERENCE

Use this context only to explain documented behavior of Hexylon commands and topics.

Allowed uses:
- explain what a command does
- explain command syntax
- explain what a command returns
- explain restrictions or requirements
- explain related functional areas of the API

Important rules:
- Do not invent undocumented behavior.
- Do not invent undocumented commands.
- Do not answer with only the SCPI command unless the user explicitly asks to generate or execute one.
- If documentation is insufficient, state that clearly.
""".strip()


def _get_base_reference(mode: KnowledgeMode) -> str:
    """
    Devuelve la referencia base adecuada según el modo de construcción.

    - command: usa la referencia compacta de generación SCPI
    - knowledge: usa una referencia documental neutra
    """
    if mode == "command":
        return API_REFERENCE.strip()

    return KNOWLEDGE_BASE_REFERENCE


def build_knowledge_context(
    user_input: str,
    *,
    mode: KnowledgeMode = "command",
    include_reference: bool = True,
    max_commands: int = 5,
    max_topics: int = 3,
) -> str:
    """
    Construye el contexto documental final para una petición del usuario.

    El contexto puede incluir:
    - referencia base adaptada al modo
    - comandos candidatos detectados heurísticamente
    - topics candidatos detectados heurísticamente

    Parameters
    ----------
    user_input:
        Petición original del usuario en lenguaje natural.
    mode:
        Modo de construcción del contexto:
        - "command": contexto orientado a generación de SCPI
        - "knowledge": contexto orientado a explicación documental
    include_reference:
        Si es True, incluye la referencia base correspondiente al modo.
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
        base_reference = _get_base_reference(mode)
        if mode == "command":
            blocks.append("BASE API REFERENCE:\n" + base_reference)
        else:
            blocks.append("BASE KNOWLEDGE REFERENCE:\n" + base_reference)

    command_names = select_candidate_commands(user_input, max_commands=max_commands)
    command_context = get_command_context(command_names)
    if command_context:
        blocks.append("COMMAND-SPECIFIC CONTEXT:\n" + command_context.strip())

    topic_names = select_candidate_topics(user_input, max_topics=max_topics)
    topic_context = get_topic_context(topic_names)
    if topic_context:
        blocks.append("TOPIC-SPECIFIC CONTEXT:\n" + topic_context.strip())
        
    # Incluir comandos del generador si la consulta los menciona
    from llm.knowledge.generator_command_catalog import (
        get_generator_command_context,
        GENERATOR_COMMAND_CATALOG,
    )

    generator_names = [
        k for k in GENERATOR_COMMAND_CATALOG.keys()
        if k.lower().replace(":", "").replace("*", "") in user_input.lower().replace(":", "").replace("*", "")
        or any(
            alias.lower() in user_input.lower()
            for alias in (GENERATOR_COMMAND_CATALOG[k].get("aliases") or [])
        )
    ]
    
    if generator_names:
        gen_context = get_generator_command_context(generator_names)
        if gen_context:
            blocks.append("GENERATOR (R&S SGU100A) COMMAND CONTEXT:\n" + gen_context.strip())

    return "\n\n".join(blocks).strip()


def build_knowledge_payload(
    user_input: str,
    *,
    mode: KnowledgeMode = "command",
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
    - ajustes futuros del pipeline

    Returns
    -------
    dict[str, object]
        Diccionario con:
        - user_input
        - mode
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
        mode=mode,
        include_reference=include_reference,
        max_commands=max_commands,
        max_topics=max_topics,
    )

    return {
        "user_input": user_input,
        "mode": mode,
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

    Esta función puede ser útil para decidir dinámicamente si compensa
    enriquecer el prompt con contexto adicional.
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