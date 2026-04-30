from __future__ import annotations

import re


FREQ_UNITS = {
    "ghz": "GHz",
    "mhz": "MHz",
    "khz": "KHz",
}

BANDWIDTH_UNITS = {
    "hzw": "HzW",
    "khzw": "KHzW",
    "mhzw": "MHzW",
    "hz": "Hz",
    "khz": "KHz",
    "mhz": "MHz",
}

LEVEL_UNITS = {
    "dbuv": "dBuV",
    "dbmv": "dBmV",
    "dbm": "dBm",
}


def _clean_number(value: str) -> str:
    value = value.replace(",", ".")

    if "." in value:
        value = value.rstrip("0").rstrip(".")

    return value


def normalize_scpi_command(command: str) -> str:
    command = command.strip()

    if not command or command == "UNKNOWN":
        return command

    command = re.sub(r"\s+", " ", command)
    parts = command.split(" ", 1)

    name = parts[0].upper()
    args = parts[1].strip() if len(parts) > 1 else ""

    if name.endswith("?"):
        return name

    if not args:
        return name

    # FREQ 594.00mhz -> FREQ 594MHz
    if name == "FREQ":
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(ghz|mhz|khz)", args, re.I)
        if match:
            value = _clean_number(match.group(1))
            unit = FREQ_UNITS[match.group(2).lower()]
            return f"FREQ {value} {unit}"

    # RBW 300hzw / 300 hz -> RBW 300HzW
    if name == "RBW":
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(hzw|khzw|mhzw|hz|khz|mhz)", args, re.I)
        if match:
            value = _clean_number(match.group(1))
            raw_unit = match.group(2).lower()

            if raw_unit in {"hz", "khz", "mhz"}:
                raw_unit = f"{raw_unit}w"

            unit = BANDWIDTH_UNITS[raw_unit]
            return f"RBW {value} {unit}"

        if args.upper() == "AUTO":
            return "RBW AUTO"

    # VBW 10khz -> VBW 10KHz
    if name == "VBW":
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(hz|khz|mhz)", args, re.I)
        if match:
            value = _clean_number(match.group(1))
            unit = BANDWIDTH_UNITS[match.group(2).lower()]
            return f"VBW {value} {unit}"

        if args.upper() == "AUTO":
            return "VBW AUTO"

    # SPAN 20mhz -> SPAN 20MHz
    if name == "SPAN":
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(khz|mhz)", args, re.I)
        if match:
            value = _clean_number(match.group(1))
            unit = BANDWIDTH_UNITS[match.group(2).lower()]
            return f"SPAN {value} {unit}"

    # RLEVEL 80dbuv -> RLEVEL 80dBuV
    if name == "RLEVEL":
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(dbuv|dbmv|dbm)", args, re.I)
        if match:
            value = _clean_number(match.group(1))
            unit = LEVEL_UNITS[match.group(2).lower()]
            return f"RLEVEL {value} {unit}"

        if args.upper() == "AUTO":
            return "RLEVEL AUTO"

    # Comandos simples con argumentos en mayúsculas
    return f"{name} {args.upper()}"