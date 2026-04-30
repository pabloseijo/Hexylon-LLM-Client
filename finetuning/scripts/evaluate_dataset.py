import json
import time
from pathlib import Path

from llm.core.scpi_generator import generate_scpi

DATASET = Path("finetuning/datasets/hexylon_scpi_sft.jsonl")


def main():
    correct = 0
    total = 0
    total_time = 0

    with DATASET.open() as f:
        for line in f:
            row = json.loads(line)

            system = row["messages"][0]["content"]
            user = row["messages"][1]["content"]
            expected = row["messages"][2]["content"]

            # Solo evaluamos COMMAND (no knowledge)
            if "SCPI" not in system:
                continue

            start = time.time()
            generated = generate_scpi(user)
            elapsed = time.time() - start

            total += 1
            total_time += elapsed

            if generated == expected:
                correct += 1
            else:
                print(f"[FAIL] {user}")
                print(f" expected: {expected}")
                print(f" generated: {generated}\n")

    print(f"\nResultado: {correct}/{total}")
    print(f"Accuracy: {correct/total:.2%}")
    print(f"Tiempo medio: {total_time/total:.2f}s")


if __name__ == "__main__":
    main()