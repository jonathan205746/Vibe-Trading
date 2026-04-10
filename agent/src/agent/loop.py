"""AgentLoop: ReAct core loop.

Three-layer context management:
  Layer 1 (microcompact) — silently prunes old tool results each iteration, keeping the most recent 3
  Layer 2 (auto_compact) — LLM summarises and compresses when token count exceeds threshold, saves transcript
  Layer 3 (compact tool) — model explicitly calls the compact tool to trigger compression
"""

from __future__ import annotations

import json
import logging
import os
import time as _time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.agent.context import ContextBuilder
from src.agent.memory import WorkspaceMemory
from src.agent.tools import ToolRegistry
from src.agent.trace import TraceWriter
from src.core.state import RunStateStore
from src.providers.chat import ChatLLM
from src.tools.background_tools import get_background_manager

RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"
TOKEN_THRESHOLD = int(os.getenv("TOKEN_THRESHOLD", "40000"))
KEEP_RECENT = 3
TOOL_RESULT_LIMIT = 10_000

logger = logging.getLogger(__name__)


def estimate_tokens(messages: list) -> int:
    """Rough token count estimate (~4 chars/token).

    Args:
        messages: Message list.

    Returns:
        Estimated token count.
    """
    return len(json.dumps(messages, default=str, ensure_ascii=False)) // 4


def _microcompact(messages: list) -> None:
    """Layer 1: silently prune old tool results, keeping the most recent N intact.

    Args:
        messages: Message list (mutated in place).
    """
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    if len(tool_msgs) <= KEEP_RECENT:
        return
    for msg in tool_msgs[:-KEEP_RECENT]:
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > 100:
            msg["content"] = "[cleared]"


def _is_tool_success(result: str) -> bool:
    """Return True if the tool result does not contain an error."""
    return '"error"' not in result[:200]


class AgentLoop:
    """ReAct Agent core loop.

    Attributes:
        registry: Tool registry.
        llm: ChatLLM client.
        memory: Workspace memory.
        max_iterations: Maximum number of iterations.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        llm: ChatLLM,
        memory: Optional[WorkspaceMemory] = None,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        max_iterations: int = 50,
    ) -> None:
        """Initialize AgentLoop.

        Args:
            registry: Tool registry.
            llm: ChatLLM client.
            memory: Workspace memory (created fresh if not provided).
            event_callback: Event callback (event_type, data).
            max_iterations: Maximum number of loop iterations.
        """
        self.registry = registry
        self.llm = llm
        self.memory = memory or WorkspaceMemory()
        self._event_callback = event_callback
        self.max_iterations = max_iterations
        self._called_ok: set[str] = set()
        self._cancelled: bool = False

    def cancel(self) -> None:
        """Cancel the current loop.

        The main loop exits on the next iteration check.
        """
        self._cancelled = True

    def run(self, user_message: str, history: Optional[List[Dict[str, Any]]] = None, session_id: str = "") -> Dict[str, Any]:
        """Run the ReAct loop synchronously.

        Args:
            user_message: User message.
            history: Prior conversation messages.
            session_id: Session ID.

        Returns:
            Execution result dict.
        """
        state_store = RunStateStore()
        RUNS_DIR.mkdir(parents=True, exist_ok=True)

        if self.memory.run_dir and Path(self.memory.run_dir).exists():
            run_dir = Path(self.memory.run_dir)
        else:
            run_dir = state_store.create_run_dir(RUNS_DIR)
            self.memory.run_dir = str(run_dir)

        state_store.save_request(run_dir, user_message, {"session_id": session_id})

        context = ContextBuilder(self.registry, self.memory)
        messages = context.build_messages(user_message, history)
        react_trace: List[Dict[str, Any]] = []

        trace = TraceWriter(run_dir)
        trace.write({"type": "start", "prompt": user_message[:500]})

        iteration = 0
        final_content = ""

        try:
            while iteration < self.max_iterations:
                if self._cancelled:
                    trace.write({"type": "cancelled", "iter": iteration})
                    logger.info("AgentLoop cancelled by user")
                    break

                iteration += 1

                # Inject background task notifications
                bg = get_background_manager()
                notifs = bg.drain_notifications()
                if notifs:
                    notif_text = "\n".join(f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs)
                    messages.append({"role": "user", "content": f"<background-results>\n{notif_text}\n</background-results>"})
                    messages.append({"role": "assistant", "content": "Noted background results."})

                # Layer 1: microcompact (every iteration)
                _microcompact(messages)

                # Layer 2: auto_compact (token threshold exceeded)
                tokens = estimate_tokens(messages)
                if tokens > TOKEN_THRESHOLD:
                    logger.info(f"Auto compact triggered: {tokens} tokens > {TOKEN_THRESHOLD}")
                    self._auto_compact(messages, run_dir, trace)

                logger.info(f"ReAct iteration {iteration}/{self.max_iterations}")

                # Streaming output + collect thinking text
                thinking_chunks: List[str] = []

                def _on_text_chunk(delta: str) -> None:
                    thinking_chunks.append(delta)
                    self._emit("text_delta", {"delta": delta, "iter": iteration})

                response = self.llm.stream_chat(
                    messages,
                    tools=self.registry.get_definitions(),
                    on_text_chunk=_on_text_chunk,
                )

                thinking_text = "".join(thinking_chunks)
                if thinking_text:
                    trace.write({"type": "thinking", "iter": iteration, "content": thinking_text[:2000]})
                    self._emit("thinking_done", {"iter": iteration, "content": thinking_text[:500]})

                if not response.has_tool_calls:
                    final_content = response.content or ""
                    trace.write({"type": "answer", "iter": iteration, "content": final_content[:2000]})
                    react_trace.append({"type": "answer", "content": final_content[:500]})
                    break

                messages.append(context.format_assistant_tool_calls(response.tool_calls, content=response.content))

                compact_requested = False

                for tc in response.tool_calls:
                    tool_def = self.registry.get(tc.name)

                    # Layer 3: compact tool — mark then defer execution
                    if tc.name == "compact":
                        compact_requested = True
                        messages.append(context.format_tool_result(tc.id, "compact", '{"status":"ok","message":"Compressing..."}'))
                        trace.write({"type": "compact_requested", "iter": iteration})
                        continue

                    is_repeatable = tool_def.repeatable if tool_def else False
                    if tc.name in self._called_ok and not is_repeatable:
                        logger.warning(f"Blocked duplicate call: {tc.name} (already succeeded)")
                        skip_msg = json.dumps({"skipped": True, "reason": f"{tc.name} already completed successfully. Use the previous result."})
                        messages.append(context.format_tool_result(tc.id, tc.name, skip_msg))
                        trace.write({"type": "tool_skipped", "iter": iteration, "tool": tc.name})
                        react_trace.append({"type": "tool_skipped", "tool": tc.name})
                        continue

                    self._emit("tool_call", {"tool": tc.name, "arguments": {k: str(v)[:200] for k, v in tc.arguments.items()}, "iter": iteration})
                    trace.write({"type": "tool_call", "iter": iteration, "tool": tc.name, "args": {k: str(v)[:200] for k, v in tc.arguments.items()}})
                    logger.info(f"Tool call: {tc.name}({list(tc.arguments.keys())})")

                    if "run_dir" not in tc.arguments and self.memory.run_dir:
                        tc.arguments["run_dir"] = self.memory.run_dir

                    t0 = _time.perf_counter()
                    result = self.registry.execute(tc.name, tc.arguments)
                    elapsed_ms = int((_time.perf_counter() - t0) * 1000)

                    self._update_memory(tc.name, result, state_store, run_dir)

                    if _is_tool_success(result):
                        self._called_ok.add(tc.name)

                    status = "ok" if _is_tool_success(result) else "error"
                    truncated = result[:TOOL_RESULT_LIMIT]
                    messages.append(context.format_tool_result(tc.id, tc.name, truncated))

                    trace.write({"type": "tool_result", "iter": iteration, "tool": tc.name, "status": status, "elapsed_ms": elapsed_ms, "preview": result[:200]})
                    react_trace.append({"type": "tool_call", "tool": tc.name, "result_preview": result[:200]})

                    self._emit("tool_result", {"tool": tc.name, "status": status, "elapsed_ms": elapsed_ms, "preview": result[:200]})

                # Layer 3: compress after all tools have executed
                if compact_requested:
                    logger.info("Manual compact triggered by model")
                    self._auto_compact(messages, run_dir, trace)

        except Exception as exc:
            logger.exception(f"AgentLoop error: {exc}")
            trace.write({"type": "end", "status": "error", "reason": str(exc), "iterations": iteration})
            trace.close()
            state_store.mark_failure(run_dir, str(exc))
            return {
                "status": "failed",
                "reason": str(exc),
                "run_dir": str(run_dir),
                "run_id": run_dir.name,
                "content": "",
                "react_trace": react_trace,
            }

        # Determine final status
        if self._cancelled:
            state_store.mark_failure(run_dir, "cancelled by user")
            final_status = "cancelled"
        elif (run_dir / "artifacts" / "metrics.csv").exists() or final_content:
            state_store.mark_success(run_dir)
            final_status = "success"
        else:
            state_store.mark_failure(run_dir, "pipeline did not complete")
            final_status = "failed"

        trace.write({"type": "end", "status": final_status, "iterations": iteration})
        trace.close()

        return {
            "status": final_status,
            "run_dir": str(run_dir),
            "run_id": run_dir.name,
            "content": final_content,
            "react_trace": react_trace,
        }

    def _auto_compact(self, messages: list, run_dir: Path, trace: TraceWriter) -> None:
        """Layer 2/3: LLM summarise-and-compress; saves transcript before compressing.

        Args:
            messages: Message list (replaced in place).
            run_dir: Run directory.
            trace: TraceWriter.
        """
        # Save full transcript (timestamped, one file per compression)
        transcript_path = run_dir / f"transcript_{int(_time.time())}.jsonl"
        with open(transcript_path, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg, default=str, ensure_ascii=False) + "\n")

        # LLM summary (no tools, plain text)
        conv_text = json.dumps(messages[1:], default=str, ensure_ascii=False)[:80000]
        summary_resp = self.llm.chat([
            {"role": "user", "content": (
                "Summarize this conversation for continuity. Include: "
                "1) What was accomplished, 2) Current state, 3) Key decisions made. "
                "Be concise but preserve critical details.\n\n" + conv_text
            )},
        ])
        summary = summary_resp.content or ""

        tokens_before = estimate_tokens(messages)
        trace.write({"type": "compact", "tokens_before": tokens_before, "summary": summary[:500]})
        self._emit("compact", {"tokens_before": tokens_before, "summary": summary[:200]})

        # Replace: keep system prompt + inject compressed summary + restore identity
        system_msg = messages[0]
        state_summary = self.memory.to_summary()
        compressed = f"[Conversation compressed. Transcript: {transcript_path}]\n\n{summary}"
        if state_summary and state_summary != "(empty state)":
            compressed += f"\n\nCurrent agent state:\n{state_summary}"
        messages.clear()
        messages.extend([
            system_msg,
            {"role": "user", "content": compressed},
            {"role": "assistant", "content": "Understood. I have the context from the summary. Continuing."},
        ])

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Fire an event via the callback."""
        if self._event_callback:
            try:
                self._event_callback(event_type, data)
            except Exception:
                pass

    def _update_memory(self, tool_name: str, result: str, state_store: RunStateStore, run_dir: Path) -> None:
        """Update memory and persist tool result."""
        self.memory.increment(tool_name)
        try:
            data = json.loads(result)
            if isinstance(data, dict):
                state_store.persist_tool_result(tool_name, data, run_dir)
        except (json.JSONDecodeError, TypeError):
            pass
