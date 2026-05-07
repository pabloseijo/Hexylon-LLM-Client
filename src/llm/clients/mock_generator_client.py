"""
Cliente mock del generador de señales R&S SGU100A.

En lugar de enviar comandos al hardware real, escribe en un fichero de log
con timestamp para validar la secuencialidad de la ejecución.

Cuando se disponga del cliente real, este módulo se sustituye manteniendo
la misma interfaz: send_generator_command(command, machine_id) -> str
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from llm.knowledge.generator_command_catalog import (
    GENERATOR_COMMAND_CATALOG,
    get_generator_command_info,
)


_LOG_PATH = Path(__file__).parents[3] / "tmp" / "mock_generator.log"

# Prefijos de comandos válidos extraídos del catálogo
_VALID_PREFIXES = tuple(
    key.split(":")[0].split("*")[0].upper().strip()
    for key in GENERATOR_COMMAND_CATALOG.keys()
    if key.strip()
)


class GeneratorClientError(Exception):
    """Error al comunicarse con el generador de señales."""


def _write_log(entry: str) -> None:
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG_PATH, "a") as f:
        f.write(entry + "\n")


def _is_known_command(command: str) -> bool:
    """
    Comprueba si el comando es reconocible según el catálogo del SGU100A.
    Acepta formas cortas (POW, FREQ, OUTP...) y formas largas.
    """
    cmd = command.strip().upper().split()[0].rstrip("?")

    # Búsqueda directa en catálogo
    if get_generator_command_info(cmd):
        return True

    # Búsqueda por prefijo — cubre formas cortas como POW, FREQ, OUTP, LOCK...
    known_prefixes = {
        "POW", "FREQ", "OUTP", "SOUR", "SETT", "LOCK", "UNL",
        "LOSC", "FAST", "FFAST", "PFAST", "PULM", "SYST",
        "*RST", "*CLS", "*IDN", "*OPC", "*WAI",
    }
    return cmd in known_prefixes or any(cmd.startswith(p) for p in known_prefixes)


def send_generator_command(command: str, machine_id: str = "generator") -> str:
    """
    Envía un comando al generador de señales.

    En modo mock escribe en tmp/mock_generator.log y devuelve OK.
    Valida que el comando sea reconocible según el catálogo SGU100A.

    Parameters
    ----------
    command:
        Comando SCPI a enviar al generador.
    machine_id:
        ID de la máquina destino (para el log).

    Returns
    -------
    str
        Respuesta del generador. En mock devuelve "OK" para escritura
        o un valor simulado para consultas (?).

    Raises
    ------
    GeneratorClientError
        Si el comando no es reconocible.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    cmd_clean = command.strip()

    # Validar que el comando es reconocible
    if not _is_known_command(cmd_clean):
        error_entry = (
            f"[{timestamp}] "
            f"machine={machine_id} "
            f"command={cmd_clean!r} "
            f"status=REJECTED reason=unknown_command"
        )
        _write_log(error_entry)
        raise GeneratorClientError(
            f"Comando no reconocido para SGU100A: '{cmd_clean}'. "
            f"Verifica la sintaxis en el manual (capítulo 13)."
        )

    # Simular respuesta para queries
    is_query = cmd_clean.endswith("?")
    if is_query:
        response = _simulate_query_response(cmd_clean)
    else:
        response = "OK"

    entry = (
        f"[{timestamp}] "
        f"machine={machine_id} "
        f"command={cmd_clean!r} "
        f"response={response!r} "
        f"status=OK"
    )
    _write_log(entry)
    print(f"[MOCK GENERATOR] {entry}")

    return response


def _simulate_query_response(command: str) -> str:
    """
    Devuelve una respuesta simulada razonable para comandos de consulta.
    Útil para validar que el sistema procesa correctamente las respuestas.
    """
    cmd = command.strip().upper().rstrip("?")

    simulated = {
        "*IDN":                                    "Rohde&Schwarz,SGU100A,1418.2005.02/100001,5.00.232.00",
        "SOURFFREQU":                              "2000000000",
        "SOURFREQ":                                "2000000000",
        "FREQ":                                    "2000000000",
        "SOURPOW":                                 "-10",
        "POW":                                     "-10",
        "SOURPOWPOW":                              "-10",
        "OUTPSTAT":                                "ON",
        "SOURPOWPEP":                              "-10",
        "SOURPOWRANGELOW":                         "-120",
        "SOURPOWRANGEUPP":                         "25",
        "SOURPOWLIM":                              "30",
        "SOURPOWLMOD":                             "NORMal",
        "SOURPOWSCH":                              "AUTO",
        "SOURPOWLEV":                              "-10",
        "SOURPOWLEVELIMM":                         "-10",
        "SOURPOWLEVIMM":                           "-10",
        "SOURPOWLEVIMMOFF":                        "0",
        "SOURPOWLEVIMMAMP":                        "-10",
        "OUTPAFIXRANGELOW":                        "-30",
        "OUTPAFIXRANGEUPP":                        "5",
        "OUTPAMOD":                                "AUTO",
        "LOSCFREQ":                                "1000000000",
        "LOSCPOW":                                 "-10",
        "SOURLOSC":                                "-10",
        "SOURIQSTAT":                              "OFF",
        "SOURPULM":                                "OFF",
        "SYSTERR":                                 "0,No error",
        "SYSTERRALL":                              "0,No error",
        "SYSTERRNEXT":                             "0,No error",
        "SYSTCOMMNETWORKIP":                       "10.113.0.149",
    }

    # Normalizar para lookup: quitar separadores
    key = cmd.replace(":", "").replace("[", "").replace("]", "").replace(" ", "")
    return simulated.get(key, "0")