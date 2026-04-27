from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


IntentName = Literal[
    "plot",
    "analysis",
    "cancel_task",
    "list_tasks",
    "session_question",
    "launch_task",
    "unknown",
]


@dataclass(frozen=True)
class ParsedIntent:
    intent: IntentName
    normalized_input: str
    task_id: str | None = None
    metric: str | None = None