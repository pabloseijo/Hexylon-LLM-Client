from llm.clients.ollama_client import ask_llm


def main() -> None:
    response = ask_llm(
        [
            {"role": "system", "content": "Responde únicamente con OK."},
            {"role": "user", "content": "Prueba de conexión."},
        ]
    )
    print(response)


if __name__ == "__main__":
    main()