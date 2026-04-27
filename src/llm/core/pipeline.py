import re
from typing import Any

from llm.clients.mcp_client import send_scpi_command
from llm.clients.ollama_client import ask_llm
from llm.core.intent_router import route_intent
from llm.core.scpi_generator import generate_scpi
from llm.memory.conversation_history import conversation_history
from llm.memory.session_memory import session_memory
from llm.memory.session_log import EventType, session_log
from llm.memory.task_history import task_history
from llm.tasks.task_executor import cancel_task, get_active_tasks, launch_task
from llm.handlers.knowledge_handler import handle_knowledge
from llm.handlers.session_handler import handle_session_question
from llm.tasks.task_models import TaskResult, TaskStatus
from llm.tasks.task_planner import try_plan_task
from llm.parsing.main_parser import parse_input
from llm.handlers.analysis_handler import handle_analysis
from llm.handlers.task_handler import (
    handle_launch_task,
    handle_cancel_task,
    handle_list_tasks,
)

# ---------------------------------------------------------------------------
# Prompts del sistema
# ---------------------------------------------------------------------------

SCPI_COMMAND_SYSTEM_PROMPT = """
Eres un generador de comandos SCPI para un equipo Hexylon.

Tu tarea es convertir una petición del usuario en un único comando SCPI válido
cuando la intención sea operativa o de consulta del equipo.

Reglas obligatorias:
- Devuelve únicamente el comando SCPI.
- No añadas explicaciones.
- No añadas comillas.
- No añadas texto antes ni después.
- No devuelvas JSON.
- No inventes comandos.
- Usa únicamente comandos documentados para Hexylon.
- Si no puedes determinar el comando con seguridad, responde exactamente: UNKNOWN.
""".strip()


KNOWLEDGE_SYSTEM_PROMPT = """
Eres un asistente técnico especializado en la API SCPI del equipo Hexylon.

Tu tarea es responder preguntas técnicas sobre:
- qué hace un comando
- qué devuelve
- qué sintaxis tiene
- qué restricciones tiene
- qué comandos están relacionados con una capacidad concreta
- qué opciones ofrece una determinada área funcional de la API

Reglas obligatorias:
- Responde en español.
- Responde de forma técnica, clara y precisa.
- Usa exclusivamente el contexto documental proporcionado.
- No inventes comandos, sintaxis, restricciones ni comportamientos.
- No devuelvas únicamente el comando SCPI salvo que el usuario pida explícitamente generarlo o ejecutarlo.
- Si la documentación no es suficiente para responder con seguridad, indícalo explícitamente.

Formato de salida obligatorio:
- La respuesta DEBE estar en markdown válido.
- Debes usar encabezados con ##.
- Debes usar listas con -.
- Debes usar **negrita** para conceptos clave.
- Debes usar bloques de código para comandos SCPI.
- No escribas texto plano estructurado sin markdown.

Plantilla obligatoria cuando aplique:

## Elemento consultado
- **Nombre**: ...

## Descripción
- ...

## Sintaxis o comandos relacionados

```scpi
COMANDO?
```

## Respuesta o comportamiento
- ...

## Restricciones o notas
- ...

Si falta información para alguna sección, indícalo dentro de esa sección.
""".strip()


SESSION_INTERPRETER_PROMPT = """
Eres un asistente técnico del sistema Hexylon LLM.

Responde preguntas sobre el estado actual de la sesión de forma natural y
conversacional, como un colaborador que conoce bien lo que está pasando.

Reglas obligatorias:
- Responde en español.
- Usa markdown ligero si mejora la legibilidad.
- Puedes usar listas con - cuando describas estado o eventos.
- Puedes usar **negrita** para resaltar elementos importantes.
- No enumeres logs crudos.
- No respondas en texto plano largo sin estructura.
""".strip()


ANALYSIS_INTERPRETER_PROMPT = """
Eres un asistente técnico especializado en análisis de señales RF del equipo Hexylon.

Analiza los resultados de medición proporcionados y responde de forma técnica
y precisa.

Reglas obligatorias:
- Responde en markdown válido.
- Usa exactamente estas secciones:
  ## Resumen
  ## Valores clave
  ## Análisis
  ## Conclusión
- Usa listas con - dentro de las secciones.
- Usa **negrita** para métricas y valores importantes.
- No respondas en texto plano corrido.

Si una sección no aplica, indícalo dentro de ella.
""".strip()


COMMAND_INTERPRETER_PROMPT = """
Eres un asistente técnico del equipo Hexylon.

Tienes acceso al historial de la conversación y a la última respuesta del equipo.
Interpreta la respuesta de forma clara y natural en español.

Reglas obligatorias:
- Responde en markdown válido.
- Usa al menos un encabezado con ##.
- Usa listas con - cuando describas valores.
- Resalta valores medidos con **negrita**.
- Si aparece un comando, muéstralo en bloque de código.
- No respondas en texto plano sin estructura.

Plantilla orientativa:

## Resultado
- **Métrica**: ...
- **Valor**: ...

## Interpretación
- ...
""".strip()

# ---------------------------------------------------------------------------
# Callbacks y handlers
# ---------------------------------------------------------------------------

def _safe_ask_llm(messages: list[dict[str, str]], fallback: str, context: str) -> str:
    try:
        return ask_llm(messages).strip()
    except Exception as exc:
        print(f"ERROR_LLM_{context}:", repr(exc))
        return fallback

# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def run_pipeline(user_input: str) -> dict[str, Any] | str:
    conversation_history.add_user_message(user_input)

    parsed = parse_input(user_input)
    normalized = parsed.normalized_input

    if parsed.intent in ("analysis", "plot"):
        response = handle_analysis(user_input)

        if isinstance(response, dict):
            conversation_history.add_assistant_message(response["message"])
            return response

        conversation_history.add_assistant_message(response)
        return response

    if parsed.intent == "session_question":
        response = handle_session_question(user_input)
        conversation_history.add_assistant_message(response)
        return response

    if parsed.intent == "cancel_task":
        response = handle_cancel_task(user_input)
        conversation_history.add_assistant_message(response)
        return response

    if parsed.intent == "list_tasks":
        response = handle_list_tasks()
        conversation_history.add_assistant_message(response)
        return response

    if parsed.intent == "launch_task":
        response = handle_launch_task(user_input)

        if isinstance(response, dict):
            conversation_history.add_assistant_message(response["message"])
            return response

        conversation_history.add_assistant_message(response)
        return response

    routed_intent = route_intent(normalized)

    if routed_intent == "knowledge":
        response = handle_knowledge(user_input, normalized)
        conversation_history.add_assistant_message(response)
        return response

    scpi_command = generate_scpi(normalized)

    if scpi_command == "UNKNOWN":
        messages = conversation_history.build_messages(
            system_prompt=COMMAND_INTERPRETER_PROMPT,
        )
        response = _safe_ask_llm(
            messages,
            fallback=(
                "## Petición no reconocida\n\n"
                "- No he podido determinar un comando SCPI válido para esta petición.\n"
                "- Tampoco ha sido posible generar una respuesta interpretativa mediante LLM.\n\n"
                "## Acción recomendada\n\n"
                "- Indica explícitamente la métrica, comando o tarea que quieres consultar."
            ),
            context="UNKNOWN_COMMAND",
        )
        conversation_history.add_assistant_message(response)
        return response

    session_log.log_command_sent(scpi_command=scpi_command, user_input=user_input)
    session_memory.set_last_metric(scpi_command.rstrip("?"))

    raw_response = send_scpi_command(scpi_command)

    messages = conversation_history.build_messages(
        system_prompt=COMMAND_INTERPRETER_PROMPT,
        extra_user_content=(
            f"Comando ejecutado: {scpi_command}\n"
            f"Respuesta del equipo: {raw_response}"
        ),
    )
    response = _safe_ask_llm(
        messages,
        fallback=(
            "## Respuesta del equipo\n\n"
            f"- **Comando ejecutado**: `{scpi_command}`\n"
            f"- **Respuesta cruda**: `{raw_response}`\n\n"
            "## Interpretación\n\n"
            "- No se ha podido interpretar la respuesta mediante LLM.\n"
            "- Se muestra la respuesta directa del equipo Hexylon."
        ),
        context="SCPI_RESPONSE",
    )
    conversation_history.add_assistant_message(response)
    return response