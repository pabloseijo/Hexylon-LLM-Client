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

def _format_generator_command_es(info: dict) -> str:
    lines = [
        f"## Comando: `{info['name']}`",
        f"\n**Dispositivo**: R&S SGU100A (Generador de señales)",
        f"\n**Categoría**: {info.get('category', 'N/A')}",
        f"\n## Descripción\n\n{info.get('description', '')}",
    ]
    read_syntax = info.get("read_syntax") or []
    write_syntax = info.get("write_syntax") or []
    if read_syntax or write_syntax:
        lines.append("\n## Sintaxis")
        for s in read_syntax + write_syntax:
            lines.append(f"\n```scpi\n{s}\n```")
    read_response = info.get("read_response")
    if read_response:
        lines.append(f"\n## Respuesta\n\n- {read_response}")
    constraints = info.get("constraints") or []
    if constraints:
        lines.append("\n## Restricciones")
        lines.extend(f"\n- {c}" for c in constraints)
    notes = info.get("notes") or []
    if notes:
        lines.append("\n## Notas")
        lines.extend(f"\n- {n}" for n in notes)
    examples = info.get("examples") or []
    if examples:
        lines.append("\n## Ejemplos")
        lines.extend(f"\n```scpi\n{e}\n```" for e in examples)
    return "".join(lines)

def handle_knowledge(user_input: str, normalized: str) -> str:
    session_log.log_knowledge_query(
        user_input=user_input,
        query_type="knowledge",
    )

    # Si hay verbo operativo claro, redirigir a command_handler
    # evita que "dame la potencia" devuelva la ficha técnica de POW
    operative_verbs = [
        "dame", "mide", "lee", "consulta", "ejecuta",
        "dime", "muéstrame", "muestrame", "obtén", "obten",
        "get", "read",
    ]
    if any(v in normalized.lower() for v in operative_verbs):
        from llm.handlers.command_handler import handle_command
        return handle_command(user_input, normalized)

    # Preguntas sobre el propio asistente
    self_query_markers = [
        "qué puedes hacer", "que puedes hacer",
        "cuáles son tus funciones", "cuales son tus funciones",
        "qué eres", "que eres",
        "quién eres", "quien eres",
        "para qué sirves", "para que sirves",
        "qué sabes hacer", "que sabes hacer",
        "ayuda", "help",
    ]
    if any(marker in normalized.lower() for marker in self_query_markers):
        messages = conversation_history.build_messages(
            system_prompt=KNOWLEDGE_SYSTEM_PROMPT,
            extra_user_content=user_input,
        )
        return _safe_ask_llm(
            messages,
            fallback="Soy un asistente técnico para el equipo Hexylon. Puedo ejecutar comandos SCPI, programar tareas de medición, analizar resultados y responder preguntas técnicas.",
        )

    result = classify(normalized)

    if result.query_type in ("exact_command", "metric_definition", "unsupported"):
        command_name = result.matched_command

        if command_name and command_name.startswith("GEN:"):
            from llm.knowledge.generator_command_catalog import get_generator_command_info
            gen_name = command_name[4:]
            info = get_generator_command_info(gen_name)
            if info:
                return _format_generator_command_es(info)

        elif command_name:
            command = get_command_info(command_name)
            if command:
                return format_command_info_es(command)

    payload = build_knowledge_payload(normalized, mode="knowledge")
    messages = conversation_history.build_messages(
        system_prompt=KNOWLEDGE_SYSTEM_PROMPT,
        extra_user_content=f"Contexto documental:\n{payload['context']}",
    )
    return _safe_ask_llm(
        messages,
        fallback=(
            "## Consulta documental\n\n"
            "- No se ha podido completar la respuesta.\n"
            "- Reintenta la consulta o especifica el comando SCPI concreto."
        ),
    )
    
    