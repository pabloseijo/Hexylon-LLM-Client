"""
Clasificador de consultas para la rama knowledge del cliente LLM de Hexylon.

Determina el tipo de consulta entrante para enrutar hacia la respuesta más
determinista posible, reduciendo la dependencia de generación libre del LLM.

Tipos de consulta soportados:

- exact_command
    El usuario pregunta sobre un comando SCPI concreto e identificable.
    Ejemplos: "qué hace FREQ", "sintaxis de RBW", "qué devuelve MEAS"

- metric_definition
    El usuario pregunta qué es una métrica de señal concreta.
    Ejemplos: "qué es el MER", "qué significa CBER", "explícame el C/N"

- how_to
    El usuario pregunta cómo realizar una acción concreta.
    Ejemplos: "cómo cambio de banda", "cómo selecciono un servicio"

- topic
    El usuario pregunta sobre un área funcional amplia sin apuntar a un
    comando concreto.
    Ejemplos: "qué comandos hay para el espectro", "opciones de perfiles"

- broad_knowledge
    Pregunta general sobre la API o el equipo sin foco específico.
    Ejemplos: "qué puedes hacer", "qué comandos existen", "cómo funciona"

- unsupported
    Consulta fuera del dominio de la API Hexylon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from llm.knowledge.command_catalog import command_exists
from llm.knowledge.command_selector import (
    COMMAND_KEYWORDS,
    _normalize_text,
    _contains_keyword,
    select_candidate_commands,
)

QueryType = Literal[
    "exact_command",
    "metric_definition",
    "how_to",
    "topic",
    "broad_knowledge",
    "unsupported",
]

HIGH_CONFIDENCE_MATCH_THRESHOLD = 2

METRIC_COMMANDS: frozenset[str] = frozenset({
    "POW", "CN", "VA", "MER", "CBER", "VBER", "BCHBER",
    "LKM", "PER", "SER", "HUM", "CSO",
    "PREBER", "POSTBER", "PRELDPCBER", "PREBCHBER",
    "MSCBER", "FICBER",
    "CBERA", "VBERA", "CBERB", "VBERB", "CBERC", "VBERC",
    "CNBOOT", "OPT_POW", "OPT_POW_1310", "OPT_POW_1490", "OPT_POW_1550",
    "ECHOES",
})

# Marcadores how_to — evaluados ANTES de la heurística de comando único
HOW_TO_MARKERS: tuple[str, ...] = (
    "como cambio",
    "como selecciono",
    "como configuro",
    "como anado",
    "como subo",
    "como bajo",
    "como activo",
    "como desactivo",
    "como uso",
    "como utilizo",
    "como puedo",
    "como se",
    "cómo cambio",
    "cómo selecciono",
    "cómo configuro",
    "cómo añado",
    "cómo subo",
    "cómo bajo",
    "cómo activo",
    "cómo desactivo",
    "cómo uso",
    "cómo utilizo",
    "cómo puedo",
    "cómo se",
    "de que forma",
    "de qué forma",
    "de que manera",
    "de qué manera",
    "pasos para",
    "procedimiento",
    "proceso para",
)

# Marcadores topic — evaluados ANTES de la heurística de comando único
TOPIC_MARKERS: tuple[str, ...] = (
    "que comandos hay",
    "qué comandos hay",
    "que comandos existen",
    "qué comandos existen",
    "comandos para",
    "comandos de",
    "que opciones hay",
    "qué opciones hay",
    "opciones de",
    "opciones para",
    "que hay para",
    "qué hay para",
    "area de",
    "área de",
    "funcionalidades",
    "capacidades",
    "que puedo hacer con",
    "qué puedo hacer con",
)

BROAD_KNOWLEDGE_MARKERS: tuple[str, ...] = (
    "que puedes hacer",
    "qué puedes hacer",
    "como funciona",
    "cómo funciona",
    "para que sirve el hexylon",
    "para qué sirve el hexylon",
    "que es hexylon",
    "qué es hexylon",
    "que es el hexylon",
    "qué es el hexylon",
    "ayuda",
    "help",
    "quien eres",
    "quién eres",
    "que eres",
    "qué eres",
    "tu funcion",
    "tu función",
    "resumen de la api",
    "overview",
)

OUT_OF_DOMAIN_MARKERS: tuple[str, ...] = (
    "receta",
    "tiempo hace",
    "clima",
    "deporte",
    "pelicula",
    "película",
    "musica",
    "música",
    "politica",
    "política",
    "historia de",
    "chiste",
    "mundial",
    "futbol",
    "fútbol",
    "baloncesto",
    "tenis",
    "cocina",
)


@dataclass(frozen=True)
class ClassificationResult:
    """
    Resultado del clasificador de consultas knowledge.

    Attributes
    ----------
    query_type:
        Categoría detectada para la consulta entrante.
    matched_command:
        Nombre del comando identificado, si aplica. None en caso contrario.
    confidence:
        'high' cuando se detectó por nombre explícito o match fuerte;
        'low' en caso contrario.
    reason:
        Motivo de clasificación. Útil para depuración.
    """
    query_type: QueryType
    matched_command: str | None
    confidence: Literal["high", "low"]
    reason: str


def _extract_explicit_command(text: str) -> str | None:
    from llm.knowledge.command_catalog import COMMAND_CATALOG
    from llm.knowledge.generator_command_catalog import GENERATOR_COMMAND_CATALOG

    normalized = text.upper()

    # Buscar primero en catálogo Hexylon
    sorted_names = sorted(COMMAND_CATALOG.keys(), key=len, reverse=True)
    for name in sorted_names:
        pattern = rf"(?<![A-Z0-9_]){re.escape(name)}\??(?![A-Z0-9_])"
        if re.search(pattern, normalized):
            return name

    # Buscar en catálogo del generador
    sorted_gen = sorted(GENERATOR_COMMAND_CATALOG.keys(), key=len, reverse=True)
    for name in sorted_gen:
        clean = name.lstrip("*").replace(":", "").replace("[", "").replace("]", "")
        if not clean:
            continue
        pattern = rf"(?<![A-Z0-9_]){re.escape(clean)}\??(?![A-Z0-9_])"
        if re.search(pattern, normalized):
            return f"GEN:{name}"

    return None


def _score_candidates(normalized_input: str) -> list[tuple[str, int]]:
    """
    Devuelve candidatos de comandos con su score de keywords, ordenados
    de mayor a menor.
    """
    scored: list[tuple[str, int]] = []
    for command_name, keywords in COMMAND_KEYWORDS.items():
        count = sum(
            1 for kw in keywords if _contains_keyword(normalized_input, kw)
        )
        if count > 0:
            scored.append((command_name, count))
    scored.sort(key=lambda x: -x[1])
    return scored


def classify(user_input: str) -> ClassificationResult:
    """
    Clasifica una consulta de la rama knowledge en su tipo más específico.

    Orden de evaluación:
    1. Fuera de dominio              →  unsupported
    2. Nombre de comando explícito   →  exact_command / metric_definition (high)
    3. Marcadores how_to             →  how_to   (ANTES que heurística)
    4. Marcadores topic              →  topic    (ANTES que heurística)
    5. Heurística candidato dominante → exact_command / metric_definition
    6. Marcadores broad_knowledge    →  broad_knowledge
    7. Candidato único score bajo    →  topic (low)
    8. Fallback                      →  broad_knowledge (low)

    Los pasos 3 y 4 se evalúan antes que el 5 para evitar que consultas
    como "como cambio de banda en modo radio" sean capturadas por la
    heurística de keywords (que detectaría MODE) en lugar de clasificarse
    correctamente como how_to.
    """
    normalized = _normalize_text(user_input)

    # 1. Fuera de dominio
    if any(marker in normalized for marker in OUT_OF_DOMAIN_MARKERS):
        return ClassificationResult(
            query_type="unsupported",
            matched_command=None,
            confidence="low",
            reason="out_of_domain_marker_matched",
        )

    # 2. Nombre de comando explícito en el texto
    explicit = _extract_explicit_command(user_input)
    if explicit:
        query_type: QueryType = (
            "metric_definition" if explicit in METRIC_COMMANDS else "exact_command"
        )
        return ClassificationResult(
            query_type=query_type,
            matched_command=explicit,
            confidence="high",
            reason=f"explicit_command_name_found:{explicit}",
        )

    # 3. Marcadores how_to — ANTES de la heurística
    if any(marker in normalized for marker in HOW_TO_MARKERS):
        scored = _score_candidates(normalized)
        top = scored[0][0] if scored else None
        return ClassificationResult(
            query_type="how_to",
            matched_command=top,
            confidence="high" if top else "low",
            reason="how_to_marker_matched",
        )

    # 4. Marcadores topic — ANTES de la heurística
    if any(marker in normalized for marker in TOPIC_MARKERS):
        scored = _score_candidates(normalized)
        top = scored[0][0] if scored else None
        return ClassificationResult(
            query_type="topic",
            matched_command=top,
            confidence="high" if scored else "low",
            reason="topic_marker_matched",
        )

    # 5. Heurística de alta confianza: candidato dominante
    scored = _score_candidates(normalized)
    if scored:
        top_command, top_score = scored[0]
        is_dominant = (
            len(scored) == 1
            or (
                top_score >= HIGH_CONFIDENCE_MATCH_THRESHOLD
                and (len(scored) < 2 or top_score > scored[1][1])
            )
        )
        if is_dominant:
            query_type = (
                "metric_definition"
                if top_command in METRIC_COMMANDS
                else "exact_command"
            )
            return ClassificationResult(
                query_type=query_type,
                matched_command=top_command,
                confidence="high",
                reason=f"heuristic_high_confidence:{top_command}(score={top_score})",
            )

    # 6. Marcadores broad_knowledge
    if any(marker in normalized for marker in BROAD_KNOWLEDGE_MARKERS):
        return ClassificationResult(
            query_type="broad_knowledge",
            matched_command=None,
            confidence="high",
            reason="broad_knowledge_marker_matched",
        )

    # 7. Candidato único con score bajo → topic
    if scored and len(scored) == 1:
        return ClassificationResult(
            query_type="topic",
            matched_command=scored[0][0],
            confidence="low",
            reason=f"single_candidate_low_score:{scored[0][0]}",
        )

    # 8. Fallback
    return ClassificationResult(
        query_type="broad_knowledge",
        matched_command=None,
        confidence="low",
        reason="fallback_no_signal",
    )