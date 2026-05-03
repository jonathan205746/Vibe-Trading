"""Load skill tool: load full skill documentation by name."""

from __future__ import annotations

import json
from typing import Any

from src.agent.skills import SkillsLoader
from src.agent.tools import BaseTool


class LoadSkillTool(BaseTool):
    """Load the full documentation for a named skill."""

    name = "load_skill"
    description = "Load full documentation for a named skill. Use this to learn about unfamiliar strategy patterns or workflows before starting."
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Skill name (e.g. 'strategy-generate', 'momentum')"},
        },
        "required": ["name"],
    }
    repeatable = True

    def __init__(self, skills_loader: SkillsLoader | None = None) -> None:
        """Initialize LoadSkillTool.

        Args:
            skills_loader: SkillsLoader instance; creates one automatically if omitted.
        """
        self._loader = skills_loader or SkillsLoader()

    def execute(self, **kwargs: Any) -> str:
        """Load skill documentation.

        Args:
            **kwargs: Must include name, or a single positional arg as skill name.

        Returns:
            Full skill documentation or an error message.
        """
        name = kwargs.get("name")
        if name is None:
            # 兼容 LLM 可能传入的非标准格式（如直接传 skill 名）
            for key in kwargs:
                if isinstance(kwargs[key], str) and len(kwargs[key]) < 100:
                    name = kwargs[key]
                    break
        if not name:
            return json.dumps({"status": "error", "content": "Error: load_skill requires 'name' parameter"}, ensure_ascii=False)
        content = self._loader.get_content(name)
        return json.dumps({
            "status": "ok" if not content.startswith("Error:") else "error",
            "content": content,
        }, ensure_ascii=False)
