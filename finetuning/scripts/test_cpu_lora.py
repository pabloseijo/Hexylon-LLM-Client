from __future__ import annotations

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


BASE_MODEL = "Qwen/Qwen3-0.6B"
LORA_PATH = "finetuning/output/cpu_lora_test"


def build_prompt(user_input: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Eres un generador de comandos SCPI para un equipo Hexylon. "
                "Devuelve únicamente un comando SCPI válido o UNKNOWN. "
                "No añadas explicaciones, markdown ni texto adicional."
            ),
        },
        {"role": "user", "content": user_input},
    ]

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


tokenizer = AutoTokenizer.from_pretrained(LORA_PATH, trust_remote_code=True)

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    trust_remote_code=True,
    torch_dtype=torch.float32,
)

model = PeftModel.from_pretrained(base_model, LORA_PATH)
model.eval()

tests = [
    "Dame el MER actual",
    "Consulta el BER previo",
    "Pon el VBW en 10 KHz",
    "Qué hace CN",
    "Cuéntame un chiste",
]

for test in tests:
    prompt = build_prompt(test)
    inputs = tokenizer(prompt, return_tensors="pt")

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=32,
            do_sample=False,
        )

    generated = tokenizer.decode(
        output[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True,
    ).strip()

    print(f"USER: {test}")
    print(f"MODEL: {generated}")
    print("-" * 60)