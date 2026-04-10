from .ollama_client import ask_llm

def interpret(raw_data: str) -> str:
    return ask_llm([
        {"role": "system", "content": "Interpreta datos SCPI de forma técnica"},
        {"role": "user", "content": raw_data}
    ])