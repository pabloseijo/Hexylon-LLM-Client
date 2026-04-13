from llm.clients.mcp_client import send_scpi_command


def main() -> None:
    response = send_scpi_command("IDN?")
    print(response)


if __name__ == "__main__":
    main()