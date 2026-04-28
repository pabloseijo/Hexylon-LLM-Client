# finetuning/scripts/benchmark_ollama.py

import time

from llm.clients.ollama_client import ask_llm

messages = [
    {
        "role": "system",
        "content": "Devuelve únicamente MER?",
    },
    {
        "role": "user",
        "content": "Dame el MER actual",
    },
]

start = time.perf_counter()
response = ask_llm(messages)
elapsed = time.perf_counter() - start

print("Respuesta:", response)
print(f"Tiempo: {elapsed:.2f}s")