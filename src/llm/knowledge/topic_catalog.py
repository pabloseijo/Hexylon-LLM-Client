"""
Catálogo estructurado de temas funcionales de la API Hexylon.

Un topic representa un área funcional de la API compuesta por múltiples comandos
relacionados. Su objetivo es permitir enriquecer el contexto del LLM cuando la
petición del usuario hace referencia a una capacidad general del sistema y no
a un único comando específico.
"""

from __future__ import annotations

from typing import Any

TOPIC_CATALOG: dict[str, dict[str, Any]] = {
    "tuning": {
        "name": "tuning",
        "description": "Operaciones de sintonía de frecuencia, banda y canal.",
        "summary": (
            "Incluye acciones de lectura y modificación de frecuencia, "
            "selección de banda y navegación o selección de canales."
        ),
        "commands": ["FREQ", "BAND", "CH"],
        "notes": [
            "Los cambios de banda pueden fallar dependiendo del modo del analizador.",
            "Los nombres de canal son case-sensitive.",
        ],
        "keywords": [
            "frequency",
            "frecuencia",
            "band",
            "banda",
            "channel",
            "canal",
            "tuning",
            "sintonía",
        ],
    },
    "input_selection": {
        "name": "input_selection",
        "description": "Selección de entrada de señal y configuración óptica.",
        "summary": (
            "Incluye selección de fuente de entrada RF, FO, IP, ASI, CVBS, "
            "TSP, ETI y EDI, así como configuración de lambda óptica."
        ),
        "commands": ["INPUT", "LAMBDA"],
        "notes": [
            "LAMBDA solo aplica en contextos de señal óptica.",
        ],
        "keywords": [
            "input",
            "entrada",
            "rf",
            "fiber",
            "fibra",
            "optics",
            "optical",
            "lambda",
            "wavelength",
            "longitud de onda",
        ],
    },
    "mode_and_layout": {
        "name": "mode_and_layout",
        "description": "Configuración de modo de analizador y distribución de widgets.",
        "summary": (
            "Incluye modos TV/Radio, índices de pantalla, modo de widget único, "
            "Mosaic 3+1, Mosaic 6 y configuración de widgets."
        ),
        "commands": ["MODE", "WIDGETS"],
        "notes": [
            "TV soporta índice 4 para Waterfall.",
            "WIDGETS solo acepta 1, 4 o 6 widgets.",
        ],
        "keywords": [
            "mode",
            "modo",
            "tv mode",
            "radio mode",
            "widget",
            "widgets",
            "mosaic",
            "layout",
            "waterfall",
            "scan",
            "ventana",
            "ventanas",
        ],
    },
    "profiles": {
        "name": "profiles",
        "description": "Gestión de perfiles almacenados en el equipo.",
        "summary": (
            "Incluye lectura del perfil activo, listado de perfiles "
            "y cambio del perfil de usuario activo."
        ),
        "commands": ["LPROF", "PROF"],
        "notes": [
            "El cambio de perfil requiere un nombre de perfil existente.",
        ],
        "keywords": [
            "profile",
            "profiles",
            "perfil",
            "perfiles",
            "current profile",
            "active profile",
            "list profiles",
            "listar perfiles",
        ],
    },
    "status_and_identity": {
        "name": "status_and_identity",
        "description": "Consultas de estado básico e identificación del equipo.",
        "summary": (
            "Incluye comprobación de lock de señal y obtención de "
            "información identificativa del equipo."
        ),
        "commands": ["LOCK", "IDN"],
        "notes": [
            "LOCK devuelve TRUE o FALSE.",
            "IDN devuelve modelo, referencia, serie, versión software y calibración.",
        ],
        "keywords": [
            "lock",
            "locked",
            "status",
            "estado",
            "device info",
            "meter info",
            "idn",
            "identification",
            "identificación",
            "model",
            "serial",
            "software version",
        ],
    },
    "measurements_basic": {
        "name": "measurements_basic",
        "description": "Medidas principales y parámetros básicos de señal.",
        "summary": (
            "Incluye medidas en tiempo real, potencia, C/N, MER, BER "
            "y parámetros de la señal sintonizada."
        ),
        "commands": [
            "MEAS",
            "PAR",
            "POW",
            "CN",
            "VA",
            "MER",
            "CBER",
            "VBER",
            "BCHBER",
        ],
        "notes": [
            "MEAS depende de lo que esté visible en pantalla.",
            "PAR depende del contexto del widget Parameters.",
            "Algunas métricas BER pueden devolver NVAL.",
        ],
        "keywords": [
            "measurement",
            "measurements",
            "medida",
            "medidas",
            "parameter",
            "parameters",
            "parámetro",
            "parámetros",
            "power",
            "potencia",
            "c/n",
            "mer",
            "ber",
        ],
    },
    "measurements_advanced": {
        "name": "measurements_advanced",
        "description": "Métricas avanzadas y especializadas de calidad de señal.",
        "summary": (
            "Incluye métricas avanzadas como Link Margin, PER, SER, HUM, "
            "CSO, PREBER, POSTBER, BERs avanzados y métricas por capas."
        ),
        "commands": [
            "LKM",
            "PER",
            "SER",
            "HUM",
            "CSO",
            "PREBER",
            "POSTBER",
            "PRELDPCBER",
            "PREBCHBER",
            "MSCBER",
            "FICBER",
            "CBERA",
            "VBERA",
            "CBERB",
            "VBERB",
            "CBERC",
            "VBERC",
            "CNBOOT",
        ],
        "notes": [
            "Muchas métricas avanzadas son dependientes del contexto.",
            "Las métricas por capas solo aplican a estándares compatibles.",
        ],
        "keywords": [
            "link margin",
            "per",
            "ser",
            "hum",
            "cso",
            "preber",
            "postber",
            "ldpc",
            "bch",
            "mscber",
            "ficber",
            "layer a",
            "layer b",
            "layer c",
            "bootstrap",
            "advanced measurements",
            "medidas avanzadas",
        ],
    },
    "echoes_and_optical": {
        "name": "echoes_and_optical",
        "description": "Análisis de ecos y medidas ópticas.",
        "summary": (
            "Incluye análisis de ecos mediante ECHOES y medidas de potencia "
            "óptica generales y específicas por lambda."
        ),
        "commands": [
            "ECHOES",
            "OPT_POW",
            "OPT_POW_1310",
            "OPT_POW_1490",
            "OPT_POW_1550",
        ],
        "notes": [
            "ECHOES requiere que el widget Echoes o PDP esté activo.",
            "Las medidas ópticas aplican en contexto óptico.",
        ],
        "keywords": [
            "echo",
            "echoes",
            "ecos",
            "pdp",
            "tii",
            "optical power",
            "potencia óptica",
            "1310",
            "1490",
            "1550",
        ],
    },
    "spectrum_analyser": {
        "name": "spectrum_analyser",
        "description": "Configuración del analizador de espectro.",
        "summary": (
            "Incluye configuración de RBW, VBW, SPAN, RLEVEL, "
            "atenuación y modos hold."
        ),
        "commands": ["RBW", "VBW", "SPAN", "RLEVEL", "ATT", "HOLD"],
        "notes": [
            "El analizador de espectro debe estar maximizado.",
            "RBW, VBW y RLEVEL soportan AUTO donde aplique.",
        ],
        "keywords": [
            "spectrum",
            "spectrum analyser",
            "analizador de espectro",
            "rbw",
            "vbw",
            "span",
            "rlevel",
            "reference level",
            "resolution bandwidth",
            "video bandwidth",
            "attenuation",
            "hold",
            "espectro",
            "analizador espectro",
            "sintonía",
            "sintonizacion",
            "sintonización",
            "medición",
            "mediciones",
            "parámetros",
            "diseño",
            "pantalla",
            "lista de canales",
        ],
    },
    "services": {
        "name": "services",
        "description": "Gestión de servicios del transport stream.",
        "summary": (
            "Incluye listado de servicios TS y selección de servicio por SID."
        ),
        "commands": ["SERVICES", "SERVICE"],
        "notes": [
            "SERVICES devuelve los SIDs del transport stream.",
            "SERVICE selecciona un servicio por SID.",
        ],
        "keywords": [
            "service",
            "services",
            "sid",
            "ts service",
            "servicio",
            "servicios",
            "listar servicios",
        ],
    },
    "iptv": {
        "name": "iptv",
        "description": "Gestión de lista de canales IPTV.",
        "summary": (
            "Incluye listado, alta, borrado y selección de canales IPTV."
        ),
        "commands": ["LCHIPTV", "ADDCHIPTV", "DELCHIPTV", "CH"],
        "notes": [
            "CH <Channel_name> puede seleccionar canales IPTV cuando IPTV está activo.",
        ],
        "keywords": [
            "iptv",
            "iptv channels",
            "channel list",
            "lista iptv",
            "añadir iptv",
            "agregar iptv",
            "eliminar iptv",
            "borrar iptv",
        ],
    },
    "utility_and_capture": {
        "name": "utility_and_capture",
        "description": "Funciones auxiliares y de captura.",
        "summary": (
            "Incluye captura de pantalla, control de field strength, "
            "selección de antena, compensación externa y tensión RF."
        ),
        "commands": ["IMAG", "FSTR", "ANT", "EXTAMP", "VDC"],
        "notes": [
            "IMAG devuelve una URL de descarga.",
            "wget requiere --no-check-certificate y curl requiere --insecure.",
        ],
        "keywords": [
            "screenshot",
            "captura",
            "captura de pantalla",
            "imag",
            "field strength",
            "intensidad de campo",
            "antenna",
            "antena",
            "external amplifier",
            "attenuator",
            "compensation",
            "vdc",
            "voltage",
            "voltaje",
            "tensión",
        ],
    },
}


def get_topic_info(topic_name: str) -> dict[str, Any] | None:
    """
    Devuelve la entrada de un topic por nombre normalizado.
    """
    normalized = topic_name.strip().lower()
    return TOPIC_CATALOG.get(normalized)


def topic_exists(topic_name: str) -> bool:
    """
    Devuelve True si el topic existe en el catálogo.
    """
    return get_topic_info(topic_name) is not None


def get_topic_context(topic_names: list[str]) -> str:
    """
    Construye un bloque de contexto textual compacto para una lista de topics.

    Este contexto puede ser inyectado en prompts cuando la petición del usuario
    hace referencia a una capacidad general del sistema.
    """
    context_blocks: list[str] = []

    for topic_name in topic_names:
        topic_info = get_topic_info(topic_name)
        if not topic_info:
            continue

        lines: list[str] = [
            f"TOPIC: {topic_info['name']}",
            f"DESCRIPTION: {topic_info['description']}",
            f"SUMMARY: {topic_info['summary']}",
        ]

        commands = topic_info.get("commands") or []
        if commands:
            lines.append("RELATED COMMANDS:")
            lines.extend(f"- {command}" for command in commands)

        notes = topic_info.get("notes") or []
        if notes:
            lines.append("NOTES:")
            lines.extend(f"- {note}" for note in notes)

        context_blocks.append("\n".join(lines))

    return "\n\n".join(context_blocks)