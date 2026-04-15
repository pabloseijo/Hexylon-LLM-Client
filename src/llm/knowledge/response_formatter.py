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
    """
    Construye una respuesta completa y estructurada para un comando SCPI
    concreto a partir del catálogo. No invoca al LLM.

    Parameters
    ----------
    command_name:
        Nombre del comando tal como aparece en el catálogo (p. ej. 'FREQ').

    Returns
    -------
    str
        Respuesta formateada lista para mostrar al usuario, o mensaje de
        comando no encontrado si no existe en el catálogo.
    """
    info = get_command_info(command_name)
    if not info:
        return (
            f"El comando '{command_name}' no está documentado en el catálogo "
            f"de la API Hexylon."
        )

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

    lines: list[str] = []

    lines.append(f"Comando: {name}")
    lines.append(f"Categoría: {category}")
    lines.append("")
    lines.append(f"Descripción: {description}")

    if read_syntax or write_syntax:
        lines.append("")
        lines.append("Sintaxis:")
        for s in read_syntax:
            lines.append(f"  {s}   (lectura)")
        for s in write_syntax:
            lines.append(f"  {s}   (escritura)")

    if read_response:
        lines.append("")
        lines.append(f"Respuesta de lectura: {read_response}")

    if write_values:
        lines.append("")
        lines.append(f"Valores de escritura: {_inline_list(write_values)}")

    if units:
        lines.append("")
        lines.append(f"Unidades: {_inline_list(units)}")

    if constraints:
        lines.append("")
        lines.append("Restricciones:")
        lines.append(_list_or_none(constraints))

    if notes:
        lines.append("")
        lines.append("Notas:")
        lines.append(_list_or_none(notes))

    if examples:
        lines.append("")
        lines.append("Ejemplos:")
        lines.append(_list_or_none(examples))

    if related:
        lines.append("")
        lines.append(f"Comandos relacionados: {_inline_list(related)}")

    return "\n".join(lines)


def format_metric_answer(command_name: str) -> str:
    """
    Construye una respuesta orientada a la definición de una métrica de señal.

    Más concisa que format_command_answer: omite la sección de escritura
    cuando no aplica y añade un encabezado orientado a definición.

    Parameters
    ----------
    command_name:
        Nombre del comando de métrica (p. ej. 'MER', 'CBER').
    """
    info = get_command_info(command_name)
    if not info:
        return (
            f"La métrica '{command_name}' no está documentada en el catálogo "
            f"de la API Hexylon."
        )

    name = info["name"]
    description = info.get("description", "Sin descripción.")
    read_syntax = info.get("read_syntax") or []
    read_response = info.get("read_response")
    units = info.get("units")
    notes = info.get("notes") or []
    constraints = info.get("constraints") or []
    related = info.get("related_commands") or []

    lines: list[str] = []

    lines.append(f"Métrica: {name}")
    lines.append("")
    lines.append(f"Definición: {description}")

    if read_syntax:
        lines.append("")
        lines.append(f"Comando de lectura: {read_syntax[0]}")

    if read_response:
        lines.append(f"Respuesta: {read_response}")

    if units:
        lines.append(f"Unidades: {_inline_list(units)}")

    if notes:
        lines.append("")
        lines.append("Notas:")
        lines.append(_list_or_none(notes))

    if constraints:
        lines.append("")
        lines.append("Restricciones:")
        lines.append(_list_or_none(constraints))

    if related:
        lines.append("")
        lines.append(f"Métricas relacionadas: {_inline_list(related)}")

    return "\n".join(lines)


def format_topic_answer(topic_names: list[str]) -> str:
    """
    Construye un resumen del área funcional indicada usando el topic_catalog.

    Este método es semideterminista: el contenido viene del catálogo pero
    puede complementarse con generación restringida en el router si el
    topic_context es insuficiente.

    Parameters
    ----------
    topic_names:
        Lista de nombres de topics seleccionados.
    """
    context = get_topic_context(topic_names)
    if not context or not context.strip():
        names = ", ".join(topic_names) if topic_names else "desconocido"
        return (
            f"No se ha encontrado documentación para el área '{names}' "
            f"en el catálogo de Hexylon."
        )
    return context.strip()


def format_unknown_answer(user_input: str) -> str:
    """
    Respuesta estándar para consultas fuera del dominio de la API Hexylon.

    Parameters
    ----------
    user_input:
        Petición original del usuario (usada para personalizar el mensaje).
    """
    _ = user_input  # reservado para personalización futura
    return (
        "Esta consulta está fuera del ámbito de la API Hexylon documentada.\n"
        "Puedo ayudarte con:\n"
        "  - Descripción y sintaxis de comandos SCPI del Hexylon.\n"
        "  - Explicación de métricas de señal (MER, C/N, BER, etc.).\n"
        "  - Áreas funcionales de la API: sintonía, espectro, perfiles, IPTV, etc.\n"
        "  - Cómo realizar operaciones concretas sobre el equipo."
    )