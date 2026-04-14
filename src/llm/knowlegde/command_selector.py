"""
Selector heurístico de comandos para la capa de conocimiento SCPI de Hexylon.

Este módulo mapea solicitudes de usuarios en lenguaje natural a candidatos
de comandos SCPI probables utilizando reglas de palabras clave deterministas.
Su propósito no es generar SCPI directamente, sino identificar qué entradas
de conocimiento de comandos deben inyectarse en el prompt del LLM como
contexto enfocado.
"""

from __future__ import annotations

import re


COMMAND_KEYWORDS: dict[str, list[str]] = {
    "FREQ": [
        "freq",
        "frequency",
        "frecuencia",
        "mhz",
        "khz",
        "ghz",
        "tuned frequency",
        "frecuencia sintonizada",
    ],
    "BAND": [
        "band",
        "banda",
        "ter",
        "sat",
        "fm",
        "dab",
    ],
    "CH": [
        "channel",
        "canal",
        "ch",
        "next channel",
        "previous channel",
        "canal siguiente",
        "canal anterior",
        "sube canal",
        "baja canal",
    ],
    "INPUT": [
        "input",
        "entrada",
        "rf",
        "fiber optics",
        "fibra",
        "fo",
        "ip input",
        "asi",
        "cvbs",
        "tsp",
        "eti",
        "edi",
    ],
    "LAMBDA": [
        "lambda",
        "wavelength",
        "longitud de onda",
        "1310",
        "1490",
        "1550",
    ],
    "MODE": [
        "mode",
        "modo",
        "tv mode",
        "radio mode",
        "waterfall",
        "mosaic",
        "scan mode",
        "modo tv",
        "modo radio",
    ],
    "WIDGETS": [
        "widget",
        "widgets",
        "mosaic",
        "ventana",
        "ventanas",
        "layout",
        "spc",
        "mer carrier",
        "mpx spectrum",
    ],
    "PROF": [
        "profile",
        "perfil",
        "current profile",
        "active profile",
        "cambiar perfil",
        "set profile",
    ],
    "LPROF": [
        "list profiles",
        "profiles",
        "perfiles",
        "listar perfiles",
        "available profiles",
    ],
    "LOCK": [
        "lock",
        "locked",
        "signal lock",
        "bloqueada",
        "bloqueado",
        "enganchada",
        "enganchado",
        "sincronizada",
        "sincronizado",
    ],
    "IDN": [
        "idn",
        "identification",
        "device info",
        "meter info",
        "model",
        "serial",
        "software version",
        "calibration date",
        "identificación",
        "información del equipo",
    ],
    "MEAS": [
        "meas",
        "measurements",
        "medidas",
        "medición",
        "measurement",
        "real-time measurements",
        "current measurements",
    ],
    "PAR": [
        "par",
        "parameters",
        "parametros",
        "parámetros",
        "signal parameters",
        "tuned signal parameters",
    ],
    "POW": [
        "pow",
        "power",
        "potencia",
        "nivel",
        "signal level",
    ],
    "CN": [
        "cn",
        "c/n",
        "carrier to noise",
    ],
    "VA": [
        "va",
        "v/a",
    ],
    "MER": [
        "mer",
        "modulation error ratio",
    ],
    "CBER": [
        "cber",
    ],
    "VBER": [
        "vber",
    ],
    "BCHBER": [
        "bchber",
    ],
    "LKM": [
        "lkm",
        "link margin",
    ],
    "PER": [
        "per",
        "packet error rate",
    ],
    "SER": [
        "ser",
        "symbol error rate",
    ],
    "HUM": [
        "hum",
    ],
    "CSO": [
        "cso",
    ],
    "PREBER": [
        "preber",
    ],
    "POSTBER": [
        "postber",
    ],
    "PRELDPCBER": [
        "preldpcber",
        "ldpc",
    ],
    "PREBCHBER": [
        "prebchber",
    ],
    "MSCBER": [
        "mscber",
    ],
    "FICBER": [
        "ficber",
    ],
    "CBERA": [
        "cbera",
        "layer a cber",
        "cber layer a",
    ],
    "VBERA": [
        "vbera",
        "layer a vber",
        "vber layer a",
    ],
    "CBERB": [
        "cberb",
        "layer b cber",
        "cber layer b",
    ],
    "VBERB": [
        "vberb",
        "layer b vber",
        "vber layer b",
    ],
    "CBERC": [
        "cberc",
        "layer c cber",
        "cber layer c",
    ],
    "VBERC": [
        "vberc",
        "layer c vber",
        "vber layer c",
    ],
    "CNBOOT": [
        "cnboot",
        "bootstrap c/n",
        "bootstrap cn",
    ],
    "ECHOES": [
        "echoes",
        "echo",
        "ecos",
        "pdp",
        "tii",
    ],
    "OPT_POW": [
        "optical power",
        "potencia óptica",
        "opt_pow",
    ],
    "OPT_POW_1310": [
        "optical power 1310",
        "potencia óptica 1310",
        "opt_pow_1310",
    ],
    "OPT_POW_1490": [
        "optical power 1490",
        "potencia óptica 1490",
        "opt_pow_1490",
    ],
    "OPT_POW_1550": [
        "optical power 1550",
        "potencia óptica 1550",
        "opt_pow_1550",
    ],
    "RBW": [
        "rbw",
        "resolution bandwidth",
        "ancho de banda de resolución",
    ],
    "VBW": [
        "vbw",
        "video bandwidth",
        "ancho de banda de vídeo",
        "ancho de banda de video",
    ],
    "SPAN": [
        "span",
        "frequency span",
        "ancho de espectro",
        "span de frecuencia",
    ],
    "RLEVEL": [
        "rlevel",
        "reference level",
        "nivel de referencia",
    ],
    "ATT": [
        "att",
        "attenuation",
        "attenuator",
        "atenuación",
        "atenuador",
    ],
    "HOLD": [
        "hold",
        "hold max",
        "hold min",
        "max hold",
        "min hold",
        "hold clear",
    ],
    "SERVICES": [
        "services",
        "service list",
        "sid list",
        "lista de servicios",
        "listar servicios",
    ],
    "SERVICE": [
        "service",
        "sid",
        "select service",
        "seleccionar servicio",
    ],
    "IMAG": [
        "imag",
        "screenshot",
        "capture image",
        "captura",
        "pantallazo",
        "captura de pantalla",
    ],
    "LCHIPTV": [
        "lchiptv",
        "iptv channels",
        "list iptv",
        "listar iptv",
        "lista iptv",
    ],
    "ADDCHIPTV": [
        "addchiptv",
        "add iptv",
        "añadir iptv",
        "agregar iptv",
        "crear canal iptv",
    ],
    "DELCHIPTV": [
        "delchiptv",
        "delete iptv",
        "remove iptv",
        "borrar iptv",
        "eliminar iptv",
    ],
    "FSTR": [
        "fstr",
        "field strength",
        "intensidad de campo",
    ],
    "ANT": [
        "ant",
        "antenna",
        "antena",
    ],
    "EXTAMP": [
        "extamp",
        "external amplifier",
        "external attenuator",
        "compensation",
        "compensación",
    ],
    "VDC": [
        "vdc",
        "voltage",
        "rf voltage",
        "output voltage",
        "voltaje",
        "tensión",
    ],
}


COMMAND_PRIORITY: dict[str, int] = {
    "FREQ": 100,
    "BAND": 95,
    "CH": 90,
    "INPUT": 85,
    "LAMBDA": 84,
    "MODE": 83,
    "WIDGETS": 82,
    "PROF": 81,
    "LPROF": 80,
    "LOCK": 79,
    "IDN": 78,
    "MEAS": 77,
    "PAR": 76,
    "POW": 75,
    "CN": 74,
    "MER": 73,
    "RBW": 72,
    "VBW": 71,
    "SPAN": 70,
    "RLEVEL": 69,
    "SERVICES": 68,
    "SERVICE": 67,
    "IMAG": 66,
    "LCHIPTV": 65,
    "ADDCHIPTV": 64,
    "DELCHIPTV": 63,
    "ECHOES": 62,
    "OPT_POW": 61,
}


def _normalize_text(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"[^\w\s/\-\?\+\.]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _contains_keyword(text: str, keyword: str) -> bool:
    escaped = re.escape(keyword.lower())
    pattern = rf"(?<!\w){escaped}(?!\w)"
    return re.search(pattern, text) is not None


def select_candidate_commands(user_input: str, max_commands: int = 5) -> list[str]:
    """
    Retorna una lista ordenada de candidatos probables de comandos SCPI para una solicitud de usuario.

    El resultado es determinista y se basa únicamente en coincidencia de palabras clave.
    Los comandos se clasifican primero por número de palabras clave coincidentes, luego por
    una prioridad predefinida.
    """
    normalized = _normalize_text(user_input)
    scored_candidates: list[tuple[str, int, int]] = []

    for command_name, keywords in COMMAND_KEYWORDS.items():
        match_count = sum(1 for keyword in keywords if _contains_keyword(normalized, keyword))
        if match_count == 0:
            continue

        priority = COMMAND_PRIORITY.get(command_name, 0)
        scored_candidates.append((command_name, match_count, priority))

    scored_candidates.sort(key=lambda item: (-item[1], -item[2], item[0]))

    return [command_name for command_name, _, _ in scored_candidates[:max_commands]]


def explain_candidate_selection(user_input: str) -> dict[str, list[str]]:
    """
    Retorna las palabras clave coincidentes por cada comando candidato.

    Útil para depurar el comportamiento del selector durante el desarrollo.
    """
    normalized = _normalize_text(user_input)
    matches: dict[str, list[str]] = {}

    for command_name, keywords in COMMAND_KEYWORDS.items():
        matched = [keyword for keyword in keywords if _contains_keyword(normalized, keyword)]
        if matched:
            matches[command_name] = matched

    return matches