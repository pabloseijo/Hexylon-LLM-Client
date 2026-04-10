from llm.scpi_generator import generate_scpi


def main() -> None:
    queries = [
        "¿Cuál es la frecuencia actual?",
        "Dime la identificación del equipo",
        "¿Está bloqueada la señal?",
        "¿Qué banda está seleccionada?",
        "Muéstrame las medidas actuales",
        "Dime los parámetros actuales",
        "¿Cuál es el perfil actual?",
    ]

    for query in queries:
        scpi = generate_scpi(query)
        print(f"Usuario: {query}")
        print(f"SCPI: {scpi}")
        print("-" * 40)


if __name__ == "__main__":
    main()