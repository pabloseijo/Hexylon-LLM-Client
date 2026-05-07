import asyncio
import json
import os
from pathlib import Path
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1,10.113.0.148,10.113.0.149"
os.environ["no_proxy"] = os.environ["NO_PROXY"]

# Cargar máquinas desde config
_MACHINES_FILE = Path(__file__).parents[3] / "config" / "machines.json"

def _load_machines() -> dict:
    path = Path(__file__).parents[3] / "config" / "machines.json"
    with open(path) as f:
        return json.load(f)

def get_machine_url(machine_id: str | None) -> str:
    machines = _load_machines()
    if machine_id is None:
        machine_id = machines.get("default", next(
            k for k in machines if k != "default"
        ))
    entry = machines.get(machine_id)
    if entry is None:
        available = [k for k in machines if k != "default"]
        raise MCPClientError(
            f"Máquina desconocida: '{machine_id}'. Disponibles: {available}"
        )
    # Soporta tanto string (formato anterior) como dict (formato nuevo)
    return entry["url"] if isinstance(entry, dict) else entry

class MCPClientError(Exception):
    """Error al comunicarse con el servidor MCP."""


async def _send_scpi_command_async(command: str, machine_id: str | None = None) -> str:
    url = get_machine_url(machine_id)
    try:
        async with streamable_http_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    "send_scpi_command",
                    {"command": command},
                )
    except Exception as exc:
        raise MCPClientError(
            f"Error al invocar send_scpi_command sobre MCP en {url}: {exc}"
        ) from exc

    if not result.content:
        raise MCPClientError("La tool send_scpi_command no devolvió contenido.")

    content = result.content[0]
    if not hasattr(content, "text"):
        raise MCPClientError(f"Formato de respuesta MCP no soportado: {result.content}")

    return content.text.strip()


def send_scpi_command(command: str, machine_id: str | None = None) -> str:
    return asyncio.run(_send_scpi_command_async(command, machine_id))