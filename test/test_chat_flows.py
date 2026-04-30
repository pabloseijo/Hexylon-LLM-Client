"""
Batería básica de pruebas de integración conversacional para hexylon-llm-client.

Ejecuta secuencias de entradas sobre run_pipeline() y valida que las respuestas
contengan ciertos patrones esperados.

Uso:
    PYTHONPATH=src python3 scripts/test_chat_flows.py

Notas:
- Estas pruebas llaman al sistema real.
- Si el equipo Hexylon no está disponible, algunas pruebas de command/task fallarán.
- Está pensado como smoke test funcional, no como test unitario puro.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field

from llm.core.pipeline import run_pipeline
from llm.memory.conversation_history import conversation_history
from llm.memory.session_log import session_log
from llm.memory.session_memory import session_memory
from llm.memory.task_history import task_history


@dataclass
class StepExpectation:
    contains_any: list[str] = field(default_factory=list)
    contains_all: list[str] = field(default_factory=list)
    not_contains: list[str] = field(default_factory=list)


@dataclass
class ChatStep:
    user_input: str
    expectation: StepExpectation


@dataclass
class ChatCase:
    name: str
    steps: list[ChatStep]


def reset_state() -> None:
    """
    Reinicia memoria de sesión y conversación para aislar cada caso.
    """
    conversation_history.clear()
    session_memory.clear()

    # Si session_log tiene clear(), usarlo. Si no, ignorar.
    if hasattr(session_log, "clear"):
        session_log.clear()

    # task_history es persistente; normalmente no debe borrarse en smoke tests.
    # Si quisieras aislarlo totalmente, habría que añadir una API específica.


def check_expectation(output: str, exp: StepExpectation) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if exp.contains_any:
        if not any(token in output for token in exp.contains_any):
            errors.append(
                f"No contiene ninguno de los patrones esperados: {exp.contains_any}"
            )

    for token in exp.contains_all:
        if token not in output:
            errors.append(f"No contiene el patrón obligatorio: {token!r}")

    for token in exp.not_contains:
        if token in output:
            errors.append(f"Contiene un patrón prohibido: {token!r}")

    return len(errors) == 0, errors


def run_test_case(case: ChatCase) -> bool:
    print(f"\n{'=' * 80}")
    print(f"TEST: {case.name}")
    print(f"{'=' * 80}")

    reset_state()
    all_ok = True

    for i, step in enumerate(case.steps, start=1):
        print(f"\n[{case.name} :: paso {i}] >>> {step.user_input}")

        try:
            output = run_pipeline(step.user_input)
        except Exception:
            all_ok = False
            print("EXCEPCIÓN durante run_pipeline():")
            traceback.print_exc()
            continue

        print(output)

        ok, errors = check_expectation(output, step.expectation)
        if ok:
            print("OK")
        else:
            all_ok = False
            print("FAIL")
            for err in errors:
                print(f"  - {err}")

    return all_ok


def build_test_cases() -> list[ChatCase]:
    return [
        ChatCase(
            name="command_basico_potencia",
            steps=[
                ChatStep(
                    user_input="dame la potencia actual",
                    expectation=StepExpectation(
                        contains_any=["dBµV", "dBuV", "dBm", "potencia"],
                        not_contains=["No he podido determinar un comando SCPI válido"],
                    ),
                ),
            ],
        ),
        ChatCase(
            name="followup_contextual_sobre_valor",
            steps=[
                ChatStep(
                    user_input="dame la potencia actual",
                    expectation=StepExpectation(
                        contains_any=["dBµV", "dBuV", "dBm", "potencia"],
                    ),
                ),
                ChatStep(
                    user_input="y esto es alto o bajo para una señal satelital?",
                    expectation=StepExpectation(
                        contains_any=[
                            "no contiene suficiente información",
                            "depende",
                            "alto",
                            "bajo",
                            "señal satelital",
                        ],
                        not_contains=["No he podido determinar un comando SCPI válido"],
                    ),
                ),
            ],
        ),
        ChatCase(
            name="knowledge_directo",
            steps=[
                ChatStep(
                    user_input="qué hace el comando MER?",
                    expectation=StepExpectation(
                        contains_any=["MER", "comando", "mide", "devuelve"],
                        not_contains=["No he podido determinar un comando SCPI válido"],
                    ),
                ),
            ],
        ),
        ChatCase(
            name="session_question_basica",
            steps=[
                ChatStep(
                    user_input="mídeme POW cada 5 segundos durante 15 segundos",
                    expectation=StepExpectation(
                        contains_all=["Tarea lanzada:", "POW?"],
                    ),
                ),
                ChatStep(
                    user_input="qué estamos haciendo?",
                    expectation=StepExpectation(
                        contains_any=[
                            "medición",
                            "tarea",
                            "potencia",
                            "sesión",
                            "estamos",
                        ],
                    ),
                ),
            ],
        ),
        ChatCase(
            name="tasks_list_and_cancel",
            steps=[
                ChatStep(
                    user_input="mídeme MER cada 5 segundos durante 30 segundos",
                    expectation=StepExpectation(
                        contains_all=["Tarea lanzada:", "MER?"],
                    ),
                ),
                ChatStep(
                    user_input="tareas activas",
                    expectation=StepExpectation(
                        contains_all=["Tareas activas:", "Tarea #1"],
                    ),
                ),
                ChatStep(
                    user_input="cancela la tarea",
                    expectation=StepExpectation(
                        contains_all=["cancelada"],
                    ),
                ),
            ],
        ),
        ChatCase(
            name="analysis_basico",
            steps=[
                ChatStep(
                    user_input="mídeme POW y MER cada 5 segundos durante 15 segundos",
                    expectation=StepExpectation(
                        contains_all=["Tarea lanzada:", "POW?", "MER?"],
                    ),
                ),
                ChatStep(
                    user_input="resume la última medición",
                    expectation=StepExpectation(
                        contains_any=[
                            "potencia",
                            "MER",
                            "medición",
                            "muestras",
                            "tendencia",
                        ],
                        not_contains=["No he encontrado ninguna medición reciente"],
                    ),
                ),
            ],
        ),
    ]


def main() -> None:
    cases = build_test_cases()
    passed = 0

    for case in cases:
        ok = run_test_case(case)
        if ok:
            passed += 1

    total = len(cases)
    print(f"\n{'=' * 80}")
    print(f"RESULTADO FINAL: {passed}/{total} casos correctos")
    print(f"{'=' * 80}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()