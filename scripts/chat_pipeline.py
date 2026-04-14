"""
Modo chat para probar el pipeline completo contra MCP y Hexylon.

Este script:
- recibe una petición en lenguaje natural
- ejecuta el pipeline completo
- muestra únicamente la respuesta final
"""

from llm.core.pipeline import run_pipeline


def main() -> None:
    print("Hexylon LLM Pipeline Chat")
    print("Escribe 'exit' para salir.\n")

    while True:
        user_input = input(">>> ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        try:
            response = run_pipeline(user_input)
            print(response)
        except Exception as exc:
            print(f"ERROR: {exc}")

        print()


if __name__ == "__main__":
    main()