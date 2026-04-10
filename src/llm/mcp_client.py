import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# Evitar proxy en llamadas locales
os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"

MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp")


class MCPClientError(Exception):
    """Error al comunicarse con el servidor MCP."""


async def _send_scpi_command_async(command: str) -> str:
    try:
        async with streamable_http_client(MCP_URL) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                result = await session.call_tool(
                    "send_scpi_command",
                    {"command": command},
                )

    except Exception as exc:
        raise MCPClientError(
            f"Error al invocar send_scpi_command sobre MCP en {MCP_URL}: {exc}"
        ) from exc

    if not result.content:
        raise MCPClientError(
            "La tool send_scpi_command no devolvió contenido."
        )

    content = result.content[0]

    if not hasattr(content, "text"):
        raise MCPClientError(
            f"Formato de respuesta MCP no soportado: {result.content}"
        )

    return content.text.strip()


def send_scpi_command(command: str) -> str:
    return asyncio.run(_send_scpi_command_async(command))