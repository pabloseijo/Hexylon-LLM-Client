"""
Modo chat local de desarrollo para probar el comportamiento del sistema
sin necesidad de conexión real con MCP ni Hexylon.

Este script muestra únicamente la respuesta final generada.
"""

from llm.core.scpi_generator import generate_response


def main() -> None:
    print("Hexylon LLM Dev Chat")
    print("Escribe 'exit' para salir.\n")

    while True:
        user_input = input(">>> ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        response = generate_response(user_input)
        print(response)
        print()


if __name__ == "__main__":
    main()