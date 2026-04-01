"""Workspace memory: shared state across tool calls.

WorkspaceMemory passes intermediate results between tools during an agent run.
Generic KV store + counters; no tool-specific fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class WorkspaceMemory:
    """Shared workspace state between tools.

    Attributes:
        run_dir: Current run directory.
        store: Generic result store (tool memory_key -> JSON string).
        counters: Tool invocation counters.
        extra: Generic KV store for derived values passed between tools.
    """

    run_dir: Optional[str] = None
    store: Dict[str, str] = field(default_factory=dict)
    counters: Dict[str, int] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def reset(self) -> None:
        """Reset all state."""
        self.run_dir = None
        self.store.clear()
        self.counters.clear()
        self.extra.clear()

    def set_result(self, key: str, value: str) -> None:
        """Store a tool result.

        Args:
            key: Memory key (e.g. "plan_output").
            value: JSON string.
        """
        self.store[key] = value

    def get_result(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a tool result.

        Args:
            key: Memory key.
            default: Default value.

        Returns:
            JSON string or default.
        """
        return self.store.get(key, default)

    def increment(self, key: str) -> int:
        """Increment a counter and return the new value.

        Args:
            key: Counter key.

        Returns:
            Updated counter value.
        """
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def set_extra(self, key: str, value: Any) -> None:
        """Set an extra KV entry.

        Args:
            key: Key name.
            value: Value.
        """
        self.extra[key] = value

    def get_extra(self, key: str, default: Any = None) -> Any:
        """Get an extra KV entry.

        Args:
            key: Key name.
            default: Default value.

        Returns:
            Stored value or default.
        """
        return self.extra.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a KV entry (alias for set_extra).

        Args:
            key: Key name.
            value: Value.
        """
        self.extra[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a KV entry (alias for get_extra).

        Args:
            key: Key name.
            default: Default value.

        Returns:
            Stored value or default.
        """
        return self.extra.get(key, default)

    def to_summary(self) -> str:
        """Generate a state summary for the LLM indicating completed steps.

        Returns:
            State summary text.
        """
        lines = []
        if self.run_dir:
            lines.append(f"- run_dir: {self.run_dir}")
        if self.store:
            completed = list(self.store.keys())
            lines.append(f"- completed: {', '.join(completed)}")
        if self.counters:
            counter_parts = [f"{k}={v}" for k, v in self.counters.items()]
            lines.append(f"- counters: {', '.join(counter_parts)}")
        return "\n".join(lines) if lines else "(empty state)"
