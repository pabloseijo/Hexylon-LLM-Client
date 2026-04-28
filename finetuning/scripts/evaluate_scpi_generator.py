import json
import time
from pathlib import Path

from llm.core.scpi_generator import generate_scpi


CASES_FILE = Path("finetuning/eval/eval_scpi_cases.jsonl")


def main() -> None:
    total = 0
    ok = 0
    total_time = 0.0

    with CASES_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            total += 1
            case = json.loads(line)
            user_input = case["input"]
            expected = case["expected"]

            start = time.perf_counter()
            generated = generate_scpi(user_input)
            elapsed = time.perf_counter() - start
            total_time += elapsed

            passed = generated == expected
            ok += int(passed)

            status = "OK" if passed else "FAIL"
            print(f"[{status}] {user_input} ({elapsed:.2f}s)")
            print(f"  expected: {expected}")
            print(f"  generated: {generated}")
            print()

    avg = total_time / total if total else 0

    print(f"Resultado: {ok}/{total} correctos")
    print(f"Tiempo total: {total_time:.2f}s")
    print(f"Tiempo medio: {avg:.2f}s/caso")


if __name__ == "__main__":
    main()