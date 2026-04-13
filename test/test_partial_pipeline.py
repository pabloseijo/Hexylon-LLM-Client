from llm.core.scpi_generator import generate_scpi
from llm.clients.mcp_client import send_scpi_command


def main() -> None:
    user_input = "¿Cuál es la frecuencia actual?"

    scpi = generate_scpi(user_input)
    print(f"SCPI generado: {scpi}")

    response = send_scpi_command(scpi)
    print(f"Respuesta Hexylon: {response}")


if __name__ == "__main__":
    main()