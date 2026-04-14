"""
Selector heurístico de topics para la capa de conocimiento de Hexylon.

Este módulo detecta áreas funcionales de la API a partir de lenguaje natural.
Su objetivo es identificar temas amplios relevantes para enriquecer el contexto
del LLM cuando la petición del usuario no apunta solo a un comando concreto,
sino a una capacidad general del sistema.
"""

from __future__ import annotations

import re

from llm.knowledge.topic_catalog import TOPIC_CATALOG


TOPIC_PRIORITY: dict[str, int] = {
    "tuning": 100,
    "input_selection": 95,
    "mode_and_layout": 90,
    "profiles": 85,
    "status_and_identity": 80,
    "measurements_basic": 75,
    "measurements_advanced": 70,
    "echoes_and_optical": 65,
    "spectrum_analyser": 60,
    "services": 55,
    "iptv": 50,
    "utility_and_capture": 45,
}


def _normalize_text(text: str) -> str:
    """
    Normaliza el texto de entrada para facilitar el matching heurístico.

    - convierte a minúsculas
    - elimina símbolos irrelevantes
    - compacta espacios
    """
    normalized = text.lower()
    normalized = re.sub(r"[^\w\s/\-\?\+\.]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _contains_keyword(text: str, keyword: str) -> bool:
    """
    Comprueba si una keyword aparece en el texto normalizado como unidad
    independiente o expresión completa.
    """
    escaped = re.escape(keyword.lower())
    pattern = rf"(?<!\w){escaped}(?!\w)"
    return re.search(pattern, text) is not None


def select_candidate_topics(user_input: str, max_topics: int = 3) -> list[str]:
    """
    Devuelve una lista ordenada de topics candidatos para una petición del usuario.

    El ranking se calcula con dos criterios:
    1. número de keywords del topic que aparecen en la petición
    2. prioridad fija del topic para desempate

    Este selector es determinista y no utiliza LLM.
    """
    normalized = _normalize_text(user_input)
    scored_candidates: list[tuple[str, int, int]] = []

    for topic_name, topic_info in TOPIC_CATALOG.items():
        keywords = topic_info.get("keywords", [])
        match_count = sum(
            1 for keyword in keywords if _contains_keyword(normalized, keyword)
        )

        if match_count == 0:
            continue

        priority = TOPIC_PRIORITY.get(topic_name, 0)
        scored_candidates.append((topic_name, match_count, priority))

    scored_candidates.sort(key=lambda item: (-item[1], -item[2], item[0]))

    return [topic_name for topic_name, _, _ in scored_candidates[:max_topics]]


def explain_topic_selection(user_input: str) -> dict[str, list[str]]:
    """
    Devuelve las keywords que han hecho match por cada topic.

    Esta función es útil para depuración y ajuste del selector.
    """
    normalized = _normalize_text(user_input)
    matches: dict[str, list[str]] = {}

    for topic_name, topic_info in TOPIC_CATALOG.items():
        keywords = topic_info.get("keywords", [])
        matched = [keyword for keyword in keywords if _contains_keyword(normalized, keyword)]

        if matched:
            matches[topic_name] = matched

    return matches