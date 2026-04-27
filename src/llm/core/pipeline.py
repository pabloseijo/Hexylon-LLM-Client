import re
from typing import Any

from llm.core.intent_router import route_intent
from llm.memory.conversation_history import conversation_history
from llm.handlers.command_handler import handle_command
from llm.handlers.knowledge_handler import handle_knowledge
from llm.handlers.session_handler import handle_session_question
from llm.parsing.main_parser import parse_input
from llm.handlers.analysis_handler import handle_analysis
from llm.handlers.task_handler import (
    handle_launch_task,
    handle_cancel_task,
    handle_list_tasks,
)


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def run_pipeline(user_input: str) -> dict[str, Any] | str:
    conversation_history.add_user_message(user_input)

    parsed = parse_input(user_input)
    normalized = parsed.normalized_input

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

    if parsed.intent == "launch_task":
        response = handle_launch_task(user_input)

        if isinstance(response, dict):
            conversation_history.add_assistant_message(response["message"])
            return response

        conversation_history.add_assistant_message(response)
        return response

    routed_intent = route_intent(normalized)

    if routed_intent == "knowledge":
        response = handle_knowledge(user_input, normalized)
        conversation_history.add_assistant_message(response)
        return response
    
    response = handle_command(user_input, normalized)
    conversation_history.add_assistant_message(response)
    return response