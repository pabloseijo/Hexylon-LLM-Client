from __future__ import annotations

from typing import Any


def format_command_info_es(command: dict[str, Any]) -> str:
    """
    Convierte una entrada del catálogo en una respuesta técnica en español.
    """

    name = command["name"]
    description = command["description"]
    read_syntax = command.get("read_syntax") or []
    read_response = command.get("read_response") or ""
    units = command.get("units") or []
    related = command.get("related_commands") or []

    return "\n".join([
        "## Elemento consultado",
        f"- **Nombre**: {name}",
        "",
        "## Descripción",
        f"- {description}",
        "",
        "## Sintaxis",
        "```scpi",
        *(read_syntax or ["N/A"]),
        "```",
        "",
        "## Respuesta",
        f"- {read_response or 'No documentado'}",
        "",
        "## Unidades",
        f"- {', '.join(units) if units else 'No especificadas'}",
        "",
        "## Comandos relacionados",
        f"- {', '.join(related) if related else 'Ninguno'}",
    ])