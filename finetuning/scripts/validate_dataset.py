# finetuning/scripts/validate_dataset.py

import json
from pathlib import Path

DATASET = Path("finetuning/datasets/hexylon_scpi_sft.jsonl")

VALID_ROLES = {"system", "user", "assistant"}


def validate_line(line: str, line_number: int) -> None:
    data = json.loads(line)

    if "messages" not in data:
        raise ValueError(f"Línea {line_number}: falta 'messages'")

    messages = data["messages"]

    if not isinstance(messages, list) or len(messages) < 3:
        raise ValueError(f"Línea {line_number}: 'messages' inválido")

    for message in messages:
        if message.get("role") not in VALID_ROLES:
            raise ValueError(f"Línea {line_number}: role inválido")

        if not isinstance(message.get("content"), str):
            raise ValueError(f"Línea {line_number}: content inválido")


def main() -> None:
    with DATASET.open("r", encoding="utf-8") as file:
        for index, line in enumerate(file, start=1):
            if line.strip():
                validate_line(line, index)

    print("Dataset válido.")


if __name__ == "__main__":
    main()