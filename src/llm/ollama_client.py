import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:0.8b"

def ask_llm(messages):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": messages,
            "stream": False
        }
    )

    response.raise_for_status()
    return response.json()["message"]["content"]