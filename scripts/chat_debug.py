"""
Modo chat local de desarrollo para probar la capa de conocimiento y la
generación SCPI sin necesidad de conexión real con MCP ni Hexylon.
"""

from llm.core.scpi_generator import generate_response
from llm.knowledge.context_builder import build_knowledge_payload


def main() -> None:
    print("Hexylon LLM Dev Chat")
    print("Escribe 'exit' para salir.\n")

    while True:
        user_input = input(">>> ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        payload = build_knowledge_payload(user_input)

        print("\n=== COMANDOS SELECCIONADOS ===")
        print(payload["selected_commands"])

        print("\n=== TOPICS SELECCIONADOS ===")
        print(payload["selected_topics"])

        print("\n=== CONTEXTO CONSTRUIDO ===")
        print(payload["context"])

        print("\n=== RESPUESTA ===")
        response = generate_response(user_input)
        print(response)

        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()