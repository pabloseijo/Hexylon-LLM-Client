from __future__ import annotations

from typing import Literal

from llm.clients.ollama_client import ask_llm
from llm.knowledge.command_catalog import command_exists
from llm.knowledge.context_builder import build_knowledge_payload

Intent = Literal["command", "knowledge"]


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
- No uses markdown.
- Usa esta estructura de salida siempre que aplique:
  1. Elemento consultado
  2. Descripción
  3. Sintaxis o comandos relacionados
  4. Respuesta o comportamiento
  5. Restricciones o notas
""".strip()


def normalize_command(text: str) -> str:
    """
    Normaliza la salida del modelo y conserva únicamente la primera línea útil.
    """
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return lines[0] if lines else "UNKNOWN"


def extract_command_name(scpi_text: str) -> str:
    """
    Extrae el nombre base del comando SCPI a partir del texto devuelto.

    Ejemplos:
    - 'FREQ?' -> 'FREQ'
    - 'FREQ 594.00MHz' -> 'FREQ'
    - 'HOLD MAX ON' -> 'HOLD'
    """
    first_token = scpi_text.strip().split()[0]
    return first_token.rstrip("?").upper()


def is_valid_scpi_output(scpi_text: str) -> bool:
    """
    Verifica si la salida parece un comando SCPI documentado.
    """
    if scpi_text == "UNKNOWN":
        return True

    if not scpi_text.strip():
        return False

    command_name = extract_command_name(scpi_text)
    return command_exists(command_name)


def keyword_mapping(user_input: str) -> str | None:
    """
    Aplica reglas deterministas mínimas para consultas simples y frecuentes.

    Estas reglas tienen prioridad sobre el LLM para reducir ambigüedad y coste.
    Solo deben activarse cuando la intención es claramente operativa.
    """
    text = user_input.lower()

    if "perfil" in text and any(
        term in text for term in ["actual", "activo", "seleccionado", "current"]
    ):
        return "PROF?"
    if "parámetro" in text or "parametro" in text:
        return "PAR?"
    if "medida" in text or "medición" in text or "medicion" in text:
        return "MEAS?"
    if (
        "bloqueada" in text
        or "bloqueado" in text
        or "lock" in text
        or "sincronizada" in text
        or "sincronizado" in text
    ):
        return "LOCK?"
    if "banda" in text and any(
        term in text
        for term in ["actual", "seleccionada", "seleccionado", "activa", "qué", "que"]
    ):
        return "BAND?"
    if "frecuencia" in text and any(
        term in text
        for term in ["actual", "sintonizada", "qué", "que", "dime", "muestra"]
    ):
        return "FREQ?"
    if "identificación" in text or "identificacion" in text or "información del equipo" in text:
        return "IDN?"

    return None


def detect_intent(user_input: str) -> Intent:
    """
    Detecta si la petición del usuario es operativa o documental.

    - command: quiere obtener/generar un comando SCPI
    - knowledge: quiere una explicación técnica basada en la documentación
    """
    text = user_input.lower()

    knowledge_markers = [
        "qué hace",
        "que hace",
        "qué devuelve",
        "que devuelve",
        "qué significa",
        "que significa",
        "explícame",
        "explicame",
        "cómo funciona",
        "como funciona",
        "qué restricciones",
        "que restricciones",
        "qué opciones",
        "que opciones",
        "para qué sirve",
        "para que sirve",
        "diferencia entre",
        "sintaxis",
        "documentación",
        "documentacion",
        "qué comandos existen",
        "que comandos existen",
        "cómo se usa",
        "como se usa",
        "ayuda",
        "explica",
        "puedes explicarme",
        "quién eres",
        "quien eres",
        "tu función",
        "tu funcion",
        "qué eres",
        "que eres",
        "qué puedes hacer",
        "que puedes hacer",
    ]

    if any(marker in text for marker in knowledge_markers):
        return "knowledge"

    return "command"


def build_command_messages(user_input: str) -> list[dict[str, str]]:
    """
    Construye los mensajes para generación de SCPI con contexto dinámico.
    """
    payload = build_knowledge_payload(
        user_input,
        mode="command",
        include_reference=True,
        max_commands=5,
        max_topics=3,
    )

    user_prompt = f"""
Contexto documental seleccionado:
{payload["context"]}

Comandos candidatos detectados:
{payload["selected_commands"]}

Topics candidatos detectados:
{payload["selected_topics"]}

Petición del usuario:
{user_input}

Devuelve exactamente un único comando SCPI válido o UNKNOWN.
""".strip()

    return [
        {"role": "system", "content": SCPI_COMMAND_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_knowledge_messages(user_input: str) -> list[dict[str, str]]:
    """
    Construye los mensajes para respuesta documental o explicativa.
    """
    payload = build_knowledge_payload(
        user_input,
        mode="knowledge",
        include_reference=True,
        max_commands=5,
        max_topics=3,
    )

    user_prompt = f"""
Contexto documental seleccionado:
{payload["context"]}

Comandos candidatos detectados:
{payload["selected_commands"]}

Topics candidatos detectados:
{payload["selected_topics"]}

Pregunta del usuario:
{user_input}

Responde usando únicamente la documentación proporcionada.
No respondas solo con el nombre del comando.
""".strip()

    return [
        {"role": "system", "content": KNOWLEDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def generate_scpi(user_input: str) -> str:
    """
    Genera un comando SCPI a partir de una petición operativa del usuario.

    Flujo:
    1. Intenta resolver por reglas deterministas simples.
    2. Si no aplica, usa el LLM con contexto dinámico en modo command.
    3. Valida que la salida corresponda a un comando documentado.
    """
    mapped = keyword_mapping(user_input)
    if mapped is not None:
        return mapped

    response = ask_llm(build_command_messages(user_input))
    command = normalize_command(response)

    if not is_valid_scpi_output(command):
        return "UNKNOWN"

    return command


def answer_with_knowledge(user_input: str) -> str:
    """
    Responde una pregunta documental o explicativa utilizando la capa knowledge.
    """
    response = ask_llm(build_knowledge_messages(user_input))
    return response.strip()


def generate_response(user_input: str) -> str:
    """
    Punto de entrada general del módulo.

    Decide dinámicamente si la petición requiere:
    - generación de comando SCPI
    - respuesta documental basada en knowledge
    """
    intent = detect_intent(user_input)

    if intent == "knowledge":
        return answer_with_knowledge(user_input)

    return generate_scpi(user_input)