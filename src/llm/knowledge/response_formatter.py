"""
Formateador de respuestas deterministas para la rama knowledge de Hexylon.

Este módulo construye respuestas estructuradas a partir del catálogo de
comandos y topics sin invocar al LLM. Es la fuente de verdad de primer nivel.

Funciones públicas:

    format_command_answer(command_name)   →  respuesta completa de un comando
    format_metric_answer(command_name)    →  respuesta enfocada en métrica
    format_topic_answer(topic_names)      →  resumen de un área funcional
    format_unknown_answer(user_input)     →  respuesta de fuera de dominio
"""

from __future__ import annotations

from llm.knowledge.command_catalog import get_command_info
from llm.knowledge.topic_catalog import get_topic_context


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _list_or_none(items: list[str] | None) -> str:
    """Formatea una lista como líneas con guión, o devuelve 'No disponible'."""
    if not items:
        return "  No disponible."
    return "\n".join(f"  - {item}" for item in items)


def _inline_list(items: list[str] | None) -> str:
    """Formatea una lista como texto inline separado por comas."""
    if not items:
        return "No disponible"
    return ", ".join(items)


# ---------------------------------------------------------------------------
# Respuestas deterministas
# ---------------------------------------------------------------------------

def format_command_answer(command_name: str) -> str:
    info = get_command_info(command_name)
    if not info:
        return format_unknown_answer(command_name)

    name = info["name"]
    category = info.get("category", "desconocida")
    description = info.get("description", "Sin descripción.")
    read_syntax = info.get("read_syntax") or []
    write_syntax = info.get("write_syntax") or []
    read_response = info.get("read_response")
    write_values = info.get("write_values")
    units = info.get("units")
    constraints = info.get("constraints") or []
    notes = info.get("notes") or []
    examples = info.get("examples") or []
    related = info.get("related_commands") or []

    syntax_lines = read_syntax + write_syntax
    syntax_block = "\n".join(syntax_lines) if syntax_lines else "N/A"

    return "\n".join([
        "## Elemento consultado",
        "",
        f"- **Comando**: `{name}`",
        f"- **Categoría**: {category}",
        "",
        "## Descripción",
        "",
        f"- {description}",
        "",
        "## Sintaxis o comandos relacionados",
        "",
        "```scpi",
        syntax_block,
        "```",
        "",
        "## Respuesta o comportamiento",
        "",
        f"- {read_response or 'No documentado'}",
        f"- **Valores de escritura**: {_inline_list(write_values)}",
        f"- **Unidades**: {_inline_list(units)}",
        "",
        "## Restricciones o notas",
        "",
        _list_or_none(constraints + notes),
        "",
        "## Ejemplos",
        "",
        _list_or_none(examples),
        "",
        "## Comandos relacionados",
        "",
        f"- {_inline_list(related)}",
    ])


def format_metric_answer(command_name: str) -> str:
    info = get_command_info(command_name)
    if not info:
        return format_unknown_answer(command_name)

    name = info["name"]
    description = info.get("description", "Sin descripción.")
    read_syntax = info.get("read_syntax") or []
    read_response = info.get("read_response")
    units = info.get("units")
    notes = info.get("notes") or []
    constraints = info.get("constraints") or []
    related = info.get("related_commands") or []

    syntax_block = "\n".join(read_syntax) if read_syntax else "N/A"

    return "\n".join([
        "## Elemento consultado",
        "",
        f"**{name}**",
        "",
        "## Descripción",
        "",
        f"- {description}",
        "",
        "## Sintaxis o comandos relacionados",
        "",
        "```scpi",
        syntax_block,
        "```",
        "",
        "## Respuesta o comportamiento",
        "",
        f"- {read_response or 'No documentado'}",
        f"- **Unidades**: {_inline_list(units)}",
        "",
        "## Restricciones o notas",
        "",
        _list_or_none(constraints + notes),
        "",
        "## Métricas relacionadas",
        "",
        f"- {_inline_list(related)}",
    ])


def format_topic_answer(topic_names: list[str]) -> str:
    context = get_topic_context(topic_names)
    names = ", ".join(topic_names) if topic_names else "desconocido"

    if not context or not context.strip():
        return "\n".join([
            "## Área funcional",
            "",
            f"- **Topic**: {names}",
            "",
            "## Resultado",
            "",
            "- No se ha encontrado documentación suficiente en el catálogo de Hexylon.",
        ])

    return "\n".join([
        "## Área funcional",
        "",
        f"- **Topic**: {names}",
        "",
        "## Documentación disponible",
        "",
        context.strip(),
    ])


def format_unknown_answer(user_input: str) -> str:
    _ = user_input
    return "\n".join([
        "## Consulta fuera de dominio",
        "",
        "Esta consulta está fuera del ámbito de la API Hexylon documentada.",
        "",
        "## Capacidades disponibles",
        "",
        "- Descripción y sintaxis de comandos SCPI del Hexylon.",
        "- Explicación de métricas de señal como **MER**, **C/N** o **BER**.",
        "- Áreas funcionales de la API: sintonía, espectro, perfiles e IPTV.",
        "- Generación de comandos SCPI válidos para el equipo.",
    ])   
    