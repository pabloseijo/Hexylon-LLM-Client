"""
Evaluación determinista de condiciones para tareas del cliente Hexylon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from llm.tasks.task_models import TaskCondition


class ConditionEvaluationError(Exception):
    """Error al evaluar una condición."""


@dataclass
class ParsedValue:
    """
    Valor parseado listo para comparación.

    Attributes
    ----------
    kind:
        Tipo lógico del valor: number, bool, unavailable, error
    value:
        Valor parseado.
    unit:
        Unidad detectada si aplica.
    raw:
        Texto original.
    """
    kind: str
    value: float | bool | None
    unit: str | None
    raw: str


def _normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None

    normalized = unit.strip()
    normalized = normalized.replace("dBµV", "dBuV")
    normalized = normalized.replace("µ", "u")
    return normalized.lower()


def parse_measurement_value(raw_text: str) -> ParsedValue:
    """
    Convierte una respuesta raw del Hexylon a una forma comparable.
    """
    text = raw_text.strip()

    if not text:
        return ParsedValue(kind="unavailable", value=None, unit=None, raw=raw_text)

    upper = text.upper()

    if upper.startswith("ERROR:"):
        return ParsedValue(kind="error", value=None, unit=None, raw=raw_text)

    if upper in {"NVAL", "UNLOCK", "NOLOCK"}:
        return ParsedValue(kind="unavailable", value=None, unit=None, raw=raw_text)

    if "TRUE" == upper:
        return ParsedValue(kind="bool", value=True, unit=None, raw=raw_text)

    if "FALSE" == upper:
        return ParsedValue(kind="bool", value=False, unit=None, raw=raw_text)

    match = re.search(
        r"([<>]?\s*[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*([A-Za-zµ%0-9/+-]+)?",
        text,
    )
    if not match:
        raise ConditionEvaluationError(
            f"No se pudo parsear el valor de medición: {raw_text}"
        )

    number_text = match.group(1).replace(" ", "")
    unit = match.group(2)

    if number_text.startswith("<") or number_text.startswith(">"):
        number_text = number_text[1:]

    try:
        value = float(number_text)
    except ValueError as exc:
        raise ConditionEvaluationError(
            f"No se pudo convertir a float: {raw_text}"
        ) from exc

    return ParsedValue(
        kind="number",
        value=value,
        unit=unit,
        raw=raw_text,
    )


def parse_threshold_value(raw_text: str) -> ParsedValue:
    """
    Convierte el umbral definido en la condición a forma comparable.
    """
    return parse_measurement_value(raw_text)


def _compare_numeric(left: float, operator: str, right: float) -> bool:
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "==":
        return left == right
    raise ConditionEvaluationError(f"Operador no soportado: {operator}")


def _compare_bool(left: bool, operator: str, right: bool) -> bool:
    if operator != "==":
        raise ConditionEvaluationError(
            "Solo se permite '==' para condiciones booleanas"
        )
    return left == right


def evaluate_condition(
    condition: TaskCondition,
    measurement_values: dict[str, str],
) -> tuple[bool, str | None]:
    """
    Evalúa una condición sobre los valores raw de una iteración.

    Returns
    -------
    tuple[bool, str | None]
        (cumplida, mensaje)
    """
    raw_value = measurement_values.get(condition.command)
    if raw_value is None:
        return False, f"No existe valor para {condition.command} en esta iteración."

    measured = parse_measurement_value(raw_value)
    threshold = parse_threshold_value(condition.threshold_raw)

    if measured.kind in {"unavailable", "error"}:
        return False, (
            f"No se puede evaluar {condition.command}: valor no disponible ({measured.raw})."
        )

    if measured.kind != threshold.kind:
        raise ConditionEvaluationError(
            f"Tipos incompatibles al evaluar condición: {measured.kind} vs {threshold.kind}"
        )

    if measured.kind == "number":
        measured_unit = _normalize_unit(measured.unit)
        threshold_unit = _normalize_unit(threshold.unit)

        if threshold_unit and measured_unit and threshold_unit != measured_unit:
            raise ConditionEvaluationError(
                f"Unidades incompatibles en condición {condition.command}: "
                f"{measured.unit} vs {threshold.unit}"
            )

        assert isinstance(measured.value, float)
        assert isinstance(threshold.value, float)

        matched = _compare_numeric(measured.value, condition.operator, threshold.value)

    elif measured.kind == "bool":
        assert isinstance(measured.value, bool)
        assert isinstance(threshold.value, bool)

        matched = _compare_bool(measured.value, condition.operator, threshold.value)

    else:
        return False, None

    if not matched:
        return False, None

    message = condition.description or (
        f"{condition.command} {condition.operator} {condition.threshold_raw} "
        f"(valor actual: {raw_value})"
    )
    return True, message