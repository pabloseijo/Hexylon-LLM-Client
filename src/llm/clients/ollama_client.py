import os
from typing import Any

import requests


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.115.0.71:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
REQUEST_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))


class OllamaClientError(Exception):
    """Error al comunicarse con Ollama."""


session = requests.Session()
session.trust_env = False


def ask_llm(messages: list[dict[str, str]], fmt: dict[str, Any] | None = None) -> str:
    
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "num_ctx": 2048,
        },
    }
    
    if fmt is not None:
        payload["format"] = fmt

    try:
        response = session.post(
            OLLAMA_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise OllamaClientError(
            f"Error comunicando con Ollama en {OLLAMA_URL}: {exc}"
        ) from exc

    if not response.ok:
        raise OllamaClientError(
            f"Ollama devolvió HTTP {response.status_code}: {response.text}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise OllamaClientError("La respuesta de Ollama no es JSON válido.") from exc

    try:
        return data["message"]["content"].strip()
    except KeyError as exc:
        raise OllamaClientError(
            f"Formato de respuesta inesperado de Ollama: {data}"
        ) from exc