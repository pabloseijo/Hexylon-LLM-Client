from llm.clients.mcp_client import send_scpi_command
from llm.core.interpreter import interpret_response
from llm.core.scpi_generator import detect_intent, generate_response, generate_scpi


def run_pipeline(user_input: str) -> str:
    """
    Ejecuta el flujo completo del sistema.

    - Si la intención es documental, responde usando la capa knowledge y no
      contacta con MCP ni Hexylon.
    - Si la intención es operativa, genera SCPI, lo envía al MCP y después
      interpreta la respuesta del equipo.
    """
    intent = detect_intent(user_input)

    if intent == "knowledge":
        return generate_response(user_input)

    scpi_command = generate_scpi(user_input)

    if scpi_command == "UNKNOWN":
        return "No he podido determinar un comando SCPI válido para esa petición."

    raw_response = send_scpi_command(scpi_command)
    return interpret_response(user_input, scpi_command, raw_response)