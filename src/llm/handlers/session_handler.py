from __future__ import annotations
from llm.clients.ollama_client import ask_llm
from llm.memory.conversation_history import conversation_history
from llm.memory.session_log import session_log, EventType
from llm.memory.task_history import task_history

SESSION_INTERPRETER_PROMPT = """
Eres un asistente técnico del sistema Hexylon LLM.
Responde preguntas sobre el estado actual de la sesión de forma clara,
estructurada y en español.
Reglas obligatorias:
- Usa markdown válido.
- Usa encabezados con ##.
- Usa listas con -.
- Resalta elementos importantes con **negrita**.
- No devuelvas logs crudos.
- Detecta el idioma del usuario y responde en ese idioma.
""".strip()

CAPABILITIES_PROMPT = """
Eres un asistente técnico del equipo Hexylon de Gsertel.

Cuando el usuario pregunte cómo funciona el sistema, qué puedes hacer,
o cómo lanzar tareas, responde explicando exactamente esto:

## Qué puedo hacer

- **Ejecutar comandos SCPI**: envío comandos al equipo y devuelvo la respuesta.
  Ejemplos: "mide la potencia", "dame la frecuencia", "cuál es el MER"

- **Lanzar tareas de medición periódica**: programo mediciones automáticas.
  Para lanzar una tarea usa frases como:
  - "mide la potencia cada 5 segundos durante 20 minutos"
  - "registra POW y MER cada minuto durante 2 horas"
  - "mide el CBER cada 30 segundos durante 1 hora y para si supera 1E-4"
  - "mide MER cada 5 segundos durante 10 minutos y avísame si baja de 20 dB"

- **Gestionar tareas activas**:
  - "qué tareas hay activas"
  - "cancela la tarea"

- **Analizar y graficar resultados**:
  - "analiza los resultados de la última tarea"
  - "grafica la evolución del MER"

- **Responder preguntas técnicas** sobre comandos SCPI, su sintaxis y comportamiento.

Reglas:
- Responde en español salvo que el usuario escriba en otro idioma.
- Detecta el idioma del usuario y responde en ese idioma.
- Usa markdown válido.
""".strip()

HELP_MARKERS = (
    "cómo lanzo", "como lanzo",
    "cómo programo", "como programo",
    "cómo ejecuto", "como ejecuto",
    "cómo lanzar", "como lanzar",
    "cómo mido", "como mido",
    "cómo puedo medir", "como puedo medir",
    "cómo se lanza", "como se lanza",
    "cómo uso", "como uso",
    "qué puedes hacer", "que puedes hacer",
    "cuáles son tus funciones", "cuales son tus funciones",
    "qué eres", "que eres",
    "para qué sirves", "para que sirves",
    "ayuda", "help",
    "cómo funciona", "como funciona",
    "qué sabes hacer", "que sabes hacer",
)


def handle_session_question(user_input: str) -> str:
    text = user_input.lower()

    session_log.log(
        EventType.SESSION_QUESTION,
        f"Pregunta sobre sesión: {user_input[:80]}",
        data={"user_input": user_input},
    )

    # Preguntas sobre capacidades y uso del sistema
    if any(marker in text for marker in HELP_MARKERS):
        messages = conversation_history.build_messages(
            system_prompt=CAPABILITIES_PROMPT,
            extra_user_content=user_input,
        )
        try:
            return ask_llm(messages).strip()
        except Exception as exc:
            print("ERROR_SESSION_LLM:", repr(exc))
            return (
                "## Qué puedo hacer\n\n"
                "- Ejecutar comandos SCPI: *mide la potencia*, *dame la frecuencia*\n"
                "- Lanzar tareas: *mide la potencia cada 5 segundos durante 20 minutos*\n"
                "- Gestionar tareas: *qué tareas hay activas*, *cancela la tarea*\n"
                "- Analizar resultados: *analiza los resultados de la última tarea*\n"
                "- Responder preguntas técnicas sobre la API SCPI\n"
            )

    # Preguntas sobre el estado de la sesión
    if any(marker in text for marker in (
        "historial", "hemos ejecutado", "hemos medido", "tareas anteriores",
    )):
        context = task_history.build_history_summary()
    else:
        context = session_log.build_session_summary()

    messages = conversation_history.build_messages(
        system_prompt=SESSION_INTERPRETER_PROMPT,
        extra_user_content=f"Contexto de la sesión:\n{context}",
    )
    try:
        return ask_llm(messages).strip()
    except Exception as exc:
        print("ERROR_SESSION_LLM:", repr(exc))
        return (
            "## Estado de la sesión\n\n"
            "- No se ha podido generar la respuesta.\n\n"
            f"## Contexto\n\n{context}\n"
        )