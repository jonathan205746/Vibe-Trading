"""Compact tool: model-initiated context compression."""

from __future__ import annotations

import json
from typing import Any

from src.agent.tools import BaseTool


class CompactTool(BaseTool):
    """Compress conversation history to free context space."""

    name = "compact"
    description = "Compress conversation history to free context space. Call when the conversation feels long or you're losing track of earlier context."
    parameters = {"type": "object", "properties": {}, "required": []}

    def execute(self, **kwargs: Any) -> str:
        return json.dumps({"status": "ok", "message": "Compression triggered"})
