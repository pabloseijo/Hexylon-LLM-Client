import re


class UnitNormalizationError(Exception):
    """Error al normalizar unidades."""


def format_number(value: float) -> str:
    """
    Formatea un número con un máximo de 2 decimales, eliminando ceros innecesarios.
    """
    return f"{value:.2f}".rstrip("0").rstrip(".")


def normalize_frequency_to_mhz(raw_text: str) -> str:
    """
    Convierte una frecuencia expresada en Hz, kHz, MHz o GHz a una representación
    normalizada en MHz.

    Ejemplos admitidos:
    - '530000 kHz' -> '530 MHz'
    - '530 MHz' -> '530 MHz'
    - '0.53 GHz' -> '530 MHz'
    - '530000000 Hz' -> '530 MHz'
    - 'FREQ 530000 kHz' -> '530 MHz'
    """
    text = raw_text.strip()

    match = re.search(r"(\d+(?:\.\d+)?)\s*GHz\b", text, re.IGNORECASE)
    if match:
        ghz = float(match.group(1))
        mhz = ghz * 1000
        return f"{format_number(mhz)} MHz"

    match = re.search(r"(\d+(?:\.\d+)?)\s*MHz\b", text, re.IGNORECASE)
    if match:
        mhz = float(match.group(1))
        return f"{format_number(mhz)} MHz"

    match = re.search(r"(\d+(?:\.\d+)?)\s*kHz\b", text, re.IGNORECASE)
    if match:
        khz = float(match.group(1))
        mhz = khz / 1000
        return f"{format_number(mhz)} MHz"

    match = re.search(r"(\d+(?:\.\d+)?)\s*Hz\b", text, re.IGNORECASE)
    if match:
        hz = float(match.group(1))
        mhz = hz / 1_000_000
        return f"{format_number(mhz)} MHz"

    # Fallback: número sin unidad
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match:
        value = float(match.group(1))

        # Heurística conservadora para respuestas SCPI sin unidad
        if value >= 1_000_000:
            mhz = value / 1_000_000
        elif value >= 10_000:
            mhz = value / 1000
        else:
            mhz = value

        return f"{format_number(mhz)} MHz"

    raise UnitNormalizationError(
        f"No se pudo normalizar frecuencia desde: {raw_text}"
    )


def normalize_power(raw_text: str) -> str:
    """
    Normaliza medidas de potencia o nivel manteniendo la unidad original cuando es válida.
    Unidades soportadas: dBµV, dBmV, dBm.
    """
    text = raw_text.strip()

    match = re.search(
        r"([-+]?\d+(?:\.\d+)?)\s*(dBµV|dBuV|dBmV|dBm)\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        raise UnitNormalizationError(
            f"No se pudo normalizar potencia desde: {raw_text}"
        )

    value = float(match.group(1))
    unit = match.group(2)

    if unit.lower() == "dbuv":
        unit = "dBµV"

    return f"{format_number(value)} {unit}"


def normalize_db_value(raw_text: str) -> str:
    """
    Normaliza magnitudes expresadas en dB.
    """
    text = raw_text.strip()

    match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*dB\b", text, re.IGNORECASE)
    if not match:
        raise UnitNormalizationError(
            f"No se pudo normalizar valor en dB desde: {raw_text}"
        )

    value = float(match.group(1))
    return f"{format_number(value)} dB"


def normalize_percentage(raw_text: str) -> str:
    """
    Normaliza porcentajes.
    """
    text = raw_text.strip()

    match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*%\b", text)
    if not match:
        raise UnitNormalizationError(
            f"No se pudo normalizar porcentaje desde: {raw_text}"
        )

    value = float(match.group(1))
    return f"{format_number(value)} %"


def normalize_bitrate_to_mbps(raw_text: str) -> str:
    """
    Convierte tasas binarias a Mbps.
    """
    text = raw_text.strip()

    match = re.search(r"(\d+(?:\.\d+)?)\s*Mbps\b", text, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        return f"{format_number(value)} Mbps"

    match = re.search(r"(\d+(?:\.\d+)?)\s*kbps\b", text, re.IGNORECASE)
    if match:
        value = float(match.group(1)) / 1000
        return f"{format_number(value)} Mbps"

    match = re.search(r"(\d+(?:\.\d+)?)\s*bps\b", text, re.IGNORECASE)
    if match:
        value = float(match.group(1)) / 1_000_000
        return f"{format_number(value)} Mbps"

    raise UnitNormalizationError(
        f"No se pudo normalizar bitrate desde: {raw_text}"
    )


def normalize_boolean(raw_text: str) -> str:
    """
    Normaliza respuestas booleanas SCPI.
    """
    text = raw_text.strip().upper()

    if "TRUE" in text:
        return "TRUE"
    if "FALSE" in text:
        return "FALSE"

    raise UnitNormalizationError(
        f"No se pudo normalizar booleano desde: {raw_text}"
    )