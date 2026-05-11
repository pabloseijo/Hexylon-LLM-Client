import json
from pathlib import Path
from typing import Any

from llm.clients.ollama_client import ask_llm
from llm.core.intent_router import route_intent
from llm.memory.conversation_history import conversation_history
from llm.handlers.command_handler import handle_command
from llm.handlers.knowledge_handler import handle_knowledge
from llm.handlers.session_handler import handle_session_question
from llm.handlers.orchestrator_handler import handle_orchestrated_sequence
from llm.parsing.main_parser import parse_input
from llm.handlers.analysis_handler import handle_analysis
from llm.handlers.task_handler import (
    handle_launch_task,
    handle_cancel_task,
    handle_list_tasks,
)
from llm.core.scpi_generator import keyword_mapping, detect_intent


def _load_machine_names() -> list[str]:
    try:
        path = Path(__file__).parents[3] / "config" / "machines.json"
        data = json.loads(path.read_text())
        return [k for k in data.keys() if k != "default"]
    except Exception:
        return []


def _extract_machine_id(user_input: str) -> str | None:
    machines = _load_machine_names()
    if not machines:
        return None

    text = user_input.lower()

    for machine in machines:
        if machine.lower() in text:
            return machine

    aliases = {
        "hexylon a": "hexylon_a",
        "hexylon b": "hexylon_b",
        "generador": "generator",
        "generator": "generator",
        "gen ": "generator",
        "sgu": "generator",
    }
    for alias, machine_id in aliases.items():
        if alias in text and machine_id in machines:
            return machine_id

    return None


def run_pipeline(user_input: str) -> dict[str, Any] | str:
    conversation_history.add_user_message(user_input)
    parsed = parse_input(user_input)
    normalized = parsed.normalized_input
    machine_id = _extract_machine_id(user_input)

    if parsed.intent in ("analysis", "plot"):
        response = handle_analysis(user_input)
        if isinstance(response, dict):
            conversation_history.add_assistant_message(response["message"])
            return response
        conversation_history.add_assistant_message(response)
        return response

    if parsed.intent == "session_question":
        response = handle_session_question(user_input)
        conversation_history.add_assistant_message(response)
        return response

    if parsed.intent == "cancel_task":
        response = handle_cancel_task(user_input)
        conversation_history.add_assistant_message(response)
        return response

    if parsed.intent == "list_tasks":
        response = handle_list_tasks()
        conversation_history.add_assistant_message(response)
        return response

    if parsed.intent == "orchestrated_sequence":
        response = handle_orchestrated_sequence(user_input)
        if isinstance(response, dict):
            conversation_history.add_assistant_message(response["message"])
            return response
        conversation_history.add_assistant_message(response)
        return response

    if parsed.intent == "launch_task":
        response = handle_launch_task(user_input, machine_id=machine_id)
        if isinstance(response, dict):
            conversation_history.add_assistant_message(response["message"])
            return response
        conversation_history.add_assistant_message(response)
        return response

    # --- Enrutamiento command / knowledge ---
    # detect_intent ya clasifica correctamente "que hace pow" como knowledge
    # y "dame la potencia" como command, sin necesidad de llamar al LLM
    scpi_intent = detect_intent(normalized)

    if scpi_intent == "knowledge":
        response = handle_knowledge(user_input, normalized)
        conversation_history.add_assistant_message(response)
        return response

    # Para comandos: si hay mapeo determinista saltamos route_intent
    mapped = keyword_mapping(normalized)
    if mapped is None:
        routed_intent = route_intent(normalized)
        if routed_intent == "knowledge":
            response = handle_knowledge(user_input, normalized)
            conversation_history.add_assistant_message(response)
            return response

    response = handle_command(user_input, normalized, machine_id=machine_id)
    conversation_history.add_assistant_message(response)
    return response