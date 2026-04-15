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

# Umbral mínimo de keywords coincidentes para considerar un único candidato
# como "alta confianza" en la detección heurística.
HIGH_CONFIDENCE_MATCH_THRESHOLD = 2

# Nombres de comandos que corresponden a métricas de señal puras.
# Se usan para clasificar preguntas del tipo "qué es el MER".
METRIC_COMMANDS: frozenset[str] = frozenset({
    "POW", "CN", "VA", "MER", "CBER", "VBER", "BCHBER",
    "LKM", "PER", "SER", "HUM", "CSO",
    "PREBER", "POSTBER", "PRELDPCBER", "PREBCHBER",
    "MSCBER", "FICBER",
    "CBERA", "VBERA", "CBERB", "VBERB", "CBERC", "VBERC",
    "CNBOOT", "OPT_POW", "OPT_POW_1310", "OPT_POW_1490", "OPT_POW_1550",
    "ECHOES",
})

# Marcadores lexicales que indican pregunta "cómo hacer algo".
HOW_TO_MARKERS: tuple[str, ...] = (
    "cómo",
    "como",
    "de qué forma",
    "de que forma",
    "de qué manera",
    "de que manera",
    "cómo puedo",
    "como puedo",
    "cómo se",
    "como se",
    "pasos para",
    "procedimiento",
    "proceso para",
)

# Marcadores lexicales que indican pregunta sobre área funcional amplia.
TOPIC_MARKERS: tuple[str, ...] = (
    "qué comandos",
    "que comandos",
    "comandos para",
    "comandos de",
    "opciones de",
    "opciones para",
    "qué opciones",
    "que opciones",
    "qué hay para",
    "que hay para",
    "área de",
    "area de",
    "funcionalidades",
    "capacidades",
    "qué puedo hacer con",
    "que puedo hacer con",
)

# Marcadores de consulta general sobre la API o el sistema.
BROAD_KNOWLEDGE_MARKERS: tuple[str, ...] = (
    "qué puedes hacer",
    "que puedes hacer",
    "qué comandos existen",
    "que comandos existen",
    "cómo funciona",
    "como funciona",
    "para qué sirve el hexylon",
    "para que sirve el hexylon",
    "qué es hexylon",
    "que es hexylon",
    "qué es el hexylon",
    "que es el hexylon",
    "ayuda",
    "help",
    "quién eres",
    "quien eres",
    "qué eres",
    "que eres",
    "tu función",
    "tu funcion",
    "resumen de la api",
    "overview",
)

# Patrones que sugieren que el usuario está fuera del dominio.
OUT_OF_DOMAIN_MARKERS: tuple[str, ...] = (
    "receta",
    "tiempo",
    "clima",
    "deporte",
    "película",
    "pelicula",
    "música",
    "musica",
    "política",
    "politica",
    "historia de",
    "cuéntame un chiste",
    "cuentame un chiste",
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
        Indicador de confianza: 'high' cuando se detectó por nombre explícito
        o match heurístico fuerte; 'low' en caso contrario.
    reason:
        Descripción interna del motivo de clasificación. Útil para depuración.
    """
    query_type: QueryType
    matched_command: str | None
    confidence: Literal["high", "low"]
    reason: str


def _extract_explicit_command(text: str) -> str | None:
    """
    Busca en el texto el nombre de un comando SCPI documentado de forma
    explícita (p. ej. "FREQ", "RBW?", "OPT_POW_1310").

    La búsqueda es insensible a mayúsculas y tolera un '?' final.
    """
    # Ordenar por longitud descendente para que OPT_POW_1310 tenga preferencia
    # sobre OPT_POW cuando ambas aparecen en el texto.
    from llm.knowledge.command_catalog import COMMAND_CATALOG
    sorted_names = sorted(COMMAND_CATALOG.keys(), key=len, reverse=True)

    normalized = text.upper()
    for name in sorted_names:
        pattern = rf"(?<![A-Z0-9_]){re.escape(name)}\??(?![A-Z0-9_])"
        if re.search(pattern, normalized):
            return name
    return None


def _score_candidates(normalized_input: str) -> list[tuple[str, int]]:
    """
    Devuelve la lista de comandos candidatos con su número de keywords
    coincidentes, ordenados de mayor a menor score.
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

    El orden de evaluación es:
    1. Detección fuera de dominio  →  unsupported
    2. Nombre de comando explícito →  exact_command (high confidence)
    3. Heurística de alta confianza (1 candidato fuerte) → exact_command/metric
    4. Marcadores how_to          →  how_to
    5. Marcadores topic           →  topic
    6. Marcadores broad_knowledge →  broad_knowledge
    7. Candidato único con score bajo → topic (low confidence)
    8. Fallback                   →  broad_knowledge (low confidence)
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

    # 3. Heurística de alta confianza: un único candidato dominante
    scored = _score_candidates(normalized)
    if scored:
        top_command, top_score = scored[0]
        is_dominant = (
            len(scored) == 1
            or top_score >= HIGH_CONFIDENCE_MATCH_THRESHOLD
            and (len(scored) < 2 or top_score > scored[1][1])
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

    # 4. Marcadores how_to
    if any(marker in normalized for marker in HOW_TO_MARKERS):
        # Si hay candidatos, el how_to es sobre un comando/área concreto
        top = scored[0][0] if scored else None
        return ClassificationResult(
            query_type="how_to",
            matched_command=top,
            confidence="high" if top else "low",
            reason="how_to_marker_matched",
        )

    # 5. Marcadores topic
    if any(marker in normalized for marker in TOPIC_MARKERS):
        top = scored[0][0] if scored else None
        return ClassificationResult(
            query_type="topic",
            matched_command=top,
            confidence="high" if scored else "low",
            reason="topic_marker_matched",
        )

    # 6. Marcadores broad_knowledge
    if any(marker in normalized for marker in BROAD_KNOWLEDGE_MARKERS):
        return ClassificationResult(
            query_type="broad_knowledge",
            matched_command=None,
            confidence="high",
            reason="broad_knowledge_marker_matched",
        )

    # 7. Candidato único con score bajo → tratarlo como topic
    if len(scored) == 1:
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