from .ollama_client import ask_llm

SYSTEM_PROMPT = """
Eres un sistema que genera comandos SCPI.

- SOLO devuelves comandos SCPI
- NO explicas nada
- Si no sabes: UNKNOWN
"""

def generate_scpi(user_input: str) -> str:
    return ask_llm([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ])