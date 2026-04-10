"""Subagent tool: isolated-context child agent that shares the filesystem and returns only a summary."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from src.agent.tools import BaseTool, ToolRegistry
from src.agent.context import ContextBuilder

_MAX_SUBAGENT_ITERATIONS = int(os.getenv("SUBAGENT_MAX_ITER", "25"))
_MAX_SUBAGENT_TIMEOUT_SEC = int(os.getenv("SUBAGENT_TIMEOUT", "300"))
_MAX_SUBAGENT_TOKEN_ESTIMATE = 30000


class SubagentTool(BaseTool):
    """Spawn a child agent to execute an independent task with isolated context."""

    name = "subagent"
    description = (
        "Spawn a subagent with fresh context. It shares the filesystem but not "
        "conversation history. Use for parallel research, isolated exploration, "
        "or tasks that would pollute the main context. Returns only a summary."
    )
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Task for the subagent"},
            "description": {"type": "string", "description": "Short label for display"},
        },
        "required": ["prompt"],
    }

    def execute(self, **kwargs: Any) -> str:
        """Start a child agent and return its summary.

        Three guards against infinite loops:
            - Iteration cap: _MAX_SUBAGENT_ITERATIONS rounds
            - Time cap: _MAX_SUBAGENT_TIMEOUT_SEC seconds
            - Token estimate cap: _MAX_SUBAGENT_TOKEN_ESTIMATE tokens

        Args:
            **kwargs: Must include prompt (str). Optional run_dir (str) and description (str).

        Returns:
            JSON string with status and summary fields.
        """
        prompt = kwargs["prompt"]
        run_dir = kwargs.get("run_dir")

        from src.providers.chat import ChatLLM
        from src.tools.bash_tool import BashTool
        from src.tools.read_file_tool import ReadFileTool
        from src.tools.write_file_tool import WriteFileTool
        from src.tools.edit_file_tool import EditFileTool
        from src.tools.load_skill_tool import LoadSkillTool
        from src.tools.backtest_tool import BacktestTool

        llm = ChatLLM()
        child = ToolRegistry()
        for t in [BashTool(), ReadFileTool(), WriteFileTool(),
                  EditFileTool(), LoadSkillTool(), BacktestTool()]:
            child.register(t)

        messages = [
            {"role": "system", "content": "You are a quantitative research subagent. Complete the task using tools, then summarize findings."},
            {"role": "user", "content": prompt},
        ]

        t0 = time.monotonic()
        for iteration in range(_MAX_SUBAGENT_ITERATIONS):
            elapsed = time.monotonic() - t0
            if elapsed > _MAX_SUBAGENT_TIMEOUT_SEC:
                return json.dumps(
                    {"status": "timeout", "summary": f"Subagent timed out after {elapsed:.0f}s ({iteration} iterations)"},
                    ensure_ascii=False,
                )

            token_estimate = len(json.dumps(messages)) // 4
            if token_estimate > _MAX_SUBAGENT_TOKEN_ESTIMATE:
                return json.dumps(
                    {"status": "token_limit", "summary": f"Subagent context too large (~{token_estimate} tokens, {iteration} iterations)"},
                    ensure_ascii=False,
                )

            response = llm.chat(messages, tools=child.get_definitions())
            if not response.has_tool_calls:
                return json.dumps({"status": "ok", "summary": response.content or "(no summary)"}, ensure_ascii=False)
            messages.append(ContextBuilder.format_assistant_tool_calls(response.tool_calls, content=response.content))
            for tc in response.tool_calls:
                if run_dir and "run_dir" not in tc.arguments:
                    tc.arguments["run_dir"] = run_dir
                result = child.execute(tc.name, tc.arguments)
                messages.append(ContextBuilder.format_tool_result(tc.id, tc.name, result[:10000]))

        return json.dumps(
            {"status": "iteration_limit", "summary": f"Subagent hit iteration limit ({_MAX_SUBAGENT_ITERATIONS} iterations)"},
            ensure_ascii=False,
        )
