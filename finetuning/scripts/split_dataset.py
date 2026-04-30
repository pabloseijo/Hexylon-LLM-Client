import json
import random
from pathlib import Path

INPUT = Path("finetuning/datasets/hexylon_scpi_sft.jsonl")
TRAIN = Path("finetuning/datasets/train.jsonl")
VAL = Path("finetuning/datasets/val.jsonl")


def main():
    data = [json.loads(l) for l in INPUT.open()]
    random.shuffle(data)

    split = int(len(data) * 0.9)

    train = data[:split]
    val = data[split:]

    with TRAIN.open("w") as f:
        for row in train:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with VAL.open("w") as f:
        for row in val:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Train: {len(train)}")
    print(f"Val: {len(val)}")


if __name__ == "__main__":
    main()