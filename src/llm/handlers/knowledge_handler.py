from __future__ import annotations

import re

from llm.clients.ollama_client import ask_llm
from llm.memory.conversation_history import conversation_history
from llm.memory.session_log import session_log
from llm.knowledge.command_catalog import COMMAND_CATALOG, get_command_info
from llm.knowledge.context_builder import build_knowledge_payload
from llm.knowledge.formatters import format_command_info_es
from llm.knowledge.query_classifier import classify


KNOWLEDGE_SYSTEM_PROMPT = """
Eres un asistente técnico especializado en el equipo Hexylon de Gsertel.

Tus capacidades son:

1. EJECUTAR COMANDOS SCPI — puedes enviar comandos al equipo y devolver la respuesta.
   Ejemplos: medir potencia, frecuencia, BER, MER, C/N, nivel de señal, estado de lock.

2. PROGRAMAR TAREAS — puedes lanzar mediciones periódicas automáticas con:
   - intervalo y duración configurables
   - condiciones de alerta (notificar si un valor supera un umbral)
   - condiciones de parada automática
   - guardado de resultados en CSV

3. GESTIONAR TAREAS — puedes listar las tareas activas y cancelarlas.

4. ANALIZAR Y GRAFICAR — puedes analizar los CSV generados por las tareas
   y generar gráficas de los resultados.

5. RESPONDER PREGUNTAS TÉCNICAS — puedes explicar qué hace un comando SCPI,
   su sintaxis, qué devuelve, sus restricciones y su área funcional.
   
6. CÓMO LANZAR UNA TAREA — el usuario puede programar mediciones periódicas
   usando lenguaje natural. Ejemplos de frases válidas:

   - "mide la potencia cada 5 segundos durante 20 minutos"
   - "registra POW y MER cada minuto durante 2 horas"
   - "mide el BER cada 30 segundos durante 1 hora y avísame si supera 1E-4"
   - "mide CBER cada 2 segundos durante 1 hora y para si supera 1E-4"

   El sistema extrae automáticamente: comandos, intervalo, duración,
   condiciones de alerta y condiciones de parada.

Reglas:
- Detecta el idioma del mensaje del usuario y responde siempre en ese mismo idioma.
  Idiomas soportados: español, gallego, inglés. Si no puedes determinarlo, responde en español.
- Responde de forma técnica, clara y precisa.
- Usa el contexto documental proporcionado cuando sea relevante.
- No inventes comandos, sintaxis ni comportamientos no documentados.
- Si la documentación no es suficiente, indícalo explícitamente.
- Responde en markdown válido.
""".strip()


def _safe_ask_llm(messages: list[dict[str, str]], fallback: str) -> str:
    try:
        return ask_llm(messages).strip()
    except Exception as exc:
        print("ERROR_LLM_KNOWLEDGE:", repr(exc))
        return fallback


def _extract_catalog_command(text: str) -> str | None:
    upper = text.upper()

    # Detecta comandos exactos como POW, POW?, MER, MER?, etc.
    for command_name in sorted(COMMAND_CATALOG.keys(), key=len, reverse=True):
        pattern = rf"(?<![A-Z0-9_]){re.escape(command_name)}\??(?![A-Z0-9_])"

        if re.search(pattern, upper):
            return command_name

    return None


def handle_knowledge(user_input: str, normalized: str) -> str:
    session_log.log_knowledge_query(
        user_input=user_input,
        query_type="knowledge",
    )

    result = classify(normalized)

    if result.query_type in (
        "exact_command",
        "metric_definition",
        "unsupported",
    ):
        command_name = _extract_catalog_command(normalized)

        if command_name:
            command = get_command_info(command_name)
            if command:
                return format_command_info_es(command)

        return (
            "## Comando no encontrado\n\n"
            "- No se ha encontrado un comando documentado en el catálogo para esta consulta.\n"
            "- Indica explícitamente el comando SCPI, por ejemplo: `POW?`, `MER?` o `FREQ?`."
        )

    payload = build_knowledge_payload(normalized, mode="knowledge")

    messages = conversation_history.build_messages(
        system_prompt=KNOWLEDGE_SYSTEM_PROMPT,
        extra_user_content=f"Contexto documental:\n{payload['context']}",
    )

    return _safe_ask_llm(
        messages,
        fallback=(
            "## Consulta documental\n\n"
            "- No se ha podido completar la respuesta mediante LLM.\n"
            "- El contexto documental fue localizado, pero la interpretación automática no está disponible temporalmente.\n\n"
            "## Acción recomendada\n\n"
            "- Reintenta la consulta o especifica el comando SCPI concreto."
        ),
    )