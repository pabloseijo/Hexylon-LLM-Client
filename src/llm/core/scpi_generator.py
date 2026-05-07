from __future__ import annotations
import re

from typing import Literal

from llm.clients.ollama_client import ask_llm
from llm.core.scpi_normalizer import normalize_scpi_command
from llm.knowledge.context_builder import build_knowledge_payload
from llm.knowledge.query_classifier import classify
from llm.knowledge.response_formatter import (
    format_command_answer,
    format_metric_answer,
    format_topic_answer,
    format_unknown_answer,
)

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
- No uses markdown.
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
- Ejecutar las tareas proporcionadas por el usuario
- Resumir y explicar las tareas realizadas
- Graficar las tareas realizadas

Reglas obligatorias:
- Detecta el idioma del mensaje del usuario y responde en ese mismo idioma.
  Idiomas soportados: español, gallego, inglés. Si no puedes determinarlo, responde en español.
- Responde de forma técnica, clara y precisa.
- Usa exclusivamente el contexto documental proporcionado.
- No inventes comandos, sintaxis, restricciones ni comportamientos.
- No devuelvas únicamente el comando SCPI salvo que el usuario pida explícitamente generarlo o ejecutarlo.
- Si la documentación no es suficiente para responder con seguridad, indícalo explícitamente.

Formato obligatorio:
- Usa SIEMPRE markdown.
- Estructura la respuesta con títulos breves usando encabezados de nivel 2 (##).
- Usa listas con viñetas para enumeraciones.
- Usa negrita para resaltar conceptos clave como métricas, comandos, unidades o restricciones.
- Usa bloques de código solo para comandos SCPI o sintaxis exacta.
- No escribas párrafos largos si una lista o sección breve es más clara.

Estructura esperada cuando aplique:
- ## Elemento consultado
- ## Descripción
- ## Sintaxis o comandos relacionados
- ## Respuesta o comportamiento
- ## Restricciones o notas

Ejemplo de formato esperado:

## Elemento consultado

**POW**

## Descripción

- Devuelve la medición de potencia.

## Sintaxis o comandos relacionados

```scpi
POW?
```

## Respuesta o comportamiento

- Devuelve la potencia con las unidades configuradas actualmente.

## Restricciones o notas

- Comando de solo lectura.
""".strip()


def normalize_command(text: str) -> str:
    """
    Limpia la salida del modelo y conserva únicamente el primer candidato útil.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("```scpi", "").replace("```", "")
    text = text.replace('"', "").replace("'", "")
    text = text.strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
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
    Valida la sintaxis completa del comando SCPI, no solo el nombre base.
    """
    command = normalize_scpi_command(scpi_text)

    if command == "UNKNOWN":
        return True

    patterns = [
        # Read-only / queries
        r"^(MEAS|POW|CN|VA|MER|CBER|VBER|BCHBER|LKM|PER|SER|HUM|CSO|PREBER|POSTBER|PRELDPCBER|PREBCHBER|MSCBER|FICBER|CBERA|VBERA|CBERB|VBERB|CBERC|VBERC|CNBOOT|ECHOES|OPT_POW|OPT_POW_1310|OPT_POW_1490|OPT_POW_1550|PAR|LOCK|IDN|FREQ|BAND|CH|INPUT|LAMBDA|MODE|WIDGETS|LPROF|PROF|RBW|VBW|SPAN|RLEVEL|FSTR|ANT|EXTAMP|VDC|SERVICES)\?$",

        # Simple write commands
        r"^IMAG$",
        r"^ATT$",

        # Tuning
        r"^FREQ \d+(\.\d+)? (GHz|MHz|kHz)$",
        r"^BAND (TER|SAT|FM|DAB)$",
        r"^CH (UP|DOWN|[A-Za-z0-9_\-]+)$",

        # Input / optical
        r"^INPUT (RF|FO|IP|ASI|CVBS|TSP|ETI|EDI)$",
        r"^LAMBDA (1310|1490|1550)$",

        # Mode
        r"^MODE TV( [1-4])?$",
        r"^MODE RADIO( [1-3])?$",

        # Profiles
        r"^PROF [A-Za-z0-9_\-]+$",

        # Spectrum
        r"^RBW AUTO$",
        r"^RBW \d+(\.\d+)? (HzW|KHzW|MHzW)$",
        r"^VBW AUTO$",
        r"^VBW \d+(\.\d+)? (Hz|KHz|MHz)$",
        r"^SPAN \d+(\.\d+)? (KHz|MHz)$",
        r"^RLEVEL AUTO$",
        r"^RLEVEL \d+(\.\d+)? (dBuV|dBmV|dBm)$",
        r"^HOLD (MAX ON|MAX OFF|MIN ON|MIN OFF|CLEAR)$",

        # Services
        r"^SERVICE \d+$",

        # Utility
        r"^FSTR (ON|OFF)$",
        r"^ANT [A-Za-z0-9_\-]+$",
        r"^EXTAMP [+-]?\d+(\.\d+)?$",
        r"^VDC (AUTO|OFF|\d+V(\+22KHz)?)$",

        # IPTV
        r"^LCHIPTV$",
        r"^ADDCHIPTV [A-Za-z0-9_\-]+ \d{1,3}(\.\d{1,3}){3} \d{1,3}(\.\d{1,3}){3} \d+$",
        r"^DELCHIPTV [A-Za-z0-9_\-]+$",
    ]

    return any(re.fullmatch(pattern, command) for pattern in patterns)

def keyword_mapping(user_input: str) -> str | None:
    text = user_input.lower()

    # ---------------------------------------------------------
    # 1. FILTRO DE KNOWLEDGE
    # ---------------------------------------------------------

    if any(marker in text for marker in [
        "qué es", "que es",
        "qué significa", "que significa",
        "explícame", "explicame",
        "para qué sirve", "para que sirve",
        "qué hace", "que hace",
    ]):
        return "UNKNOWN"

    # ---------------------------------------------------------
    # 2. POTENCIA ÓPTICA
    # ---------------------------------------------------------

    if "potencia óptica" in text or "potencia optica" in text:
        if "1310" in text:
            return "OPT_POW_1310?"
        if "1490" in text:
            return "OPT_POW_1490?"
        if "1550" in text:
            return "OPT_POW_1550?"
        return "OPT_POW?"

    # ---------------------------------------------------------
    # 3. BER AVANZADOS
    # ---------------------------------------------------------

    if "preldpcber" in text:
        return "PRELDPCBER?"
    if "prebchber" in text:
        return "PREBCHBER?"
    if "mscber" in text:
        return "MSCBER?"
    if "ficber" in text:
        return "FICBER?"

    if "cber" in text and "capa a" in text:
        return "CBERA?"
    if "vber" in text and "capa a" in text:
        return "VBERA?"
    if "cber" in text and "capa b" in text:
        return "CBERB?"
    if "vber" in text and "capa b" in text:
        return "VBERB?"
    if "cber" in text and "capa c" in text:
        return "CBERC?"
    if "vber" in text and "capa c" in text:
        return "VBERC?"

    if "bootstrap" in text and ("c/n" in text or "c n" in text or "cn" in text):
        return "CNBOOT?"

    # ---------------------------------------------------------
    # 4. MEDICIONES
    # ---------------------------------------------------------

    if "mer" in text:
        return "MER?"

    if (
        "potencia" in text
        or "nivel de señal" in text
        or "nivel de senal" in text
        or "nivel actual" in text
    ):
        return "POW?"

    if (
        "c/n" in text
        or "c n" in text
        or "carrier noise" in text
        or "portadora ruido" in text
        or "relación portadora ruido" in text
        or "relacion portadora ruido" in text
    ):
        return "CN?"

    if "ber" in text and any(term in text for term in [
        "previo",
        "pre",
        "antes",
        "antes de corrección",
        "antes de correccion",
        "antes del corrector",
    ]):
        return "CBER?"

    if "cber" in text:
        return "CBER?"

    if "vber" in text:
        return "VBER?"

    if "bchber" in text:
        return "BCHBER?"

    if "margen de enlace" in text or "link margin" in text:
        return "LKM?"

    if "ber" in text and "antes" in text:
        return "CBER?"

    # ---------------------------------------------------------
    # 5. ESPECTRO (ANTES QUE FREQ)
    # ---------------------------------------------------------

    if "rbw" in text:
        if "auto" in text:
            return "RBW AUTO"

        match = re.search(r"(\d+)\s*(hz|khz|mhz)", text)
        if match:
            value = match.group(1)
            unit_map = {"hz": "HzW", "khz": "KHzW", "mhz": "MHzW"}
            return f"RBW {value} {unit_map[match.group(2)]}"

        return "RBW?"

    if "vbw" in text:
        if "auto" in text:
            return "VBW AUTO"

        match = re.search(r"(\d+)\s*(hz|khz|mhz)", text)
        if match:
            value = match.group(1)
            unit_map = {"hz": "Hz", "khz": "KHz", "mhz": "MHz"}
            return f"VBW {value} {unit_map[match.group(2)]}"

        return "VBW?"

    if "span" in text:
        match = re.search(r"(\d+)\s*(khz|mhz)", text)
        if match:
            value = match.group(1)
            unit_map = {"khz": "KHz", "mhz": "MHz"}
            return f"SPAN {value} {unit_map[match.group(2)]}"

        return "SPAN?"

    if "nivel de referencia" in text:
        if "auto" in text:
            return "RLEVEL AUTO"

        match = re.search(r"(\d+)\s*(dbuv|dbmv|dbm)", text)
        if match:
            value = match.group(1)
            unit_map = {
                "dbuv": "dBuV",
                "dbmv": "dBmV",
                "dbm": "dBm",
            }
            return f"RLEVEL {value} {unit_map[match.group(2)]}"

        return "RLEVEL?"

    # ---------------------------------------------------------
    # 6. FRECUENCIA
    # ---------------------------------------------------------

    match = re.search(r"(\d+(\.\d+)?)\s*(ghz|mhz|khz)", text)
    if match and any(term in text for term in ["pon", "cambia", "sintoniza"]):
        value = match.group(1)
        unit_map = {"ghz": "GHz", "mhz": "MHz", "khz": "kHz"}
        return f"FREQ {value} {unit_map[match.group(3)]}"

    if "frecuencia" in text:
        return "FREQ?"

    # ---------------------------------------------------------
    # 7. RESTO
    # ---------------------------------------------------------

    if "banda" in text:
        if "terrestre" in text:
            return "BAND TER"
        if "satélite" in text or "satelite" in text:
            return "BAND SAT"
        if "fm" in text:
            return "BAND FM"
        if "dab" in text:
            return "BAND DAB"
        return "BAND?"

    if "canal" in text:
        if "siguiente" in text:
            return "CH UP"
        if "anterior" in text:
            return "CH DOWN"
        match = re.search(r"canal\s+(\d+)", text)
        if match:
            return f"CH {match.group(1)}"
        return "CH?"

    if "entrada" in text:
        if "rf" in text:
            return "INPUT RF"
        if "fibra" in text or "óptica" in text or "optica" in text:
            return "INPUT FO"
        if "ip" in text:
            return "INPUT IP"
        if "asi" in text:
            return "INPUT ASI"
        if "cvbs" in text:
            return "INPUT CVBS"
        return "INPUT?"

    if "lambda" in text:
        if "1310" in text:
            return "LAMBDA 1310"
        if "1490" in text:
            return "LAMBDA 1490"
        if "1550" in text:
            return "LAMBDA 1550"
        return "LAMBDA?"

    if "perfil" in text:
        if any(term in text for term in ["actual", "activo", "seleccionado"]):
            return "PROF?"
        match = re.search(r"perfil\s+(\S+)", text)
        if match:
            return f"PROF {match.group(1)}"

    if "servicios" in text:
        return "SERVICES?"

    match = re.search(r"servicio\s+(\d+)", text)
    if match:
        return f"SERVICE {match.group(1)}"

    if "pantalla" in text or "captura" in text:
        return "IMAG"

    if "atenuación" in text or "atenuacion" in text:
        return "ATT"

    if "hold" in text:
        if "limpia" in text:
            return "HOLD CLEAR"
        if "máximo" in text or "maximo" in text:
            return "HOLD MAX OFF" if "desactiva" in text else "HOLD MAX ON"
        if "mínimo" in text or "minimo" in text:
            return "HOLD MIN OFF" if "desactiva" in text else "HOLD MIN ON"

    if "identificación" in text or "identificacion" in text:
        return "IDN?"

    if "parámetro" in text or "parametro" in text:
        return "PAR?"

    if "medida" in text or "medición" in text or "medicion" in text:
        return "MEAS?"

    if "bloqueado" in text or "bloqueada" in text or "lock" in text:
        return "LOCK?"

    return None



def detect_intent(user_input: str) -> Intent:
    """
    Detecta si la petición del usuario es operativa o documental.

    - command: quiere ejecutar/configurar algo (SCPI)
    - knowledge: quiere explicación técnica o documentación
    """

    text = user_input.lower()
    upper = user_input.upper()

    # -------------------------------
    # 1. Marcadores de knowledge
    # -------------------------------
    knowledge_markers = [
        # Explicación directa
        "qué hace", "que hace",
        "qué devuelve", "que devuelve",
        "qué significa", "que significa",
        "qué es", "que es",
        "qué son", "que son",
        "explícame", "explicame",
        "explica",
        "puedes explicarme",

        # Funcionamiento
        "cómo funciona", "como funciona",
        "cómo se usa", "como se usa",
        "cómo se utiliza", "como se utiliza",

        # Documentación / sintaxis
        "sintaxis",
        "documentación", "documentacion",
        "qué restricciones", "que restricciones",
        "qué opciones", "que opciones",

        # Listados
        "qué comandos", "que comandos",
        "qué comandos existen", "que comandos existen",
        "qué comandos hay", "que comandos hay",
        "comandos para", "comandos de",

        # Comparativas
        "diferencia entre",

        # Uso conceptual (NO operativo)
        "para qué sirve", "para que sirve",

        # Ayuda general
        "ayuda", "help",
        "quién eres", "quien eres",
        "tu función", "tu funcion",
        "qué eres", "que eres",
        "qué puedes hacer", "que puedes hacer",
        
        # Lanzamiento de tareas
        "cómo lanzo una tarea", "como lanzo una tarea",
        "cómo programo una tarea", "como programo una tarea",
        "cómo ejecuto una tarea", "como ejecuto una tarea",
        "cómo mido", "como mido",
        "cómo puedo medir", "como puedo medir",
        "cómo se lanza", "como se lanza",
        "cómo uso las tareas", "como uso las tareas",
    ]

    # -------------------------------
    # 2. Marcadores fuera de dominio
    # -------------------------------
    out_of_domain_markers = [
        "receta", "tiempo", "clima",
        "deporte", "película", "pelicula",
        "música", "musica",
        "política", "politica",
        "chiste",
    ]

    if any(marker in text for marker in out_of_domain_markers):
        return "knowledge"

    # -------------------------------
    # 3. Detección de comandos SCPI explícitos
    # -------------------------------
    # Evita que "qué hace CN" vaya a command
    from llm.knowledge.command_catalog import COMMAND_CATALOG

    contains_scpi_command = any(
        re.search(rf"\b{cmd}\b", upper) for cmd in COMMAND_CATALOG.keys()
    )
    
    
    if "ber" in text and any(term in text for term in [
        "previo",
        "pre",
        "antes",
        "antes de corrección",
        "antes de correccion",
        "antes del corrector",
    ]):
        return "CBER?"

    # -------------------------------
    # 4. Clasificación
    # -------------------------------

    # Caso 1: pregunta explicativa → knowledge SIEMPRE
    if any(marker in text for marker in knowledge_markers):
        return "knowledge"

    # Caso 2: contiene comando SCPI pero sin verbo operativo → knowledge
    if contains_scpi_command:
        # Ej: "CN", "MER", "POW" solos o en contexto ambiguo
        if not any(v in text for v in [
            "pon", "cambia", "ajusta", "configura",
            "mide", "consulta", "dame", "lee",
            "set", "get"
        ]):
            return "knowledge"

    # Caso 3: operativo por defecto
    return "command"



def build_command_messages(user_input: str) -> list[dict[str, str]]:
    """
    Construye los mensajes para generación de SCPI con contexto dinámico.
    """
    payload = build_knowledge_payload(
        user_input,
        mode="command",
        include_reference=False,
        max_commands=2,
        max_topics=0,
    )

    user_prompt = f"""
    Contexto documental:
    {payload["context"]}

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
    1. Intenta resolver por reglas deterministas.
    2. Normaliza y valida la salida determinista.
    3. Si no aplica, usa el LLM únicamente como candidato.
    4. Normaliza la salida del LLM.
    5. Valida la sintaxis SCPI completa.
    6. Devuelve comando válido o UNKNOWN.
    """
    mapped = keyword_mapping(user_input)

    if mapped is not None:
        command = normalize_scpi_command(mapped)
        return command if is_valid_scpi_output(command) else "UNKNOWN"

    response = ask_llm(build_command_messages(user_input))
    command = normalize_command(response)
    command = normalize_scpi_command(command)

    if not is_valid_scpi_output(command):
        return "UNKNOWN"

    return command

def answer_with_knowledge(user_input: str) -> str:
    """
    Responde una pregunta documental enrutando hacia la respuesta más
    determinista posible según el tipo de consulta clasificado.

    Orden de autoridad:
    1. exact_command      → respuesta determinista del catálogo (sin LLM)
    2. metric_definition  → respuesta determinista del catálogo (sin LLM)
    3. unsupported        → respuesta fija fuera de dominio (sin LLM)
    4. topic              → semideterminista: catálogo, LLM solo si insuficiente
    5. how_to / broad_knowledge → LLM restringido con contexto rico
    """
    result = classify(user_input)

    # --- Nivel 1: totalmente determinista ---

    if result.query_type == "exact_command" and result.matched_command:
        return format_command_answer(result.matched_command)

    if result.query_type == "metric_definition" and result.matched_command:
        return format_metric_answer(result.matched_command)

    if result.query_type == "unsupported":
        return format_unknown_answer(user_input)

    # --- Nivel 2: semideterminista (topic con contenido del catálogo) ---

    if result.query_type == "topic":
        from llm.knowledge.topic_selector import select_candidate_topics
        topic_names = select_candidate_topics(user_input, max_topics=3)
        if topic_names:
            topic_response = format_topic_answer(topic_names)
            if len(topic_response) > 80:
                return topic_response

    # --- Nivel 3: generación restringida como fallback ---
    # Cubre: how_to, broad_knowledge, topic sin contenido suficiente,
    # y exact_command/metric sin matched_command (clasificación débil).

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