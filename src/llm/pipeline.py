from .scpi_generator import generate_scpi
from .interpreter import interpret

# IMPORTANTE: esto debe apuntar a tu cliente MCP real
from mcp_client import send_scpi_command


def run_pipeline(user_input: str):
    scpi = generate_scpi(user_input)

    if scpi == "UNKNOWN":
        return "No se puede determinar comando SCPI"

    raw = send_scpi_command(scpi)
    return interpret(raw)